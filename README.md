# Modesty

A Quickshell desktop island and dotfiles for Arch Linux and Hyprland. Three pills
show media, clock, and system status, with animated panels, a launcher, Luma
search and assistant, notifications, lock screen, themes, and an optional window
companion.

## Install on Arch Linux

Start with an installed **x86_64 Arch Linux** system, working graphics drivers,
a normal user account, internet access, and sudo. This installs desktop configs;
it does not install Arch itself, GPU drivers, a bootloader, or a login manager.

```sh
sudo pacman -Syu --needed git
git clone https://github.com/sandeepbist/Modesty.git ~/App/Modesty
cd ~/App/Modesty
./install.sh --dry-run
./install.sh
```

Run as your desktop user, not root. Keep the checkout in place: startup and
shortcuts refer to its absolute path. Home and checkout paths must not contain
whitespace. This Hyprland profile uses the default `~/.config`; unset
`XDG_CONFIG_HOME` before installing.

The guided installer checks official Arch packages, Python D-Bus/GObject modules,
and NetworkManager/Bluetooth services before copying files. Package installation
uses a full Arch update. Optional AUR apps, fonts, Spotify tools, and local voice
are separate choices. You can choose Hyprland, shell preferences, app configs,
wallpapers, Spotify theme, and fonts. `--non-interactive` copies all groups only
when required packages and services are already ready; it never installs packages.

Installation copies the reviewed templates in `setup/`, replacing `@HOME@` and
`@MODESTY_ROOT@` for your machine. It does not export the maintainer's current
home directory. Existing files and symlinks are backed up under
`~/.local/state/modesty-install-backups/<timestamp>/`; identical files are skipped.
Restore individual files from that directory to undo installation.

Log out, then select **Hyprland** in your login manager, or run `start-hyprland`
from a TTY. Current Arch Hyprland supports the bundled Lua config. Monitor
arrangements, scale, brightness access, and suspend/hibernate support depend on
your hardware. Configure these for your machine as needed.

Firefox and Pavucontrol are working defaults; installed Zen and Pwvucontrol take
priority. The cursor default is Adwaita. Change apps and shortcuts in
`~/.config/modesty/desktop/hypr-vars.lua`. Optional Zen, Spotify and other AUR apps
need their own installation and sign-in. After Spotify has created its preferences,
run `spicetify backup apply` to activate the bundled theme.

The installer includes no API keys, passwords, keyrings, saved network credentials,
Bluetooth pairings, conversations, personal notes, or model caches. Luma AI needs
an optional provider key configured in Settings. Keys stay outside this repo.
Desktop actions default to review; personal knowledge folders start empty.
Preferences persist in `$XDG_STATE_HOME/modesty`, normally `~/.local/state/modesty`.

### Optional Hyprland plugins

The desktop runs without plugins. Dynamic cursor effects and Super+Tab overview
need matching plugins. After logging into Hyprland, install them with:

```sh
hyprpm add https://github.com/VirtCode/hypr-dynamic-cursors.git
hyprpm add https://github.com/yayuuu/hyprland-scroll-overview.git
hyprpm update
hyprpm enable dynamic-cursors
hyprpm enable scrolloverview
hyprpm reload
hyprctl reload
```

Startup runs `hyprpm reload`; plugin settings are guarded when plugins are absent.
Rebuild plugins with `hyprpm update` after compositor updates. Builds and version
compatibility are controlled by each plugin's upstream. See the
[Hyprland plugin guide](https://wiki.hypr.land/Plugins/Using-Plugins/).

### Optional local voice

Hold **Ctrl + backtick** to speak to Luma; release to submit. The installer offers
an isolated Moonshine Small English CPU runtime. Manual setup:

```sh
sudo pacman -Syu --needed uv
python3 scripts/luma-voice.py --install
```

Model downloads and the Python environment stay in local user storage. Voice is
loaded on demand; Settings can keep it ready. Text search does not start voice.

## Use

| Input | Result |
| --- | --- |
| Click album art | Media player |
| Click clock | Calendar |
| Click status circle | Control center |
| Tap Super | Application launcher |
| Super + Space | Luma search and assistant |
| Super + comma | Settings |
| Super + L | Lock |
| Escape / outside click | Dismiss panel |

Volume and brightness events widen the clock pill. Hover moves pills slightly.
Panels support reduced motion. Settings controls geometry, motion, appearance,
control-center layout, notifications, and the optional window companion.
Luma supports files, file contents, clipboard, calculations, web search and
conversation. NetworkManager, BlueZ, PipeWire, MPRIS, Matugen and Hyprsunset provide
system integrations. External-monitor DDC brightness is not implemented.

```sh
python3 scripts/session-control.py restart
quickshell ipc -p "$PWD/shell.qml" call island health
```

For an existing Caelestia Lua setup, `./launch.sh --switch` performs a reversible
shell handoff. `./launch.sh --restore` restores that handoff only when its backup
exists. Fresh installation does not require Caelestia. The internal compatibility
shortcut names are handled by Modesty itself.

Environment overrides: `MODESTY_SCREEN`, `MODESTY_WALLPAPERS`, and
`MODESTY_REDUCED_MOTION=1`.

## Development

```sh
python3 tests/check.py
```

The runner checks installer backups and template isolation, offline backends,
interaction state, isolated D-Bus behavior, and QML loading. It needs the desktop
dependencies and Node.js. Live input and hardware checks require explicit
`--live` and are excluded. QML loading checks require a completion marker and no
errors; they do not prove visual quality or every hardware configuration.

`services/` owns shared state, `modules/` owns UI, `components/` and `theme/` provide
shared visuals, `scripts/` handles system integration, and `setup/` contains public
installation templates. Research and private development notes stay ignored.

Inter and Sacramento include their SIL OFL licenses under `assets/fonts/`.
Lucide icons retain their license under `assets/icons/lucide/`. Vendored fuzzysort
retains its MIT license in its source. Companion artwork is generated illustration
with native QML animation.
