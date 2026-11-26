#!/usr/bin/env python3
"""Verify handoff/rollback against temporary copies, without touching the session."""
import importlib.util
import json
from pathlib import Path
import shlex
import tempfile
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
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
from subprocess import CompletedProcess, TimeoutExpired
with patch.object(mod.subprocess, 'run', return_value=CompletedProcess([], 0, 'ERROR: Failed to load configuration', '')):
    try: mod.validate_shell()
    except RuntimeError: pass
    else: raise AssertionError('Zero-exit QML load failure was accepted')
with patch.object(mod.subprocess, 'run', return_value=CompletedProcess([], 0, 'DEBUG qml: VALIDATION COMPLETE', '')):
    mod.validate_shell()
with patch.dict(mod.os.environ, {'WAYLAND_DISPLAY':''}):
    absent_audio='ERROR quickshell.service.pipewire.loop: Failed to connect pipewire context. Errno: 112\nDEBUG qml: VALIDATION COMPLETE'
    with patch.object(mod.subprocess,'run',return_value=CompletedProcess([],0,absent_audio,'')):
        mod.validate_shell(headless=True)
        try:mod.validate_shell()
        except RuntimeError:pass
        else:raise AssertionError('Live validation ignored missing audio')
    for failure in ('ERROR: Failed to load configuration', 'WARN: Quickshell was built against Qt 6.11.2 but the system has updated to Qt 6.12.0 without rebuilding the package.'):
        with patch.object(mod.subprocess,'run',return_value=CompletedProcess([],0,failure+'\nDEBUG qml: VALIDATION COMPLETE','')):
            try:mod.validate_shell(headless=True)
            except RuntimeError:pass
            else:raise AssertionError('Headless validation accepted broken QML or a Qt mismatch')
with tempfile.TemporaryDirectory() as tmp:
    marker = Path(tmp)/'main'; marker.touch()
    with patch.object(mod,'MARKER',marker), patch.object(mod,'assert_unlocked'), patch.object(mod,'validate_shell',side_effect=RuntimeError('bad QML')), patch.object(mod,'stop_modesty') as stop, patch.object(mod,'start') as start:
        try: mod.restart()
        except RuntimeError: pass
        else: raise AssertionError('Invalid shell restarted')
        stop.assert_not_called(); start.assert_not_called()
print('PASS failed QML validation preserves the live shell, including zero-exit errors')

with patch.object(mod,'health',return_value={'locked':False}):
    for code in (0,1):
        with patch.object(mod,'run',return_value=CompletedProcess([],code,'Target not found.\n','')) as run:
            mod.flush_notes()
            assert run.call_count == 1
    acknowledgement='{"ok":true,"status":"pending"}'
    saved='{"loaded":true,"dirty":false,"saving":false,"saveState":"Saved","error":""}'
    with patch.object(mod,'run',side_effect=[CompletedProcess([],0,acknowledgement,''),CompletedProcess([],0,saved,'')]):
        mod.flush_notes()
    for response in ('Function not found.', 'Storage target not found.', 'No handler was able to save.', '{"ok":false,"status":"failed"}', '{"ok":false,"status":"failed","error":"Target not found."}', '[]'):
        with patch.object(mod,'run',return_value=CompletedProcess([],0,response,'')):
            try:mod.flush_notes()
            except RuntimeError:pass
            else:raise AssertionError('Invalid Notes acknowledgement allowed a restart '+response)
    for response in ('Target not found.', '[]', '{"loaded":true,"dirty":false,"saving":false,"saveState":"Failed"}', '{"loaded":true,"dirty":false,"saving":false,"saveState":"Saved","error":"disk failure"}'):
        with patch.object(mod,'run',side_effect=[CompletedProcess([],0,acknowledgement,''),CompletedProcess([],0,response,'')]):
            try:mod.flush_notes()
            except RuntimeError:pass
            else:raise AssertionError('Invalid Notes save status allowed a restart '+response)
print('PASS Notes restart flush accepts exact absent-target response and refuses missing functions, invalid statuses and failed saves')

