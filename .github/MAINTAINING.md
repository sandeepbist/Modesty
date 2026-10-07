# Maintaining Modesty

Use one branch per change and pull requests into `main`. CI and review bots help
find mistakes; the maintainer decides what merges and when a release is published.
Do not enable automatic merges or grant contributors write access just to accept PRs.

## Checks and review

| Check | Purpose |
| --- | --- |
| Quick checks | Release metadata, archive regressions, Python syntax, JavaScript regressions and workflow lint |
| Offline checks on Arch | Installer, updates, backend services and real QML loading on current Arch packages |
| CodeQL (python) | Security analysis of Python source |
| CodeQL (actions) | Security analysis of Actions workflows |

CodeQL does not check QML. Keep the real QML checks and native desktop review.
Hosted Arch checks run in disposable containers with no desktop credentials. The
container rebuilds stable Quickshell when Arch's Qt upgrade precedes its package
rebuild; this does not repair a contributor's machine or certify optional plugins.

For installer, update or runtime changes, also test the real installer as a normal
user with `python3 tests/installer-cli.py --isolated-home`. It needs the required
packages and services already installed. Check fresh install, repeat install,
cancellation, edited-config backups and uninstall. Check UI changes in Hyprland,
including reduced motion, rapid input and interruption of animations.

CodeRabbit configuration is advisory. Its GitHub App requires a separate
installation; the YAML file does not connect an account. Review the App's current
permissions and terms before connecting only this repository. It cannot replace
maintainer review. Automatic approval, label assignment, reviewer assignment,
docstring generation and test generation are disabled in this configuration.

Dependabot groups weekly Actions updates into reviewable PRs. Check the upstream
repository and new full commit SHA before merging. Arch packages, optional plugins
and voice model downloads are checked by Modesty's compatibility and installer
logic; this Dependabot configuration does not maintain those dependencies.

## One-time GitHub activation

Local configuration files do not change repository settings. Complete these steps
after approving and pushing the workflows, before the first release:

1. Let all four named checks complete on `main` and a PR. Review failed checks;
   do not mark them successful manually.
2. Update the existing main ruleset with the required checks in
   [main-ruleset.json](main-ruleset.json). Retain owner-only updates, code-owner
   review, resolved conversations and squash merges. Keep automatic merges off.
   The administrator bypass lets the sole owner merge their own PR because GitHub
   does not permit approving one's own PR. The owner must still inspect passing
   checks and perform local review before using that bypass.
3. In Settings → Environments, create **release**, add **@sandeepbist** as the
   required reviewer, and allow only protected branches. Leave **Prevent
   self-review** off so the sole maintainer can approve their own release run.
   Disable administrator bypass of environment protection. The workflow refuses
   packaging until the maintainer reviewer and protected-branch policy exist.
4. In Settings → General → Releases, enable **release immutability** before
   publishing. It locks published tags/assets and provides a signed release
   attestation. Drafts remain editable. Do not move or reuse a released tag.
5. Enable GitHub secret scanning and push protection in Settings → Security.
   Keep Actions tokens read-only by default and workflow PR approval off.
   Approve fork workflow runs only after inspecting their workflow changes.
6. Optionally connect CodeRabbit for this repository. Review its findings and
   permissions; leave merge control with the maintainer.

These settings need account-level activation. Nothing in this checklist claims
they are already enabled. Use advanced CodeQL through the supplied workflow;
do not also enable duplicate CodeQL default setup.

## Prepare a release

`VERSION` holds `X.Y.Z` or `X.Y.Z-rc.N`, without a `v` prefix. Tags use the same
version with `v` prepended. `0.1.0` is the proposed first release, not a published
release. Use patch versions for fixes, minor versions for compatible additions,
and document breaking changes explicitly. Before 1.0, minor versions may break
compatibility; every such change still needs migration instructions.

1. Create a release branch. Update `VERSION` and move reviewed changes from
   `[Unreleased]` into one matching `## [X.Y.Z]` section in `CHANGELOG.md`.
   Keep compatibility requirements, migration steps and known limitations clear.
   Update `runtime-requirements.json` only for runtimes that were tested.
2. Run `python3 scripts/release.py check` and `python3 tests/check.py`, then check
   install/uninstall and the native desktop. Open a PR and review all checks.
3. After merging, wait for **Checks** and **CodeQL** push runs to pass on the exact
   `main` commit. A PR run, older successful run or pending/failed rerun does not
   satisfy the release gate.
4. Create and push an annotated `vX.Y.Z` tag on that reviewed commit. Run **Release
   draft** manually from `main`, giving the existing tag. This workflow does not
   create tags or publish releases.
5. Approve the **release** environment job after inspecting the package job.
   It creates a draft containing `.tar.gz`, `.zip` and `SHA256SUMS`. Its notes come
   from the version's changelog section and include the exact source commit.
6. Download and verify the draft assets with `sha256sum -c SHA256SUMS`. Check that
   the tag still points to the source commit in the notes and that the installer,
   defaults, license and third-party notices are included. Review release notes,
   prerelease status and migration instructions. Publish manually when satisfied.

Packaging executes reviewed `main` tooling and reads the tagged source as data.
It verifies main ancestry and successful CI for the exact revision. Before creating
its draft, it checks the remote tag still points to the packaged commit. Existing
drafts are never overwritten automatically; inspect the cause before retrying.
Recheck the tag before publication because draft tags are still mutable.

For a local archive preview from a clean checkout with an existing tag:

```sh
python3 scripts/release.py build --tag v0.1.0 --output /tmp/modesty-v0.1.0
```

This creates files only. Add `--verify-ci` to enforce the same remote CI gate.
Outputs must stay outside the checkout and must not already exist. Archive content
comes from the tagged Git tree, excluding untracked and ignored files. Fixed UTC
timestamps make repeated builds reproducible on the same toolchain. Git/zlib
changes can change archive bytes; checksums identify the actual published files.
Checksums detect corruption, while GitHub's immutable release attestation verifies
origin and integrity. Neither establishes that software is free of bugs.

## Releases and Settings updates

Source archives are versioned installation snapshots. Keep their extracted path
stable if installing from an archive. They contain no system packages or voice
models, and they have no Git checkout for Settings updates.

Settings updates continue using passing `main` push revisions from the official
Git checkout. Publishing a release does not change that channel. Updates do not
migrate installed defaults, install system packages or rebuild plugins. Review
installer/runtime changes separately; do not promise support for an untested Qt,
Quickshell or Hyprland version.

If a release is faulty, publish a new patch release rather than replacing assets
or moving its tag. Document the affected versions and recovery steps. The Settings
rollback restores source only; it cannot undo a separate installer or system update.

References: [GitHub Actions security](https://docs.github.com/en/actions/reference/security/secure-use),
[release environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
[immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases),
[CodeRabbit configuration](https://docs.coderabbit.ai/reference/configuration).
