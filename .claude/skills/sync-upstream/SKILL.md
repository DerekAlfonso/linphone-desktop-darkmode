---
name: sync-upstream
description: Sync this fork's master with the upstream linphone-desktop repo (BelledonneCommunications) while keeping fork-local tooling commits. Use when the user wants to update, sync, pull upstream, or catch the fork up.
---

# Sync the fork with upstream

`master` in this fork = `upstream/master` + fork-local tooling commits (AGENTS.md, .claude/, …)
+ any work in progress. Sync by **merging** upstream into `master` (no rebase), so the fork's
published history is never rewritten.

## Steps

1. Ensure the remote exists and fetch:
   ```bash
   git remote get-url upstream || git remote add upstream https://github.com/BelledonneCommunications/linphone-desktop.git
   git fetch upstream
   git rev-list --left-right --count upstream/master...master   # behind / ahead
   ```

2. Require a clean tree on `master` (`git status --porcelain` empty). If the user is
   elsewhere, stash or commit with their agreement first, then `git switch master`.

3. Merge:
   ```bash
   git merge --ff upstream/master -m "Merge upstream/master into fork"
   ```
   A fast-forward is fine when the fork has no own commits. Conflicts are almost always in a
   `fork-local` marker block (keep upstream's lines outside the block, keep the block) or in a
   feature file; resolve, then `git commit`.

4. Update submodules to the pinned SDK:
   `git -c submodule.external/feature-specs.update=none submodule update --init --recursive`
   (`feature-specs` is a private Belledonne repo; skip it).

5. Rebase any open feature branches onto the new `master` if the user wants them current.

6. **Push only with the user's OK**: `git push origin master`.
   (`gh repo sync DerekAlfonso/linphone-desktop-darkmode` is not suitable once the fork has
   its own commits: it refuses or would discard them.)
