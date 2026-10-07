#!/usr/bin/env python3
"""Interactive, backup-first Arch installer for the saved Modesty desktop."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import compatibility
import installation
from desktop_environment import clean_environment
HOME = Path.home()
SETUP = ROOT / "setup"
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state")
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")

CORE = "hyprland quickshell hyprpm networkmanager network-manager-applet bluez bluez-utils pipewire pipewire-pulse wireplumber brightnessctl foot fish starship matugen hyprsunset flameshot fuzzel cliphist wl-clipboard slurp grim wayland wayland-protocols wf-recorder gpu-screen-recorder ffmpeg playerctl cava polkit-gnome python-dbus python-gobject python-pillow qt6ct qt6-wayland qt6-imageformats qt6-multimedia xdg-desktop-portal-hyprland gnome-keyring trash-cli jq thunar xdg-utils poppler adw-gtk-theme ttf-material-symbols-variable ttf-jetbrains-mono-nerd noto-fonts-emoji git base-devel cmake ninja meson btop discord obsidian libqalculate lm_sensors ripgrep fastfetch chafa hyprpicker libnotify wtype bubblewrap".split()
EXTRAS = "spotify spicetify-cli zen-browser-bin pwvucontrol ttf-rubik-vf ttf-phosphor-icons tesseract tesseract-data-eng".split()
CORE += ["firefox", "pavucontrol", "adwaita-cursors", "adwaita-icon-theme", "upower", "xdg-desktop-portal-gtk"]
STATE_DEFAULTS = (
    "appearance.json", "bindings.json", "control-layout.json", "preferences.json",
    "sequences.txt", "theme.json", "wallpaper.json", "wallpaper-data.json", "wallpaper-palette.json",
)
PLUGINS = {
    "dynamic-cursors": "https://github.com/VirtCode/hypr-dynamic-cursors.git",
    "scrolloverview": "https://github.com/yayuuu/hyprland-scroll-overview.git",
}
PLUGIN_QUEUE = STATE / "modesty/plugins-pending.json"


def ask(label, default=True):
    suffix = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{label} [{suffix}] ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Enter y or n.")


def run(*args, cwd=None, env=None):
    print("$", " ".join(args))
    subprocess.run(args, check=True, cwd=cwd, env=env)


def install_voice():
    missing_uv = not shutil.which("uv")
    print('Local voice downloads Moonshine Small English and an isolated Python runtime.')
    print('Runtime: $XDG_DATA_HOME/modesty/stt-moonshine-venv (default ~/.local/share).')
    print('Models: $XDG_CACHE_HOME/modesty/voice-moonshine (default ~/.cache).')
    if missing_uv:
        print('Missing uv: installing it requires sudo pacman -Syu --needed uv, a full Arch upgrade.')
    if not ask("Install local English hold-to-talk for Luma (Moonshine Small CPU runtime)?", False):
        print('Local voice skipped.')
        return False
    if missing_uv:
        run("sudo", "pacman", "-Syu", "--needed", "uv")
    run("python3", str(ROOT / "scripts/luma-voice.py"), "--install")
    return True


def rebuild_quickshell(installed, unattended=False):
    package = next((p for p in ('quickshell', 'quickshell-git') if p in installed), None)
    if package is None:
        raise RuntimeError('No recognized Quickshell package to rebuild. Repair your custom package manually.')
    origin = ('https://gitlab.archlinux.org/archlinux/packaging/packages/quickshell.git'
              if package == 'quickshell' else 'https://aur.archlinux.org/quickshell-git.git')
    print(f'Rebuilding {package} for installed Qt; its package variant is preserved.')
    with tempfile.TemporaryDirectory(prefix='modesty-quickshell-') as folder:
        if shutil.disk_usage(folder).free < 3*1024**3:
            raise RuntimeError('Free at least 3 GiB in the temporary filesystem before rebuilding Quickshell. No dotfiles were changed.')
        checkout = Path(folder)/package
        run('git', 'clone', '--depth', '1', origin, str(checkout))
        build = checkout/'PKGBUILD'
        recipe = build.read_text()
        if package == 'quickshell' and re.search(r'(?m)^pkgver=0\.3\.1$', recipe) and re.search(r'(?m)^pkgrel=1$', recipe):
            # Official stable 0.3.1 predates this upstream Qt 6.12 fix. Keep
            # the release and backport the immutable, checksummed upstream patch.
            if re.search(r'(?m)^prepare\s*\(', recipe):
                raise RuntimeError('Stable package preparation changed. Repair it manually; no dotfiles were changed.')
            build.write_text(recipe+'''\n# Backport upstream Qt 6.12 compatibility to stable 0.3.1.
pkgrel="${pkgrel}.1"
source+=("quickshell-qt6.12.patch::https://github.com/quickshell-mirror/quickshell/commit/5d5d49873fe8cf1f99ddfd5006ceb2057c5c9b13.patch")
sha256sums+=("b8a7eab0f883070a26283140e06d252a0aa3483287c54bbb0c3aacb6e82eb0b2")
prepare() {
    GIT_CEILING_DIRECTORIES="$srcdir" git -C "$srcdir/quickshell" apply --exclude=changelog/next.md "$srcdir/quickshell-qt6.12.patch"
}
''')
        build_env = clean_environment()
        build_env.setdefault('CMAKE_BUILD_PARALLEL_LEVEL', '2')
        run('makepkg', '-si', *(['--noconfirm'] if unattended else []), cwd=checkout, env=build_env)


def aur_helper():
    helper = shutil.which("paru") or shutil.which("yay")
    if helper:
        return helper
    print('No AUR helper found. Proposed fix: build yay from https://aur.archlinux.org/yay.git as your user, then install it with sudo.')
    if not ask("Install yay from the AUR for optional apps?", False):
        return None
    with tempfile.TemporaryDirectory(prefix="modesty-yay-") as folder:
        checkout = Path(folder) / "yay"
        run("git", "clone", "https://aur.archlinux.org/yay.git", str(checkout))
        run("makepkg", "-si", cwd=checkout)
    return shutil.which("yay")


def installed_packages():
    result = subprocess.run(["pacman", "-Qq"], capture_output=True, text=True, check=True)
    return set(result.stdout.splitlines())


def missing_core(installed):
    alternatives = {"hyprland": ("hyprland-git",), "quickshell": ("quickshell-git",),
                    "hyprpm": ("hyprpm-git",), "firefox": ("zen-browser-bin", "zen-browser")}
    return [p for p in CORE if p not in installed and not any(name in installed for name in alternatives.get(p, ()))]


def plugin_status():
    if not shutil.which("hyprpm"):
        return {}
    result = subprocess.run(["hyprpm", "list"], capture_output=True, text=True)
    output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout + result.stderr)
    status = {}
    for match in re.finditer(r"^[^\w\n]*Plugin\s+([^\s:]+)(.*?)(?=^[^\w\n]*Plugin\s+|\Z)", output, re.S | re.M):
        enabled = re.search(r"enabled:\s*(true|false)", match.group(2))
        status[match.group(1)] = bool(enabled and enabled.group(1) == "true")
    return status


def missing_plugins():
    status = plugin_status()
    return [name for name in PLUGINS if not status.get(name)]


def install_plugins(names):
    # hyprpm needs a running compositor with the same ABI as its installed binary.
    if not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
        raise RuntimeError('Plugin setup needs a running Hyprland session. Log in, then rerun --finish-plugins.')
    compatibility.require(ROOT)
    print('Selected plugins:', ', '.join(names))
    for name in names:
        print('Source:', PLUGINS[name])
    print('hyprpm update refreshes all registered plugin repositories and headers. Selected plugins will be built/enabled; Hyprland will reload.')
    if not ask('Proceed with these plugin changes?', False):
        print('Plugin setup deferred; the pending selection was kept.')
        return False
    run("hyprpm", "update")
    for name in names:
        if name not in plugin_status():
            run("hyprpm", "add", PLUGINS[name])
        if not plugin_status().get(name):
            run("hyprpm", "enable", name)
    if any(name in missing_plugins() for name in names):
        raise RuntimeError("Selected plugins did not build or enable. Rerun the installer to retry.")
    run("hyprpm", "reload")
    run("hyprctl", "reload")
    return True


def choose_groups():
    return [name for name, label in (
        ("desktop", "Install saved Hyprland keybinds, window rules and layout?"),
        ("shell", "Install Modesty settings, themes and terminal artwork?"),
        ("apps", "Install foot, fish, GTK/Qt, Flameshot and prompt settings?"),
        ("wallpapers", "Install the wallpapers supplied with this repo?"),
        ("spotify", "Install Spotify theme files?"),
        ("fonts", "Install bundled fonts for other apps?"),
    ) if ask(label)]


def choose_plugins():
    return [name for name, label in (
        ("dynamic-cursors", "Install optional dynamic cursor effects with the bundled stretch/shake settings?"),
        ("scrolloverview", "Install optional Super+Tab window overview with the bundled layout settings?"),
    ) if ask(label, False)]


def save_plugin_queue(names):
    PLUGIN_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=PLUGIN_QUEUE.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(json.dumps(names).encode())
    os.replace(temporary, PLUGIN_QUEUE)


def missing_services():
    return [name for name in ("NetworkManager", "bluetooth")
            if subprocess.run(["systemctl", "is-enabled", "--quiet", name]).returncode != 0]


def files_for(group):
    if group == "desktop":
        return [SETUP / "desktop/main-shell"] + sorted((SETUP / "config/hypr").rglob("*")) + sorted((SETUP / "config/modesty/desktop").rglob("*"))
    if group == "shell":
        paths = [SETUP / "config/modesty/cava.conf", SETUP / "config/modesty/emoji-list.txt", SETUP / "config/modesty/session.json"]
        paths += sorted((SETUP / "config/modesty/terminal").rglob("*"))
        paths += [SETUP / "state/modesty" / name for name in STATE_DEFAULTS]
        return paths
    if group == "apps":
        paths = []
        for name in ("foot", "fish", "gtk-3.0", "qt6ct", "flameshot", "fastfetch"):
            paths += sorted((SETUP / "config" / name).rglob("*"))
        paths.append(SETUP / "config/starship.toml")
        return paths
    if group == "spotify":
        return sorted((SETUP / "config/spicetify").rglob("*"))
    if group == "wallpapers":
        return sorted((SETUP / "wallpapers").rglob("*"))
    if group == "fonts":
        return sorted((ROOT / "assets/fonts").glob("*.ttf"))
    raise ValueError(group)


def destination(source, group):
    if source == SETUP / "desktop/main-shell":
        return STATE / "modesty/main-shell"
    if group == "wallpapers":
        return HOME / "Pictures/Wallpapers" / source.relative_to(SETUP / "wallpapers")
    if group == "fonts":
        return HOME / ".local/share/fonts/modesty" / source.name
    relative = source.relative_to(SETUP)
    if relative.parts[0] == "config":
        return CONFIG.joinpath(*relative.parts[1:])
    return STATE.joinpath(*relative.parts[1:])


def rendered(source):
    raw = source.read_bytes()
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw
    return value.replace("@MODESTY_ROOT@", str(ROOT)).replace("@HOME@", str(HOME)).encode()


def planned_files(groups):
    files = [(source, destination(source, group)) for group in groups
             for source in files_for(group) if source.is_file()]
    if "wallpapers" not in groups:
        # Keep the user's current wallpaper selection and its matching palettes.
        files = [(source, target) for source, target in files if source.name not in
                 {"wallpaper.json", "wallpaper-data.json", "wallpaper-palette.json"}]
    return files


def install_files(groups, dry_run):
    return installation.install(planned_files(groups), rendered, ROOT, HOME, STATE, dry_run)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show changes without installing")
    parser.add_argument("--non-interactive", action="store_true", help="install all saved files only when dependencies are ready")
    parser.add_argument("--finish-plugins", action="store_true", help="build the plugins selected during installation after Hyprland starts")
    parser.add_argument("--install-voice", action="store_true", help="install only optional local voice and its dependencies")
    parser.add_argument("--uninstall", action="store_true", help="back up current installed files and restore recorded originals")
    parser.add_argument("--adopt-existing", action="store_true", help="record exact template matches from an older installation; originals remain unknown")
    parser.add_argument("--recover-install", action="store_true", help="back up surviving files and restore an interrupted file transaction")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as your desktop user, not root; the installer uses sudo only for packages.")
    maintenance = args.uninstall or args.adopt_existing or args.recover_install
    if not maintenance and not shutil.which("pacman"):
        parser.error("This installer needs Arch Linux and pacman.")
    if any(c.isspace() for c in str(ROOT) + str(HOME)):
        parser.error("Clone path and home directory must not contain whitespace because Hyprland keybind commands use them.")
    if CONFIG != HOME / ".config":
        parser.error("This saved Hyprland config requires the default ~/.config directory; unset XDG_CONFIG_HOME before installing.")
    if maintenance:
        if sum((args.uninstall, args.adopt_existing, args.recover_install)) != 1 or args.finish_plugins or args.install_voice:
            parser.error('Choose only one uninstall, adoption or recovery operation.')
        if args.adopt_existing:
            files = planned_files(["desktop", "shell", "apps", "spotify", "wallpapers", "fonts"])
            installation.adopt(files, rendered, ROOT, HOME, STATE, True)
            if not args.dry_run and (args.non_interactive or ask('Adopt exact matches? Originals are unknown; uninstall will back up these files before removal.', False)):
                installation.adopt(files, rendered, ROOT, HOME, STATE)
        elif args.uninstall:
            installation.uninstall(ROOT, HOME, STATE, True)
            if not args.dry_run and (args.non_interactive or ask('Back up installed files, restore originals and uninstall?', False)):
                # Refuse before stopping anything if a required original is unavailable.
                files = installation.uninstall_plan(ROOT, HOME, STATE)
                installation.require_space(files, STATE, removing=True)
                spec = importlib.util.spec_from_file_location('uninstall_session', ROOT/'scripts/session-control.py')
                control = importlib.util.module_from_spec(spec); spec.loader.exec_module(control)
                running = control.health()
                if running:
                    control.assert_unlocked()
                    from updates import busy_work
                    busy_work()
                    control.stop_modesty()
                try:
                    installation.uninstall(ROOT, HOME, STATE)
                except Exception:
                    if running and not (STATE/'modesty-install/transaction.json').exists():
                        control.start()
                    raise
        else:
            pending = (STATE/'modesty-install/transaction.json').is_file()
            installation.recover(ROOT, HOME, STATE, True)
            if pending and not args.dry_run and (args.non_interactive or ask('Back up surviving files and recover the interrupted transaction?', False)):
                with installation.locked(STATE):
                    installation.recover(ROOT, HOME, STATE)
        return
    if args.install_voice:
        if args.dry_run or args.non_interactive or args.finish_plugins:
            parser.error("--install-voice requires interactive setup")
        try:
            if install_voice():
                print("Local English voice installed. Hold Ctrl + backtick in Luma to speak.")
            else:
                raise SystemExit(130)
        except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
            print(f"Voice setup failed: {error}. Retry from Settings → Voice.")
            raise
        finally:
            if sys.stdin.isatty():
                input("Press Enter to close setup.")
        return
    if args.finish_plugins:
        if args.dry_run or args.non_interactive:
            parser.error("--finish-plugins requires an interactive terminal")
        if not PLUGIN_QUEUE.exists():
            print("No plugin installation pending.")
            return
        names = json.loads(PLUGIN_QUEUE.read_text())
        if not isinstance(names, list) or not names or any(name not in PLUGINS for name in names):
            raise RuntimeError("Invalid pending plugin selection.")
        try:
            completed = install_plugins(names)
        except (subprocess.CalledProcessError, RuntimeError) as error:
            print(f"Plugin setup failed: {error}. Your desktop still works. Rerun with --finish-plugins to retry.")
            input("Press Enter to close this window.")
            raise
        if completed:
            PLUGIN_QUEUE.unlink()
        input("Selected plugins installed. Press Enter to close this window." if completed else "Plugin setup deferred. Press Enter to close this window.")
        return
    print(f"Modesty desktop installer\nRepository: {ROOT}\nHome: {HOME}")

    installed = installed_packages()
    core = missing_core(installed)
    extras = [p for p in EXTRAS if p not in installed]
    print("Required packages:", ", ".join(core) if core else "all installed")
    print("Optional extras:", ", ".join(extras) if extras else "all installed")
    if args.dry_run:
        print("Optional local voice: isolated Moonshine Small CPU runtime and model (installed on request)")
        print("Hyprland plugins:", ", ".join(missing_plugins()) or "both present")
        print("System services:", ", ".join(missing_services()) or "both enabled")
        print("Python modules:", ", ".join(name for name in ("dbus", "gi") if importlib.util.find_spec(name) is None) or "both present")
        install_files(["desktop", "shell", "apps", "spotify", "wallpapers", "fonts"], True)
        return

    if core:
        print('Proposed fix: install the listed required packages with a full Arch upgrade. File rollback does not undo package changes.')
        if args.non_interactive or not ask("Update Arch and install required packages before dotfiles?", False):
            raise RuntimeError("Required packages are missing; no dotfiles were changed.")
        run("sudo", "pacman", "-Syu", "--needed", *core)
        installed = installed_packages()
        core = missing_core(installed)
        if core:
            raise RuntimeError("Required packages still missing: " + ", ".join(core))
    else:
        print("Required packages ready.")

    if not args.non_interactive:
        install_voice()

    if extras and not args.non_interactive and ask("Install optional apps, Spotify tools, and extra fonts?", False):
        helper = aur_helper()
        if not helper:
            print("An AUR helper is needed for optional extras. Install paru/yay, then rerun for those apps.")
        else:
            run(helper, "-S", "--needed", *extras)

    if importlib.util.find_spec("dbus") is None or importlib.util.find_spec("gi") is None:
        raise RuntimeError("Python D-Bus/GObject modules unavailable; no dotfiles were changed.")
    services = missing_services()
    if services:
        print("Disabled system services:", ", ".join(services))
        print('Proposed fix: enable and start these services now and on future boots. Existing network management may need manual review.')
        if args.non_interactive or not ask("Enable these services before dotfiles?", False):
            raise RuntimeError("Required services are disabled; no dotfiles were changed.")
        run("sudo", "systemctl", "enable", "--now", *services)
        if missing_services():
            raise RuntimeError("Required services could not be enabled; no dotfiles were changed.")
    if args.non_interactive:
        groups = ["desktop", "shell", "apps", "spotify", "wallpapers", "fonts"]
    else:
        groups = choose_groups()
        if not groups:
            print("No dotfiles changed.")
            return
    plugins = choose_plugins() if not args.non_interactive and "desktop" in groups else []
    if any(group in groups for group in ('desktop', 'shell')):
        compatibility.require(ROOT, live=False)
        spec = importlib.util.spec_from_file_location('install_session', ROOT/'scripts/session-control.py')
        control = importlib.util.module_from_spec(spec); spec.loader.exec_module(control)
        try:
            control.validate_shell(headless=not bool(os.environ.get('WAYLAND_DISPLAY')))
        except compatibility.QtMismatch as error:
            print(error)
            print('Proposed fix: rebuild the installed stable/git Quickshell variant as your user, installing build dependencies and the rebuilt package with sudo. Needs at least 3 GiB temporary space; configs wait for validation.')
            if args.non_interactive or not ask('Rebuild your installed Quickshell variant for current Qt? Source compilation may take several minutes.', False):
                raise
            rebuild_quickshell(installed_packages())
            compatibility.require(ROOT, live=False)
            control.validate_shell(headless=not bool(os.environ.get('WAYLAND_DISPLAY')))
    if not args.non_interactive:
        install_files(groups, True)
        print('Existing files will be backed up before replacement. Backup location:', STATE/'modesty-install-backups')
        if not ask("Apply these files with backups for existing files?", False):
            print('No dotfiles changed. Earlier approved package, service or voice steps are retained.')
            return
    install_files(groups, False)
    if not args.non_interactive and "desktop" in groups and not plugins:
        PLUGIN_QUEUE.unlink(missing_ok=True)
    if plugins:
        save_plugin_queue(plugins)
        # Fresh TTY installs cannot use hyprpm until the first compositor login.
        if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            try:
                if install_plugins(plugins):
                    PLUGIN_QUEUE.unlink()
            except (subprocess.CalledProcessError, RuntimeError) as error:
                print(f"Optional plugins need a retry: {error}")
        if PLUGIN_QUEUE.exists():
            print("Selected plugins will install in a terminal on your next Hyprland login.")
            print("Manual retry:", shlex.join(["python3", str(ROOT / "install.py"), "--finish-plugins"]))
    if "fonts" in groups and shutil.which("fc-cache"):
        run("fc-cache", "-f", str(HOME / ".local/share/fonts/modesty"))
    print("Install complete. Log out and start a Hyprland session to load Modesty and saved keybinds.")
    print("Network, Bluetooth, Spotify and keyring accounts need your normal sign-in on the new machine.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
    except (RuntimeError, ValueError, subprocess.CalledProcessError, OSError) as exc:
        print("Install stopped:", exc, file=sys.stderr)
        sys.exit(1)
