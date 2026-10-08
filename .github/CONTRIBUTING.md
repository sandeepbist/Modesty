# Contributing to Modesty

Issues and pull requests are welcome. The maintainer, @sandeepbist, decides what
merges into this repository. Contributors work through forks; opening an issue
or PR does not grant push or merge access.

## Report a bug

Search existing issues, then use the bug report form. Include reproducible steps,
expected behavior, actual behavior and the relevant package versions. For visual
bugs, a short recording helps more than a long description. Remove credentials,
private messages and personal file contents from screenshots and logs.

For vulnerabilities, follow [SECURITY.md](SECURITY.md) rather than posting exploit
details in a public issue.

## Submit a change

1. Fork the repository and create a branch for one change.
2. Keep UI in `modules/`, shared state in `services/`, and system work in `scripts/`.
   Reuse existing components. Update `setup/` when changing installation defaults.
3. Run `python3 tests/check.py` with the desktop dependencies, Node.js and Lua installed.
   Add a regression check for a behavior change where it can catch a real failure.
   For installer changes, also run `python3 tests/installer-cli.py --isolated-home`
   as a normal user with the required packages and services already available.
   This uses a disposable home and source copy; it does not install packages.
4. Check UI changes in a native Hyprland session, including reduced motion. Include
   a screenshot or short clip and say what you tested.
5. Add user-visible changes to `[Unreleased]` in `CHANGELOG.md`. Do not bump
   `VERSION` or create a release tag in an ordinary feature PR.
6. Open a PR against `main`. Describe the trigger, resulting behavior and checks.

Discuss larger features in an issue before starting. Keep commits focused and
avoid unrelated formatting. Do not include generated logs, caches, model files,
personal config exports, credentials or research notes. CI runs on hosted runners
with read-only repository permissions; CodeQL gets permission to upload security
results. Review bots advise; they do not merge contributions. GitHub may ask the
maintainer to approve workflow runs from new contributors.

Settings updates select `main` revisions with passing push checks. Dependency
changes must update `runtime-requirements.json`, the installer and relevant tests.
Do not widen compatibility ranges without testing the affected runtime. Source
updates do not migrate installed configs or change system packages.

Code contributions use GPL-3.0. Preserve third-party notices. New fonts, icons,
images or other bundled assets need a source and documented redistribution terms.
Reviews may ask for changes; acceptance and timing remain the maintainer's choice.
