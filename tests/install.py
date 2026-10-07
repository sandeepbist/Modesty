#!/usr/bin/env python3
"""Exercise the real installer against temporary homes, never the live desktop."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import subprocess
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
GROUPS = ["desktop", "shell", "apps", "spotify", "wallpapers", "fonts"]
assert not installer.missing_core(set(installer.CORE)-{'hyprland','quickshell','hyprpm','firefox'}|{'hyprland-git','quickshell-git','hyprpm-git','zen-browser-bin'})

with tempfile.TemporaryDirectory(prefix="modesty-install-check-") as directory:
    home = Path(directory) / "home"
    home.mkdir()
    state = Path(directory) / "external-state"
    with patch.object(installer, "HOME", home), patch.object(installer, "CONFIG", home / ".config"), patch.object(installer, "STATE", state), contextlib.redirect_stdout(io.StringIO()):
        # Dry-run must not create directories or backups.
        expected = installer.install_files(GROUPS, True)
        assert expected > 0
        assert not list(home.iterdir()) and not state.exists()
        assert installer.install_files(GROUPS, False) == expected
        for group in GROUPS:
            for source in installer.files_for(group):
                if source.is_file():
                    target = installer.destination(source, group)
                    assert target.read_bytes() == installer.rendered(source), target
                    assert target.stat().st_mode & 0o777 == source.stat().st_mode & 0o777
        assert installer.install_files(GROUPS, False) == 0
        assert not (state / "modesty-install-backups").exists()
        # A saved wallpaper must exist in the installed wallpaper set.
        wallpaper = json.loads((state / "modesty/wallpaper.json").read_text())
        assert Path(wallpaper["path"]).is_file()
        wallpaper_data = json.loads((state / "modesty/wallpaper-data.json").read_text())
        assert wallpaper_data["image"] == wallpaper["path"]
        assert Path(wallpaper_data["image"]).is_file()
        assert (state / "modesty/main-shell").read_text().strip() == str(ROOT)
        # Regular files and symlinks are backed up; symlink destinations are untouched.
        fish = home / ".config/fish/config.fish"
        fish.write_text("my existing fish config\n")
        prompt = home / ".config/starship.toml"
        original = home / "original-prompt"
        original.write_text("my original prompt\n")
        prompt.unlink()
        prompt.symlink_to(original)
        palette = state / "modesty/wallpaper-palette.json"
        palette.write_text("my palette\n")
        assert installer.install_files(GROUPS, False) == 3
        backup, = (state / "modesty-install-backups").iterdir()
        assert (backup / ".config/fish/config.fish").read_text() == "my existing fish config\n"
        assert (backup / ".config/starship.toml").is_symlink()
        assert original.read_text() == "my original prompt\n"
        assert (backup / "state/modesty/wallpaper-palette.json").read_text() == "my palette\n"
        assert not prompt.is_symlink()
        # Reject directory conflicts before modifying any other template destination.
        fish.write_text("keep me\n")
        prompt.unlink()
        prompt.mkdir()
        try:
            installer.install_files(GROUPS, False)
        except RuntimeError as error:
            assert "Destination is a directory" in str(error)
        else:
            raise AssertionError("Directory conflict accepted")
        assert fish.read_text() == "keep me\n"
        # Atomic replacement failure must leave the previous file intact.
        prompt.rmdir()
        prompt.write_text("previous prompt\n")
        with patch.object(installer.os, "replace", side_effect=OSError("write failed")):
            try:
                installer.install_files(["apps"], False)
            except OSError:
                pass
            else:
                raise AssertionError("Expected write failure")
        assert fish.read_text() == "keep me\n"
        assert not list(fish.parent.glob(".modesty-*"))

# Future private state must not silently become part of an install.
with tempfile.TemporaryDirectory() as directory:
    setup = Path(directory)
    for name in ("preferences.json", "reminders.json", "gemini.key", "luma-memory.txt", "future-private-state.json"):
        path = setup / "state/modesty" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("private placeholder")
    with patch.object(installer, "SETUP", setup):
        copied = {path.name for path in installer.files_for("shell") if path.is_file()}
        assert copied == {"preferences.json"}, copied

# A fresh install has no migration backup; restoring must not change its configs.
spec = importlib.util.spec_from_file_location("handoff", ROOT / "scripts/session-control.py")
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)
with tempfile.TemporaryDirectory() as directory, patch.object(handoff, "BACKUP", Path(directory) / "absent.json"), patch.object(handoff, "assert_unlocked") as unlocked:
    try:
        handoff.restore()
    except RuntimeError as error:
        assert "No Caelestia handoff" in str(error)
    else:
        raise AssertionError("Fresh-install restore accepted")
    unlocked.assert_not_called()

print("PASS clean-home install, all rendered files, idempotence, backups, symlinks, atomic writes, conflicts and private-state isolation")

with tempfile.TemporaryDirectory() as directory:
    home = Path(directory)
    state = home / ".local/state"
    with patch.object(installer, "HOME", home), patch.object(installer, "CONFIG", home / ".config"), patch.object(installer, "STATE", state), contextlib.redirect_stdout(io.StringIO()):
        installer.install_files(["shell"], False)
        assert not (home / "Pictures/Wallpapers").exists()
        assert not any((state / "modesty" / name).exists() for name in ("wallpaper.json", "wallpaper-data.json", "wallpaper-palette.json"))
        saved = state / "modesty/wallpaper.json"
        saved.write_text('{"path":"my-wallpaper.png"}')
        installer.install_files(["shell"], False)
        assert saved.read_text() == '{"path":"my-wallpaper.png"}'

with patch("builtins.input", side_effect=["y", "y", "y", "n", "n", "y"]):
    assert installer.choose_groups() == ["desktop", "shell", "apps", "fonts"]
with patch("builtins.input", side_effect=["y", "n"]):
    assert installer.choose_plugins() == ["dynamic-cursors"]
with patch("builtins.input", side_effect=["n", "y"]):
    assert installer.choose_plugins() == ["scrolloverview"]

# Match actual hyprpm output, including a failed build before an enabled plugin.
output = "Repository cursors:\n  │ Plugin dynamic-cursors\n  └─ enabled: Plugin failed to build\nRepository overview:\n  │ Plugin scrolloverview\n  └─ enabled: \x1b[32mtrue\x1b[0m\n"
with patch.object(installer.shutil, "which", return_value="/usr/bin/hyprpm"), patch.object(installer.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, "")):
    assert installer.plugin_status() == {"dynamic-cursors": False, "scrolloverview": True}
    assert installer.missing_plugins() == ["dynamic-cursors"]

status = {}
commands = []
def plugin_command(*args):
    commands.append(args)
    if args[:2] == ("hyprpm", "add"):
        status[next(name for name, url in installer.PLUGINS.items() if url == args[2])] = False
    if args[:2] == ("hyprpm", "enable"):
        status[args[2]] = True

with patch.object(installer, "plugin_status", side_effect=lambda: status.copy()), patch.object(installer, "run", side_effect=plugin_command):
    installer.install_plugins(["dynamic-cursors"])
    assert commands == [("hyprpm", "update"), ("hyprpm", "add", installer.PLUGINS["dynamic-cursors"]), ("hyprpm", "enable", "dynamic-cursors"), ("hyprpm", "reload"), ("hyprctl", "reload")]
    commands.clear()
    installer.install_plugins(["dynamic-cursors"])
    assert commands == [("hyprpm", "update"), ("hyprpm", "reload"), ("hyprctl", "reload")]
with tempfile.TemporaryDirectory() as directory, patch.object(installer, "PLUGIN_QUEUE", Path(directory) / "modesty/plugins-pending.json"):
    installer.save_plugin_queue(["scrolloverview"])
    assert json.loads(installer.PLUGIN_QUEUE.read_text()) == ["scrolloverview"]
print("PASS interactive wallpaper/plugin choices, preserved wallpaper, failed-build parsing, plugin install/reuse and first-login queue")

with patch.object(installer.shutil, "which", return_value=None), patch.object(installer, "run") as run:
    installer.install_voice()
    assert run.call_args_list[0].args == ("sudo", "pacman", "-Syu", "--needed", "uv")
    assert run.call_args_list[1].args == ("python3", str(ROOT / "scripts/luma-voice.py"), "--install")
with patch.object(installer.shutil, "which", return_value="/usr/bin/uv"), patch.object(installer, "run") as run:
    installer.install_voice()
    run.assert_called_once_with("python3", str(ROOT / "scripts/luma-voice.py"), "--install")
print("PASS shared voice setup installs missing dependency and reuses existing uv without administrator commands")
