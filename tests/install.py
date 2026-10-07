#!/usr/bin/env python3
"""Exercise the real installer against temporary homes, never the live desktop."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

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

with patch.object(installer, "plugin_status", side_effect=lambda: status.copy()), patch.object(installer, "run", side_effect=plugin_command), patch.object(installer.compatibility, 'require'), patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE':'test'}), patch('builtins.input', return_value='y'):
    installer.install_plugins(["dynamic-cursors"])
    assert commands == [("hyprpm", "update"), ("hyprpm", "add", installer.PLUGINS["dynamic-cursors"]), ("hyprpm", "enable", "dynamic-cursors"), ("hyprpm", "reload"), ("hyprctl", "reload")]
    commands.clear()
    installer.install_plugins(["dynamic-cursors"])
    assert commands == [("hyprpm", "update"), ("hyprpm", "reload"), ("hyprctl", "reload")]
with tempfile.TemporaryDirectory() as directory, patch.object(installer, "PLUGIN_QUEUE", Path(directory) / "modesty/plugins-pending.json"):
    installer.save_plugin_queue(["scrolloverview"])
    assert json.loads(installer.PLUGIN_QUEUE.read_text()) == ["scrolloverview"]
print("PASS interactive wallpaper/plugin choices, preserved wallpaper, failed-build parsing, plugin install/reuse and first-login queue")

with patch.object(installer.shutil, "which", return_value=None), patch.object(installer, "run") as run, patch('builtins.input',return_value='y'):
    installer.install_voice()
    assert run.call_args_list[0].args == ("sudo", "pacman", "-Syu", "--needed", "uv")
    assert run.call_args_list[1].args == ("python3", str(ROOT / "scripts/luma-voice.py"), "--install")
with patch.object(installer.shutil, "which", return_value="/usr/bin/uv"), patch.object(installer, "run") as run, patch('builtins.input',return_value='y'):
    installer.install_voice()
    run.assert_called_once_with("python3", str(ROOT / "scripts/luma-voice.py"), "--install")
print("PASS shared voice setup installs missing dependency and reuses existing uv without administrator commands")

# Qt repair keeps the installed package flavor and checksums the stable backport.
for package in ('quickshell', 'quickshell-git'):
    commands=[];recipes=[]
    def rebuild_command(*args,cwd=None,env=None):
        commands.append(args)
        if args[0]=='git':
            target=Path(args[-1]);target.mkdir()
            (target/'PKGBUILD').write_text('pkgver=0.3.1\npkgrel=1\n')
        else:
            assert env.get('CMAKE_BUILD_PARALLEL_LEVEL')
            recipes.append((cwd/'PKGBUILD').read_text())
            if package=='quickshell':
                # PKGBUILD is a Git checkout; its nested source tree must not
                # silently inherit that repository when applying the backport.
                subprocess.run(['git','init',str(cwd)],check=True,capture_output=True)
                srcdir=cwd/'src';probe=srcdir/'quickshell/src/probe';probe.parent.mkdir(parents=True)
                probe.write_text('old\n')
                (srcdir/'quickshell-qt6.12.patch').write_text('diff --git a/src/probe b/src/probe\n--- a/src/probe\n+++ b/src/probe\n@@ -1 +1 @@\n-old\n+new\n')
                subprocess.run(['bash','-c',recipes[-1]+'\nprepare'],cwd=cwd,env=dict(os.environ,srcdir=str(srcdir)),check=True,capture_output=True)
                assert probe.read_text()=='new\n'
    with patch.object(installer,'run',side_effect=rebuild_command),contextlib.redirect_stdout(io.StringIO()):
        installer.rebuild_quickshell({package})
    assert commands[0][4].endswith('/'+package+'.git'),commands
    assert commands[1]==('makepkg','-si'),commands
    if package=='quickshell':
        assert '5d5d49873fe8cf1f99ddfd5006ceb2057c5c9b13.patch' in recipes[0]
        assert 'b8a7eab0f883070a26283140e06d252a0aa3483287c54bbb0c3aacb6e82eb0b2' in recipes[0]
    else:
        assert 'prepare()' not in recipes[0]
with patch.object(installer,'run') as command:
    try:installer.rebuild_quickshell({'custom-quickshell'})
    except RuntimeError:pass
    else:raise AssertionError('Unknown package variant rebuilt')
    command.assert_not_called()
with patch.object(installer.shutil,'disk_usage',return_value=SimpleNamespace(free=0)),patch.object(installer,'run') as command,contextlib.redirect_stdout(io.StringIO()):
    try:installer.rebuild_quickshell({'quickshell'})
    except RuntimeError as error:assert '3 GiB' in str(error)
    else:raise AssertionError('Qt rebuild accepted insufficient temporary space')
    command.assert_not_called()
print('PASS optional Qt repair preserves stable/git variants, pins the upstream backport and refuses custom packages')

with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
    home=Path(directory)
    control=SimpleNamespace(health=Mock(return_value={'locked':False}),assert_unlocked=Mock(),stop_modesty=Mock())
    busy=Mock(side_effect=RuntimeError('Finish recording before reloading.'))
    spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module:None))
    with (
        patch.object(installer,'HOME',home),
        patch.object(installer,'CONFIG',home/'.config'),
        patch.object(installer,'STATE',home/'.local/state'),
        patch.object(installer.os,'geteuid',return_value=1000),
        patch.object(sys,'argv',['install.py','--uninstall','--non-interactive']),
        patch.object(installer.installation,'uninstall') as uninstall,
        patch.object(installer.installation,'uninstall_plan',return_value=[]),
        patch.object(installer.importlib.util,'spec_from_file_location',return_value=spec),
        patch.object(installer.importlib.util,'module_from_spec',return_value=control),
        patch.dict(sys.modules,{'updates':SimpleNamespace(busy_work=busy)}),
    ):
        try:installer.main()
        except RuntimeError as error:assert 'Finish recording' in str(error)
        else:raise AssertionError('Uninstall interrupted active desktop work')
        control.stop_modesty.assert_not_called()
        uninstall.assert_called_once_with(ROOT,home,home/'.local/state',True)
print('PASS uninstall refuses active work before stopping the shell or changing files')

# Declining approval (including an empty answer) never runs package/model/plugin commands.
for answer in ('n', ''):
    with patch('builtins.input', return_value=answer), patch.object(installer,'run') as command, patch.object(installer.shutil,'which',return_value=None), contextlib.redirect_stdout(io.StringIO()):
        assert installer.install_voice() is False
        assert installer.aur_helper() is None
        command.assert_not_called()
    with patch('builtins.input', return_value=answer), patch.object(installer,'run') as command, patch.object(installer.compatibility,'require'), patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE':'test'}), contextlib.redirect_stdout(io.StringIO()):
        assert installer.install_plugins(['dynamic-cursors']) is False
        command.assert_not_called()
with patch.object(installer,'run') as command, patch.object(installer.compatibility,'require',side_effect=RuntimeError('Unsupported runtime')), patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE':'test'}), patch('builtins.input') as prompt:
    try:installer.install_plugins(['dynamic-cursors'])
    except RuntimeError:pass
    else:raise AssertionError('Plugin setup bypassed runtime validation')
    command.assert_not_called();prompt.assert_not_called()
print('PASS declined/default-no voice, AUR and plugin approvals run no commands; runtime failures stop before plugin changes')

for missing_package in (True, False):
    with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stdout(io.StringIO()):
        home=Path(directory)
        packages=set(installer.CORE+installer.EXTRAS)-({'foot'} if missing_package else set())
        with (
            patch.object(installer,'HOME',home),patch.object(installer,'CONFIG',home/'.config'),patch.object(installer,'STATE',home/'.local/state'),
            patch.object(installer.os,'geteuid',return_value=1000),patch.object(sys,'argv',['install.py']),
            patch.object(installer,'installed_packages',return_value=packages),
            patch.object(installer,'missing_services',return_value=[] if missing_package else ['NetworkManager']),
            patch.object(installer.shutil,'which',return_value='/usr/bin/tool'),
            patch('builtins.input',return_value=''),patch.object(installer,'run') as command,
        ):
            try:installer.main()
            except RuntimeError as error:assert 'Required packages' in str(error) or 'Required services' in str(error),error
            else:raise AssertionError('Required repair proceeded without approval')
            command.assert_not_called()
            assert not list(home.iterdir())
print('PASS default-no required package/service repairs run no commands and create no files')
