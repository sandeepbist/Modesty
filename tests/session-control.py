#!/usr/bin/env python3
"""Verify handoff/rollback against temporary copies, without touching the session."""
import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('handoff', ROOT/'scripts/session-control.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
originals = {}
for path, replacements in mod.changes().items():
    fixture = ROOT / "setup/config/hypr" / path.relative_to(mod.CONFIG)
    content = fixture.read_text().replace("@MODESTY_ROOT@", str(ROOT)).replace(mod.SETTINGS_BIND, "")
    for old, new in replacements: content = content.replace(new, old)
    originals[str(path.relative_to(mod.CONFIG))] = content

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    cfg, state = tmp/'hypr', tmp/'state'
    for name, text in originals.items():
        path = cfg/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
    with patch.object(mod,'CONFIG',cfg), patch.object(mod,'STATE',state), patch.object(mod,'MARKER',state/'main-shell'), patch.object(mod,'BACKUP',state/'backup.json'), patch.object(mod,'assert_unlocked'), patch.object(mod,'run'), patch.object(mod,'stop_modesty'), patch.object(mod,'stop_agent'), patch.object(mod,'start'), patch.object(mod,'auth'), patch.object(mod,'validate_shell'):
        mod.enable()
        assert mod.MARKER.exists() and mod.BACKUP.exists()
        assert 'session-control.py' in (cfg/'hyprland/execs.lua').read_text()
        # Preserve a user's edit made after installation when restoring.
        keys = cfg/'hyprland/keybinds.lua'
        keys.write_text(keys.read_text()+'\n-- unrelated user edit\n')
        mod.restore()
        assert not mod.MARKER.exists()
        assert (cfg/'hyprland/execs.lua').read_text() == originals['hyprland/execs.lua']
        assert keys.read_text() == originals['hyprland/keybinds.lua']+'\n-- unrelated user edit\n'
        print('PASS handoff replaces only shell commands; restore retains later user edits')
        with patch.object(mod,'start',side_effect=[RuntimeError('startup failed'),None]):
            try: mod.enable()
            except RuntimeError: pass
            else: raise AssertionError('Expected startup failure')
        assert not mod.MARKER.exists()
        assert (cfg/'hyprland/execs.lua').read_text() == originals['hyprland/execs.lua']
        print('PASS startup failure rolls back startup commands and selection marker')
        before=keys.read_text(); keys.write_text(before.replace('caelestia shell -d','custom shell'))
        try: mod.enable()
        except RuntimeError: pass
        else: raise AssertionError('Expected changed-config preflight rejection')
        assert not mod.MARKER.exists()
        assert (cfg/'hyprland/execs.lua').read_text() == originals['hyprland/execs.lua']
        print('PASS changed config is detected before any file is written')

# A syntax failure must never remove the working shell, even on exit code zero.
from subprocess import CompletedProcess
with patch.object(mod.subprocess, 'run', return_value=CompletedProcess([], 0, 'ERROR: Failed to load configuration', '')):
    try: mod.validate_shell()
    except RuntimeError: pass
    else: raise AssertionError('Zero-exit QML load failure was accepted')
with patch.object(mod.subprocess, 'run', return_value=CompletedProcess([], 0, 'DEBUG qml: VALIDATION COMPLETE', '')):
    mod.validate_shell()
with tempfile.TemporaryDirectory() as tmp:
    marker = Path(tmp)/'main'; marker.touch()
    with patch.object(mod,'MARKER',marker), patch.object(mod,'assert_unlocked'), patch.object(mod,'validate_shell',side_effect=RuntimeError('bad QML')), patch.object(mod,'stop_modesty') as stop, patch.object(mod,'start') as start:
        try: mod.restart()
        except RuntimeError: pass
        else: raise AssertionError('Invalid shell restarted')
        stop.assert_not_called(); start.assert_not_called()
print('PASS failed QML validation preserves the live shell, including zero-exit errors')
