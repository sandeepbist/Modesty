# Modesty

A Quickshell desktop for Arch Linux and Hyprland. Three small pills expand into
media controls, a calendar and a control center. Modesty also includes a launcher,
Luma search and assistant, notifications, a lock screen and a window companion.

![Modesty control center on the maintainer's desktop](assets/showcase/controls.png)

**[Install](#install) · [Screenshots and video](#screenshots-and-video) ·
[Contribute](.github/CONTRIBUTING.md) ·
[Report a bug](https://github.com/sandeepbist/Modesty/issues/new/choose)**

## Install

Start with **x86_64 Arch Linux**, working graphics drivers, a normal user account,
internet access and sudo. The installer sets up desktop configs and dependencies.
It does not install Arch, graphics drivers, a bootloader or a login manager.

```sh
sudo pacman -Syu --needed git
git clone https://github.com/sandeepbist/Modesty.git ~/App/Modesty
cd ~/App/Modesty
./install.sh
```

Run as your desktop user, not root. The installer walks you through:

1. Required Arch packages and NetworkManager/Bluetooth services.
2. Which configs to install: desktop, shell, apps, fonts and Spotify theme.
3. Whether to install the supplied wallpapers or keep your existing selection.
4. Optional cursor effects and the Super + Tab window overview.
5. Optional local speech recognition for Luma.

Existing files are backed up before replacement. Package installation uses a full
Arch update. AUR apps and local voice are separate choices. Review planned file
changes without writing anything with `./install.sh --dry-run`.

After installation, **log out and select Hyprland** in your login manager, or run
`start-hyprland` from a TTY. Keep the checkout at the same path: startup and
shortcuts use it. Home and checkout paths must not contain whitespace. This
profile uses `~/.config`; unset `XDG_CONFIG_HOME` before installing.

The profile uses Hyprland's Lua configuration. Monitor arrangement, scale,
brightness permissions and suspend/hibernate support depend on your hardware.
Set those for your machine. Firefox, Pavucontrol and Adwaita cursors are defaults;
installed Zen and Pwvucontrol take priority.

### Optional plugins

The installer asks separately about
[dynamic cursor effects](https://github.com/VirtCode/hypr-dynamic-cursors) and
[window overview](https://github.com/yayuuu/hyprland-scroll-overview).
It builds and enables selected plugins through `hyprpm`, with Modesty's settings.

On a fresh TTY install, plugin setup finishes after your first Hyprland login.
A terminal opens automatically; enter your sudo password if requested. If an
upstream build fails, the desktop stays usable. Retry from the checkout:

```sh
python3 install.py --finish-plugins
```

Run `hyprpm update` after compositor updates. Plugin compatibility depends on
upstream. Both plugins are optional.

### Optional local voice

Choose voice during installation, or open **Settings → Luma → Voice → Install
local voice** later. Setup downloads and verifies Moonshine Small English and
installs an isolated CPU runtime. The panel also offers repair/retry. Terminal
setup uses the same installer:

```sh
python3 install.py --install-voice
```

Hold **Ctrl + backtick** to speak to Luma; release to submit. Transcription runs
locally and needs no API key. Voice loads on demand; Settings can keep it ready.
Models and the Python environment stay outside the checkout.

**Luma's AI answers use your configured cloud provider.** Submitted speech becomes
text sent to that provider, together with enabled context and tool results.
Local speech recognition does not make the assistant itself local. Application
launching, calculations and local search work without an AI key.

## Use

| Input | Opens |
| --- | --- |
| Album-art pill | Media controls |
| Clock pill | Clock; calendar available from the clock panel |
| Status pill | Control center |
| Tap Super | Application launcher |
| Super + Space | Luma search and assistant |
| Super + comma | Settings |
| Super + L | Lock screen |
| Escape / outside click | Dismiss the current panel |

Volume and brightness changes temporarily widen the clock pill. Settings controls
spacing, motion, colors, control-center layout, notifications and the companion.
Reduced motion is supported. Microphone/camera activity appears while capture is
active; the privacy panel provides microphone mute controls.

Luma searches applications, files, file contents and clipboard entries, handles
calculations and web search, and can perform desktop actions. Configure an
optional provider key in Settings. Desktop access defaults to **Review**, and
knowledge folders start empty. Every generic command asks for confirmation in
Review mode. Full access allows broader automatic actions; enable it deliberately.
See [security and privacy](.github/SECURITY.md) before enabling AI context/tools.

**Agent activity tracking currently works with T3 Code only.** Modesty reads task
status metadata to show working, waiting and completion feedback; it does not
read T3 prompts or credentials. Standalone Codex, Claude Code and OpenCode CLI
integration is planned and is not implemented yet.

## Screenshots and video

Captured from the maintainer's live Hyprland desktop, using the installed shell
and personal wallpaper. The installer supplies a separate, credited wallpaper
collection. Colors, panel layout and apps can differ on your machine.

| Calendar | Themes |
| --- | --- |
| ![Live calendar panel](assets/showcase/calendar.png) | ![Live theme picker](assets/showcase/themes.png) |

| Launcher | Local voice setup |
| --- | --- |
| ![Live application launcher](assets/showcase/launcher.png) | ![Local voice settings on the live desktop](assets/showcase/voice.png) |

[![Watch island transitions](assets/showcase/island.gif)](assets/showcase/island.mp4)

[Watch the full-resolution clip](assets/showcase/island.mp4) ·
[Watch volume and brightness transitions](assets/showcase/sliders.mp4)

## Customize, update and restore

User preferences live in `$XDG_STATE_HOME/modesty`, normally
`~/.local/state/modesty`. Change apps and shortcuts in
`~/.config/modesty/desktop/hypr-vars.lua`. Public installation templates live in
`setup/`; the installer does not copy the maintainer's live home directory.
Keys, saved network credentials, Bluetooth pairings, conversations, personal
notes and model caches are not part of the install.

To update, pull changes and run the installer again. It skips identical files
and backs up files it replaces. Review any custom config changes before applying.
Restart an existing Modesty session after code changes:

```sh
git pull --ff-only
./install.sh
python3 scripts/session-control.py restart
```

Backups live under `~/.local/state/modesty-install-backups/<timestamp>/`
(or your custom state directory). Restore relevant files from that backup to
undo installation, then log in again. Declining wallpapers preserves your
existing wallpaper and palette. Spotify needs a separate installation and first
launch before `spicetify backup apply` can apply its theme.

For an existing Caelestia Lua setup, `./launch.sh --switch` performs a reversible
shell handoff; `./launch.sh --restore` restores that handoff when its backup exists.
A fresh installation does not require Caelestia.

## Troubleshooting

- **The shell did not start:** from the checkout, run
  `quickshell ipc -p "$PWD/shell.qml" call island health`. If no instance exists,
  run `python3 scripts/session-control.py restart` and keep its error output.
- **A plugin failed to build:** retry `python3 install.py --finish-plugins` after
  checking compatibility with your Hyprland version.
- **Voice is missing:** use Install/Repair under Settings → Luma → Voice.
- **An external monitor has no brightness slider:** DDC brightness is not
  implemented. The built-in slider uses supported backlight devices.

The installer has been exercised on a clean Arch container; UI and audio have
also been checked on the maintainer's desktop. Containers cannot verify physical
GPU drivers, login behavior or every hardware setup. If installation fails,
[open an issue](https://github.com/sandeepbist/Modesty/issues/new/choose) with the
command, error and package versions. Remove keys and personal data from logs.

## Contribute

Bug reports, small fixes, accessibility improvements and feature proposals are
welcome. Read [the contribution guide](.github/CONTRIBUTING.md), fork the repo and
open a pull request. Discuss larger changes in an issue first. **The maintainer
reviews and merges contributions.** Opening a PR does not grant write access.

Run offline checks before submitting code:

```sh
python3 tests/check.py
```

Checks need desktop dependencies and Node.js. They cover installer backups,
template isolation, backend behavior, isolated D-Bus services, security boundaries
and QML loading. Live input/hardware checks require explicit `--live` and are not
part of this command. QML loading checks do not replace visual review.

`services/` owns shared state; `modules/` owns UI; `components/` and `theme/` contain
shared visuals; `scripts/` handles system integration; `setup/` contains portable
installation defaults. Research, private notes and disposable outputs stay out
of the public source tree.

## License and credits

Modesty code and adapted configs use [GPL-3.0](LICENSE). Hyprland configs are
adapted from [Caelestia](https://github.com/caelestia-dots/caelestia). Fonts,
icons, vendored code and third-party images retain their own terms; see
[third-party notices](THIRD_PARTY.md).
