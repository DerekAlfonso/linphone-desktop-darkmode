# AGENTS.md

Guide for coding agents working in this fork of
[linphone-desktop](https://github.com/BelledonneCommunications/linphone-desktop)
(`DerekAlfonso/linphone-desktop-darkmode`). This file is fork-local: it is never sent upstream.

## Fork workflow

- Remotes: `origin` = the fork (GitHub), `upstream` = BelledonneCommunications/linphone-desktop
  (GitHub mirror of https://gitlab.linphone.org/BC/public/linphone-desktop).
- `master` = `upstream/master` + fork-local tooling + fork work. Sync by merging upstream
  (skill: `sync-upstream`); never rebase or force-push `master`.
- Do feature work on branches off `master`. To contribute upstream, use the `upstream-pr` skill:
  it builds `upstream-pr/<name>` on `upstream/master` with all tooling stripped.
- Fork-local paths are listed in `.fork-local`. Add any new tooling path there. Fork-only edits
  to files that exist upstream must be wrapped in lines containing `>>> fork-local` and
  `<<< fork-local` (see the end of `.gitignore`).
- Keep tooling and product changes in separate commits; the PR script drops tooling-only commits.
- Claude Code's project memory directory is a junction to `.claude/memory/`, so memories are
  committed with the fork.

## Project layout

- `Linphone/` — the Qt 6 / QML application (`core/`, `model/`, `view/`, `tool/`, `data/`).
- `external/linphone-sdk` — Linphone SDK submodule, built as part of the tree.
- `external/google/*` — crashpad and its tooling (crash handler builds only).
- `cmake/` — build modules, toolchains, install rules, and a `pre-commit` clang-format hook
  that configuring the build copies into `.git/hooks/`.
- `tester/squish` — UI tests; `.gitlab-ci-files/` — upstream CI.

## Build (Windows)

See `README.md` ("Specific instructions for the Windows platform"). In short: VS 2022 MSVC x64,
Qt 6.10+ (msvc2022_64, with qtnetworkauth and qtshadertools), MSYS2 tools on PATH, Python with
`pystache six`, then from a VS x64 developer shell:

```
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_WINDOWS_TOOLS_CHECK=ON
cmake --build build --parallel
cmake --install build
```

Output lands in `build/OUTPUT`. Submodules:
`git -c submodule.external/feature-specs.update=none submodule update --init --recursive`
(`feature-specs` is a private Belledonne repo).

## Conventions

- C++17, formatted with the repo `.clang-format` (LLVM base, 4-space access offset).
- Match surrounding code style; upstream commit messages are short imperative sentences,
  optionally ending with a ticket id such as `#LINQT-1234`.
