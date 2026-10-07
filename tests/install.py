#!/usr/bin/env python3
"""Exercise the real installer against temporary homes, never the live desktop."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
GROUPS = ["desktop", "shell", "apps", "spotify", "wallpapers", "fonts"]

with tempfile.TemporaryDirectory(prefix="modesty-install-check-") as directory:
    home = Path(directory) / "home"
    home.mkdir()
    state = Path(directory) / "external-state"
    with patch.object(installer, "HOME", home), patch.object(installer, "CONFIG", home / ".config"), patch.object(installer, "STATE", state), contextlib.redirect_stdout(io.StringIO()):
        # Dry-run must not create directories or backups.
        expected = installer.install_files(GROUPS, True)
        assert expected > 100
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
