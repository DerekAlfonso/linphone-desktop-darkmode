#!/usr/bin/env python3
"""Build a clean branch for an upstream PR from fork commits.

Replays the commits in BASE..SOURCE (merges skipped) onto UPSTREAM in a
temporary worktree, dropping every path listed in .fork-local and stripping
">>> fork-local" ... "<<< fork-local" blocks from the remaining files.
Commits that become empty (tooling-only) are dropped. Author, date and
message of each kept commit are preserved.

The user's checkout is never touched. Nothing is pushed.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

MARK_START = ">>> fork-local"
MARK_END = "<<< fork-local"


def git(*args, cwd=None, check=True, capture=True):
    result = subprocess.run(
        ["git", *args], cwd=cwd, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if check and result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip() if capture else ""


def ok(*args, cwd=None):
    """True when the git command exits 0 (for --quiet / --is-ancestor style checks)."""
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True).returncode == 0


def lines(text):
    return [l for l in text.splitlines() if l]


def read_pathspecs(source):
    """Turn the .fork-local manifest at SOURCE into git glob pathspecs."""
    manifest = git("show", f"{source}:.fork-local", check=False)
    if not manifest:
        sys.exit(f".fork-local not found at {source}")
    specs = []
    for raw in manifest.splitlines():
        entry = raw.strip()
        if not entry or entry.startswith("#"):
            continue
        entry = entry.lstrip("/")
        if entry.endswith("/"):
            entry += "**"
        specs.append(f":(glob){entry}")
    return specs


def strip_blocks(text):
    out, skipping = [], False
    for line in text.splitlines(keepends=True):
        if MARK_START in line:
            skipping = True
            # Drop blank lines that only separated the block from the content above.
            while out and not out[-1].strip():
                out.pop()
            if out and not out[-1].endswith(("\n", "\r")):
                out[-1] += "\n"
            continue
        if skipping:
            if MARK_END in line:
                skipping = False
            continue
        out.append(line)
    return "".join(out)


def filter_index(wt, specs):
    """Remove fork-local content from the staged cherry-pick. Returns touched paths."""
    removed = lines(git("diff", "--cached", "--name-only", "--", *specs, cwd=wt))
    if removed:
        git("restore", "--source=HEAD", "--staged", "--worktree", "--", *removed, cwd=wt)

    stripped = []
    for path in lines(git("diff", "--cached", "--name-only", "--diff-filter=AM", cwd=wt)):
        full = os.path.join(wt, path)
        try:
            with open(full, encoding="utf-8", newline="") as f:
                text = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        if MARK_START not in text:
            continue
        with open(full, "w", encoding="utf-8", newline="") as f:
            f.write(strip_blocks(text))
        git("add", "--", path, cwd=wt)
        # Whitespace left over at EOF is not worth a hunk: fall back to upstream's file.
        if ok("cat-file", "-e", f"HEAD:{path}", cwd=wt) and \
                ok("diff", "--cached", "--quiet", "--ignore-blank-lines", "--ignore-space-at-eol",
                   "HEAD", "--", path, cwd=wt):
            git("restore", "--source=HEAD", "--staged", "--worktree", "--", path, cwd=wt)
        stripped.append(path)
    return removed, stripped


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("name", help="PR branch is created as upstream-pr/<name>")
    p.add_argument("--source", default="HEAD", help="branch or commit holding the work (default: HEAD)")
    p.add_argument("--base", help="exclusive start of the commit range (default: merge-base with "
                                  "the fork's master for a feature branch, else --upstream)")
    p.add_argument("--upstream", default="upstream/master", help="branch to build on (default: upstream/master)")
    p.add_argument("--fork-master", default="master", help="the fork's integration branch (default: master)")
    p.add_argument("--force", action="store_true", help="overwrite an existing upstream-pr/<name> branch")
    p.add_argument("--dry-run", action="store_true", help="list the commits and stop")
    args = p.parse_args()

    os.chdir(git("rev-parse", "--show-toplevel"))
    branch = f"upstream-pr/{args.name}"
    source = git("rev-parse", "--verify", f"{args.source}^{{commit}}")
    upstream = git("rev-parse", "--verify", f"{args.upstream}^{{commit}}")

    if args.base:
        base = git("rev-parse", "--verify", f"{args.base}^{{commit}}")
    else:
        fork_master = git("rev-parse", "--verify", f"{args.fork_master}^{{commit}}")
        on_master = ok("merge-base", "--is-ancestor", source, fork_master)
        base = upstream if on_master else git("merge-base", source, fork_master)

    commits = lines(git("rev-list", "--reverse", "--no-merges", f"{base}..{source}", "--not", upstream))
    if not commits:
        sys.exit(f"No commits to send: {base[:10]}..{source[:10]} is already in {args.upstream}.")

    print(f"Replaying {len(commits)} commit(s) from {base[:10]}..{source[:10]} onto {args.upstream} ({upstream[:10]}):")
    for c in commits:
        print("  " + git("log", "-1", "--format=%h %s", c))
    if args.dry_run:
        return

    if ok("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}") and not args.force:
        sys.exit(f"Branch {branch} already exists; pass --force to rebuild it.")

    specs = read_pathspecs(source)
    wt = tempfile.mkdtemp(prefix="upstream-pr-")
    os.rmdir(wt)
    git("worktree", "add", "--quiet", "--detach", wt, upstream)
    kept, dropped = [], []
    try:
        for c in commits:
            subject = git("log", "-1", "--format=%h %s", c)
            pick = subprocess.run(["git", "cherry-pick", "--no-commit", c], cwd=wt,
                                  capture_output=True, text=True)
            if pick.returncode != 0:
                conflicted = lines(git("diff", "--name-only", "--diff-filter=U", cwd=wt))
                local = set(lines(git("diff", "--name-only", "--diff-filter=U", "--", *specs, cwd=wt)))
                if not conflicted or set(conflicted) - local:
                    sys.exit(f"Conflict replaying {subject} onto {args.upstream}:\n  "
                             + "\n  ".join(sorted(set(conflicted) - local) or [pick.stderr.strip()])
                             + "\nSync the fork with upstream (sync-upstream skill), resolve, then retry.")
            filter_index(wt, specs)
            if ok("diff", "--cached", "--quiet", cwd=wt):
                git("reset", "--quiet", "--hard", cwd=wt)
                dropped.append(subject)
                continue
            git("commit", "--quiet", "--no-verify", "-C", c, cwd=wt)
            kept.append(subject)

        if not kept:
            sys.exit("Every commit was fork-local tooling; nothing to send upstream.")

        # Final guard: nothing fork-local may survive.
        leaked = lines(git("diff", "--name-only", upstream, "HEAD", "--", *specs, cwd=wt))
        marked = lines(git("grep", "-l", MARK_START, "HEAD", "--",
                           *lines(git("diff", "--name-only", upstream, "HEAD", cwd=wt)),
                           cwd=wt, check=False))
        if leaked or marked:
            sys.exit("Fork-local content leaked into the PR branch:\n  " + "\n  ".join(leaked + marked))

        head = git("rev-parse", "HEAD", cwd=wt)
        git("branch", *(["--force"] if args.force else []), branch, head)
    finally:
        git("worktree", "remove", "--force", wt, check=False)
        shutil.rmtree(wt, ignore_errors=True)

    print(f"\nKept {len(kept)}, dropped {len(dropped)} tooling-only commit(s).")
    for d in dropped:
        print("  dropped: " + d)
    print(f"\nCreated {branch} on {args.upstream}:")
    print(git("diff", "--stat", upstream, branch))


if __name__ == "__main__":
    main()
