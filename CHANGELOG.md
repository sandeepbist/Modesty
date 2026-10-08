# Changelog

Versioned releases will be listed on [GitHub Releases](https://github.com/sandeepbist/Modesty/releases).
Entries are prepared before publishing. GitHub Releases records which versions have been published.

## [Unreleased]

### Fixed

- Thunar backgrounds and selection colors follow the active palette in both modes. Selected file labels use the matching foreground, and keyboard focus outlines remain visible. Named application palettes use the shell's selection foreground.
- Voice ribbons fade in when activated, including after panel travel and when reopening, instead of appearing at full brightness.
- Shift+Tab moves backwards through launcher results on platforms that send Tab with a Shift modifier.
- Image previews and lock/wallpaper images encode local paths, including filenames containing `#`, `?` and `%`.
- Stopping a hung recorder has a ten-second deadline and reports an incomplete video instead of remaining stuck while saving. Exited recorder processes no longer block restarting.
- Direct camera monitoring restarts after an unexpected helper exit; disabling capture activity cancels retries.
- Fish reads desktop color sequences from the configured XDG state directory.
- File drops keep a stable native target while the cue expands, so quick edge drops land on the first attempt. Drag ownership survives transitions between the surface and native target.
- Desktop startup no longer empties the user's trash automatically.
- Installer rejects clone/home paths containing shell or Lua metacharacters before any package or config changes, while keeping uninstall and recovery available.
- Installing Python through the bootstrap requires an explicit yes.
- Web results label Wikipedia only for wikipedia.org and its subdomains.
- Reload diagnostics show the runtime versions just validated, replacing stale details from an earlier update check.
- Calculator queries now wait for their scope bindings to settle before starting work. Closing search cancels queued and running calculations.
- Notification bursts retain the newest 50 history records after exit animations.

### Changed

- Luma search opens with a brief palette-colored sweep along its lower border, then stops rendering the effect. Voice and assistant work use soft lights around the rounded perimeter; hidden or disabled effects stop animating.
- Fluid motion uses native Qt springs for island morphs, launcher and power selection, button presses, switches and Settings page entrances. Gentle motion damps rebound; reduced motion remains instant. Volume/brightness feedback retains its short transition.
- Launcher uses a filled selection indicator and icon backgrounds. App descriptions are optional under Launcher settings and hidden by default.
- Required Arch CI installs the actual required package set and runs the real installer/uninstaller as a normal user in a disposable home.
- Removed unused portal-restart and legacy workspace/config helper scripts from installation templates.
- Qt6ct uses the Adwaita icon theme supplied by the installer.
- Artwork notices distinguish generated Atelier illustrations from downloaded Dragon Ball Legends artwork.
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