listing=['quickshell','list','-p',str(ROOT/'shell.qml')]
flushing=['quickshell','ipc','-p',str(ROOT/'shell.qml'),'call','notes','flush','session']
status=['quickshell','ipc','-p',str(ROOT/'shell.qml'),'call','notes','status']
killing=['quickshell','kill','-p',str(ROOT/'shell.qml')]
live=CompletedProcess([],0,'Instance test:\n  Process ID: 987654321\n','')
with tempfile.TemporaryDirectory() as tmp, patch.object(mod,'STATE',Path(tmp)), patch.object(mod,'health',return_value=None):
    for response in (CompletedProcess([],1,'','IPC unavailable'),CompletedProcess([],0,'',''),CompletedProcess([],0,'Function not found.',''),CompletedProcess([],0,'[]','')):
        def respond(args,check=True):
            if args==listing:return live
            if args==flushing:return response
            if args==killing:return CompletedProcess([],0,'','')
            raise AssertionError('Unexpected shell command '+str(args))
        with patch.object(mod,'run',side_effect=respond) as run:
            try:mod.stop_modesty()
            except RuntimeError:pass
            else:raise AssertionError('Missing health and Notes acknowledgement killed the live shell')
            assert [call.args[0] for call in run.call_args_list]==[listing,flushing]
    for response in (CompletedProcess([],1,saved,''),CompletedProcess([],0,'',''),CompletedProcess([],0,'Target not found.',''),CompletedProcess([],0,'[]',''),CompletedProcess([],0,'{"loaded":true,"dirty":false,"saving":false,"saveState":"Failed"}',''),CompletedProcess([],0,'{"loaded":true,"dirty":false,"saving":false,"saveState":"Saved","error":"disk failure"}','')):
        with patch.object(mod,'run',side_effect=[live,CompletedProcess([],0,acknowledgement,''),response]) as run:
            try:mod.stop_modesty()
            except RuntimeError:pass
            else:raise AssertionError('Invalid Notes save status killed the live shell')
            assert [call.args[0] for call in run.call_args_list]==[listing,flushing,status]
    for replies,commands in (([live,TimeoutExpired(flushing,12)],[listing,flushing]),([live,CompletedProcess([],0,acknowledgement,''),TimeoutExpired(status,12)],[listing,flushing,status])):
        with patch.object(mod,'run',side_effect=replies) as run:
            try:mod.stop_modesty()
            except TimeoutExpired as error:assert error.timeout==12
            else:raise AssertionError('Notes IPC timeout killed the live shell')
            assert [call.args[0] for call in run.call_args_list]==commands
    absent=CompletedProcess([],0,'',f'No running instances for "{ROOT}/shell.qml"\nUse --all to list all instances.\n')
    with patch.object(mod,'run',return_value=absent) as run:
        mod.stop_modesty()
        assert [call.args[0] for call in run.call_args_list]==[listing]
    for response in (CompletedProcess([],1,'','List unavailable'),CompletedProcess([],0,'',''),CompletedProcess([],0,'Unknown response','')):
        with patch.object(mod,'run',return_value=response) as run:
            try:mod.stop_modesty()
            except RuntimeError:pass
            else:raise AssertionError('Unknown shell instance state allowed a stop')
            assert [call.args[0] for call in run.call_args_list]==[listing]
    with patch.object(mod,'run',side_effect=[live,CompletedProcess([],0,acknowledgement,''),CompletedProcess([],0,saved,''),CompletedProcess([],0,'','')]) as run:
        mod.stop_modesty()
        assert [call.args[0] for call in run.call_args_list]==[listing,flushing,status,killing]
    for code in (0,1):
        with patch.object(mod,'run',side_effect=[live,CompletedProcess([],code,'Target not found.\n',''),CompletedProcess([],0,'','')]) as run:
            mod.stop_modesty()
            assert [call.args[0] for call in run.call_args_list]==[listing,flushing,killing]
print('PASS missing health never skips Notes save; absent instances are a no-op; failed flush, status and instance listing preserve the live shell')

