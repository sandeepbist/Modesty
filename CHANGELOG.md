# Changelog

Versioned releases will be listed on [GitHub Releases](https://github.com/sandeepbist/Modesty/releases).
Entries are prepared before publishing. GitHub Releases records which versions have been published.

## [Unreleased]

### Fixed

- Calculator queries now wait for their scope bindings to settle before starting work. Closing search cancels queued and running calculations.
- Notification bursts retain the newest 50 history records after exit animations.

### Changed

- Conversation updates preserve unchanged model rows and create only the message view each role needs.
- Control tiles create level sliders and media artwork only when their tile kind needs them.
- Inactive island panels skip resize callbacks; lyric lookup reuses its position index and visualizer bars skip identical frames.

## [0.1.0]

### Added

- Three expanding island pills, media controls, calendar, notifications and control center.
- Application launcher, Luma search and assistant, local Moonshine Small voice input, and window companion.
- Microphone/camera activity indicators, microphone mute controls and lock screen.
- Interactive installation with optional wallpapers, voice and Hyprland plugins.
- Config backups, installation receipts, recovery previews and backup-first uninstall.
- Settings source updates with compatibility checks, reload and rollback.
- Versioned source downloads, SHA-256 checksums and maintainer-reviewed release drafts.

### Compatibility and limitations

- x86_64 Arch Linux, Hyprland 0.56.x and Quickshell 0.3.1 or newer within 0.3.x.
- Speech recognition is local; AI answers use the user's configured cloud provider.
- Agent activity tracking supports T3 Code. Standalone CLI integrations are planned.
- External DDC brightness is not implemented. Optional plugin builds depend on upstream compatibility.
- Updates preserve installed configs and packages. Apply new defaults separately through the interactive installer.
- Git source archives are snapshots. Automatic Settings updates require the official Git checkout on `main`.

The installation guide and third-party notices are included in each source archive.
