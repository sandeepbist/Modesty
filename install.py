#!/usr/bin/env python3
"""Interactive, backup-first Arch installer for the saved Modesty desktop."""
import argparse
import datetime as dt
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
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


def run(*args, cwd=None):
    print("$", " ".join(args))
    subprocess.run(args, check=True, cwd=cwd)


def aur_helper():
    helper = shutil.which("paru") or shutil.which("yay")
    if helper:
        return helper
    if not ask("Install yay from the AUR for optional apps?", True):
        return None
    with tempfile.TemporaryDirectory(prefix="modesty-yay-") as folder:
        checkout = Path(folder) / "yay"
        run("git", "clone", "https://aur.archlinux.org/yay.git", str(checkout))
        run("makepkg", "-si", "--noconfirm", cwd=checkout)
    return shutil.which("yay")


def installed_packages():
    result = subprocess.run(["pacman", "-Qq"], capture_output=True, text=True, check=True)
    return set(result.stdout.splitlines())


def missing_core(installed):
    alternatives = {"hyprland": "hyprland-git", "quickshell": "quickshell-git", "hyprpm": "hyprpm-git"}
    return [p for p in CORE if p not in installed and alternatives.get(p) not in installed]


def missing_plugins():
    if not shutil.which("hyprpm"):
        return list(PLUGINS)
    result = subprocess.run(["hyprpm", "list"], capture_output=True, text=True)
    output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout + result.stderr)
    blocks = output.split("Repository ")
    return [name for name in PLUGINS if not any(("Plugin " + name) in block and "enabled: true" in block for block in blocks)]


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


def backup_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        destination.symlink_to(os.readlink(source))
    else:
        shutil.copy2(source, destination)


def install_files(groups, dry_run):
    files = [(source, destination(source, group)) for group in groups
             for source in files_for(group) if source.is_file()]
    for _, target in files:
        if target.is_dir() and not target.is_symlink():
            raise RuntimeError(f"Destination is a directory: {target}; no dotfiles were changed.")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = STATE / "modesty-install-backups" / stamp
    writes = 0
    backed_up = 0
    for source, target in files:
        content = rendered(source)
        if target.is_file() and not target.is_symlink() and target.read_bytes() == content:
            continue
        if dry_run:
            print("Would install", target)
            writes += 1
            continue
        if target.exists() or target.is_symlink():
            relative = target.relative_to(HOME) if target.is_relative_to(HOME) else Path("state") / target.relative_to(STATE)
            backup_file(target, backup / relative)
            backed_up += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".modesty-", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
            temporary.chmod(source.stat().st_mode & 0o777)
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        writes += 1
    print(f"{'Planned' if dry_run else 'Installed'} {writes} files; backed up {backed_up} existing files" + (f" to {backup}" if backed_up else "") + ".")
    return writes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show changes without installing")
    parser.add_argument("--non-interactive", action="store_true", help="install all saved files only when dependencies are ready")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as your desktop user, not root; the installer uses sudo only for packages.")
    if not shutil.which("pacman"):
        parser.error("This installer needs Arch Linux and pacman.")
    if any(c.isspace() for c in str(ROOT) + str(HOME)):
        parser.error("Clone path and home directory must not contain whitespace because Hyprland keybind commands use them.")
    if CONFIG != HOME / ".config":
        parser.error("This saved Hyprland config requires the default ~/.config directory; unset XDG_CONFIG_HOME before installing.")
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
        if args.non_interactive or not ask("Update Arch and install required packages before dotfiles?", True):
            raise RuntimeError("Required packages are missing; no dotfiles were changed.")
        run("sudo", "pacman", "-Syu", "--needed", *core)
        installed = installed_packages()
        core = missing_core(installed)
        if core:
            raise RuntimeError("Required packages still missing: " + ", ".join(core))
    else:
        print("Required packages ready.")

    if not args.non_interactive and ask("Install local English hold-to-talk for Luma (Moonshine Small CPU runtime)?", False):
        if not shutil.which("uv"):
            run("sudo", "pacman", "-Syu", "--needed", "uv")
        run("python3", str(ROOT / "scripts/luma-voice.py"), "--install")

    if extras and not args.non_interactive and ask("Install optional apps, Spotify tools, and extra fonts?", True):
        helper = aur_helper()
        if not helper:
            print("An AUR helper is needed for optional extras. Install paru/yay, then rerun for those apps.")
        else:
            run(helper, "-S", "--needed", *extras)

    plugins = missing_plugins()
    if plugins:
        print("Optional Hyprland plugins:", ", ".join(plugins))
        print("Install plugins after logging into Hyprland; see README.md. The desktop works without them.")

    if importlib.util.find_spec("dbus") is None or importlib.util.find_spec("gi") is None:
        raise RuntimeError("Python D-Bus/GObject modules unavailable; no dotfiles were changed.")
    services = missing_services()
    if services:
        print("Disabled system services:", ", ".join(services))
        if args.non_interactive or not ask("Enable these services before dotfiles?", True):
            raise RuntimeError("Required services are disabled; no dotfiles were changed.")
        run("sudo", "systemctl", "enable", "--now", *services)
        if missing_services():
            raise RuntimeError("Required services could not be enabled; no dotfiles were changed.")
    if args.non_interactive:
        groups = ["desktop", "shell", "apps", "spotify", "wallpapers", "fonts"]
    else:
        groups = []
        for name, label, default in (
            ("desktop", "Install saved Hyprland keybinds, window rules and layout?", True),
            ("shell", "Install Modesty settings, themes, reminders and terminal artwork?", True),
            ("apps", "Install foot, fish, GTK/Qt, Flameshot and prompt settings?", True),
            ("wallpapers", "Install saved wallpapers?", True),
            ("spotify", "Install Spotify theme files (can skip until Spotify is installed)?", True),
            ("fonts", "Install bundled Inter fonts for other apps?", True),
        ):
            if ask(label, default):
                groups.append(name)
        if not groups or not ask("Apply these files with backups for existing files?", True):
            print("No dotfiles changed.")
            return
    install_files(groups, False)
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
    except (RuntimeError, subprocess.CalledProcessError, OSError) as exc:
        print("Install stopped:", exc, file=sys.stderr)
        sys.exit(1)