import shell_renderer
ready = {'locked':False, 'compatibility':True, 'preview':False, 'policyAgent':True}
with tempfile.TemporaryDirectory() as tmp, patch.object(mod,'MARKER',Path(tmp)/'main-shell'), patch.object(mod,'run',return_value=CompletedProcess([],0,'ok\n','')) as run, patch.object(mod,'health',return_value=ready) as health, patch.object(shell_renderer,'run_shell') as render, patch.object(mod.time,'sleep'):
    mod.MARKER.touch()
    script = Path(tmp)/'Modesty \' " ; $(touch owned) `touch owned` & |\n'/'scripts/session-control.py'
    with patch.object(mod,'__file__',str(script)):
        mod.start()
    assert run.call_count == 1, 'Shell startup bypassed compositor dispatch'
    command = run.call_args.args[0]
    assert command[:2] == ['hyprctl','eval']
    prefix, suffix = 'hl.dispatch(hl.dsp.exec_cmd(', '))'
    assert command[2].startswith(prefix) and command[2].endswith(suffix)
    assert shlex.split(json.loads(command[2][len(prefix):-len(suffix)])) == ['python3',str(script.resolve()),'spawn-native']
    render.assert_not_called()
    print('PASS startup dispatches the native worker with metacharacter paths quoted as one argument')

    for response in (CompletedProcess([],1,'','socket unavailable'), CompletedProcess([],0,'Error evaluating Lua',''), CompletedProcess([],0,'',''), CompletedProcess([],0,'ok\n','dispatch error')):
        with patch.object(mod,'run',return_value=response), patch.object(mod,'health') as probe:
            try: mod.start()
            except RuntimeError as error:
                assert (response.stdout+response.stderr).strip() in str(error)
            else: raise AssertionError('Failed compositor dispatch was accepted')
            probe.assert_not_called()
    with patch.object(mod,'run',side_effect=TimeoutExpired(['hyprctl','eval'],12)):
        try: mod.start()
        except TimeoutExpired: pass
        else: raise AssertionError('Compositor timeout was hidden')
    print('PASS failed, empty, error and timed-out dispatch replies fail before readiness polling')

    with patch.object(mod.time,'monotonic',side_effect=[0,0,39,99.9]), patch.object(mod,'health',side_effect=[None,dict(ready,policyAgent=False),ready]):
        mod.start()
    for state in (None,dict(ready,compatibility=False),dict(ready,preview=True),dict(ready,policyAgent=False)):
        with patch.object(mod.time,'monotonic',side_effect=[0,0,100]), patch.object(mod,'health',return_value=state):
            try: mod.start()
            except RuntimeError as error: assert 'permission agent' in str(error)
            else: raise AssertionError('Unready shell passed startup health checks')
    with patch.object(mod,'assert_unlocked'), patch.object(mod,'validate_shell') as validate, patch.object(mod,'stop_modesty') as stop:
        run.reset_mock()
        mod.restart()
        validate.assert_called_once(); stop.assert_called_once()
        assert run.call_args.args[0][:2] == ['hyprctl','eval']
    render.assert_not_called()
    print('PASS startup waits through native setup and health budgets and requires compatibility, preview off and permission agent')

    run.reset_mock(); health.reset_mock()
    mod.MARKER.unlink()
    mod.start()
    run.assert_called_once_with(['caelestia','shell','-d'])
    run.reset_mock()
    try: mod.spawn_native()
    except RuntimeError: pass
    else: raise AssertionError('Native worker launched without main-shell selection')
    run.assert_not_called(); health.assert_not_called(); render.assert_not_called()
    mod.MARKER.touch()
    with patch.object(mod,'health',return_value={'locked':True}):
        try: mod.spawn_native()
        except RuntimeError: pass
        else: raise AssertionError('Native worker launched while locked')
    run.assert_not_called(); render.assert_not_called()
    print('PASS Caelestia fallback remains; native worker refuses missing marker and locked session')

    environment = {'PATH':'/usr/bin', 'WAYLAND_DISPLAY':'wayland-test', 'ELECTRON_RUN_AS_NODE':'1', 'LD_LIBRARY_PATH':'/opt/t3code/lib:/usr/lib', 'MODESTY_COMPAT':'0', 'MODESTY_PREVIEW':'1'}
    with patch.object(mod,'assert_unlocked') as unlocked, patch.dict(mod.os.environ,environment,clear=True):
        mod.spawn_native()
        unlocked.assert_called_once()
        expected = {'PATH':'/usr/bin', 'WAYLAND_DISPLAY':'wayland-test', 'LD_LIBRARY_PATH':'/usr/lib', 'MODESTY_COMPAT':'1', 'MODESTY_PREVIEW':'0'}
        render.assert_called_once_with(['quickshell','-d','--no-duplicate','-p',str(ROOT/'shell.qml')],expected)
        assert dict(mod.os.environ) == environment
        for failure in (RuntimeError('renderer failed'),TimeoutExpired(['quickshell'],12)):
            with patch.object(shell_renderer,'run_shell',side_effect=failure):
                try: mod.spawn_native()
                except (RuntimeError,TimeoutExpired) as error: assert error is failure
                else: raise AssertionError('Native worker hid renderer failure')
    run.assert_not_called()
    print('PASS native worker preserves renderer startup, cleans environment, forces main-shell modes and propagates failures without recursion')
