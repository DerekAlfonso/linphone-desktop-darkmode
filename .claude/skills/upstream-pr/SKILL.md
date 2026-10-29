---
name: upstream-pr
description: Prepare a pull request for the upstream linphone-desktop project (BelledonneCommunications) from work in this fork, with all fork-local tooling (AGENTS.md, CLAUDE.md, .claude/, memory, .fork-local marker blocks) removed. Use when the user wants to send, upstream, contribute or open a PR/MR for a change to the main repo.
---

# Prepare an upstream PR

This fork carries tooling that must never reach upstream. It is defined in `.fork-local`
(paths) plus `>>> fork-local` / `<<< fork-local` marker blocks inside shared files such as
`.gitignore`. `prepare_upstream_pr.py` builds a clean branch `upstream-pr/<name>` on top of
`upstream/master` without touching the current checkout and without pushing.

## Steps

1. **Make sure upstream is current**: `git fetch upstream`. If `upstream` is missing:
   `git remote add upstream https://github.com/BelledonneCommunications/linphone-desktop.git`.

2. **Pick the work to send.** Default is the current branch:
   - On a feature branch (not `master`): its commits since it branched from fork `master`.
   - On `master`: every fork commit not yet in `upstream/master`.
   - Narrow it with `--source <branch>` and/or `--base <ref>` (exclusive start).
   Preview first:
   ```bash
   python .claude/skills/upstream-pr/prepare_upstream_pr.py <name> --dry-run
   ```
   Show the user the commit list and confirm it is the intended set.

3. **Build the branch**:
   ```bash
   python .claude/skills/upstream-pr/prepare_upstream_pr.py <name>
   ```
   Add `--force` to rebuild an existing `upstream-pr/<name>`. On a conflict the script stops
   and names the files: sync the fork (sync-upstream skill), rebase the feature branch on the
   new `master`, then rerun.

4. **Review the result** before anything leaves the machine:
   ```bash
   git log --oneline upstream/master..upstream-pr/<name>
   git diff --stat upstream/master upstream-pr/<name>
   ```
   Confirm no tooling paths and no `fork-local` markers appear. If upstream wants a single
   commit, squash on the PR branch only (never on `master`).

5. **Optionally build/test** the PR branch in a worktree:
   `git worktree add ../linphone-pr upstream-pr/<name>` (submodules need
   `git submodule update --init --recursive` there).

6. **Publish only with the user's explicit OK** (push and PR creation are public):
   ```bash
   git push -u origin upstream-pr/<name>
   gh pr create --repo BelledonneCommunications/linphone-desktop --base master --head DerekAlfonso:upstream-pr/<name>
   ```
   The GitHub repo is a mirror; Belledonne's primary review happens as merge requests on
   https://gitlab.linphone.org/BC/public/linphone-desktop. If the user prefers GitLab, push the
   same branch to their GitLab fork remote and open the MR there instead. Draft the PR body
   from the kept commits; do not mention the fork's tooling.

## Rules

- Never add fork-local files to an `upstream-pr/*` branch, and never merge one back into `master`.
- New tooling paths go into `.fork-local` (commit that change in the fork) before preparing a PR.
- Fork-only edits to upstream files must sit inside marker blocks, or they will be sent.
