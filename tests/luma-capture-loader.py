#!/usr/bin/env python3
"""Verify opt-in persistence without contacting Hyprland or compiling a plugin."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('luma_loader', HERE.parent/'scripts/luma-capture.py')
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)
real_run = subprocess.run
checks = 0


def check(condition):
    global checks
    assert condition
    checks += 1


def fails(action, text):
    try:
        action()
    except RuntimeError as error:
        check(text in str(error))
    else:
        raise AssertionError('Expected failure: '+text)


with tempfile.TemporaryDirectory(prefix='luma-loader-check-') as temporary:
    root = Path(temporary)
    env = {key: str(root/name) for key, name in
           (('XDG_CONFIG_HOME', 'config $() "quote" é\n'),
            ('XDG_STATE_HOME', 'state'), ('XDG_CACHE_HOME', 'cache'))}
    with patch.dict(os.environ, env), patch.object(loader, 'SOURCE', root/'plugin.cpp'):
        loader.SOURCE.write_text('// Fake compiler input\n')
        marker, script, execs = loader.paths()
        execs.parent.mkdir(parents=True)
        original = ('-- user config\r\n'+loader.ANCHOR+'\r\n'
                    'local unrelated = "keep exactly"\r\n-- no final newline').encode()
        execs.write_bytes(original)
        execs.chmod(0o640)
        calls = []
        active = set()
        version = loader.SUPPORTED_BUILD
        load_error = None
        reload_error = None

        def output(command, **kwargs):
            calls.append(command)
            if command == ['hyprctl', 'version', '-j']:
                return json.dumps({'commit': version})
            if command == ['pkg-config', '--cflags', '--libs', 'hyprland']:
                return '-I/mock/include'
            if command == [os.environ.get('CXX', 'c++'), '--version']:
                return 'mock compiler 1.0'
            if command == ['hyprctl', 'plugin', 'list', '-j']:
                return json.dumps([{'name': 'luma-capture'}] if active else [])
            if command[:3] == ['hyprctl', 'plugin', 'load']:
                # All persistent writes must follow a confirmed successful load.
                if not marker.exists():
                    check(not marker.exists() and not script.exists())
                    check(execs.read_bytes() == original)
                if load_error:
                    return load_error
                if command[3] in active:
                    return 'Cannot load a plugin twice!'
                active.add(command[3])
                return 'ok\n'
            if command == ['hyprctl', 'reload']:
                return reload_error or 'ok'
            if command[:3] == ['hyprctl', 'plugin', 'unload']:
                if command[3] not in active:
                    return 'plugin not loaded'
                active.remove(command[3])
                return 'ok'
            raise AssertionError('Unexpected subprocess: '+repr(command))

        def compile_plugin(command, **kwargs):
            calls.append(command)
            check(command[1:3] == ['-std=c++23', '-O2'])
            Path(command[-1]).write_bytes(b'mock .so')
            return subprocess.CompletedProcess(command, 0)

        with patch.object(subprocess, 'check_output', side_effect=output), \
                patch.object(subprocess, 'run', side_effect=compile_plugin):
            # Missing/ambiguous anchors fail before any subprocess or config write.
            for invalid in (b'-- no anchor\n', (loader.ANCHOR+'\n').encode()*2):
                execs.write_bytes(invalid)
                before = list(calls)
                fails(loader.enable, 'exactly one')
                check(calls == before and execs.read_bytes() == invalid)
                check(not marker.exists() and not script.exists())
            execs.write_bytes(original)

            before = list(calls)
            check(loader.restore() is None and calls == before)
            version = 'unsupported'
            fails(loader.enable, 'supports only')
            check(not marker.exists() and not script.exists() and execs.read_bytes() == original)
            version = loader.SUPPORTED_BUILD
            for load_error in ('Stop screen capture before loading', 'ok\nlogical error',
                               'Cannot load a plugin twice!'):
                fails(loader.enable, 'load failed')
                check(not marker.exists() and not script.exists() and execs.read_bytes() == original)
            load_error = None

            write = loader.atomic_write
            for failed_path in (marker, script, execs):
                def write_failure(path, contents):
                    if path == failed_path:
                        raise OSError('mock disk failure')
                    write(path, contents)
                with patch.object(loader, 'atomic_write', side_effect=write_failure):
                    try:
                        loader.enable()
                    except (OSError, RuntimeError) as error:
                        check('mock disk failure' in str(error))
                    else:
                        raise AssertionError('Expected persistence failure')
                if failed_path == marker:
                    check(not marker.exists() and not active)
                else:
                    check(marker.exists() and active)
                    loader.disable()
                    check(not marker.exists() and not active)
                if script.exists():
                    script.unlink()
                execs.write_bytes(original)

            plugin = loader.enable()
            check(json.loads(marker.read_text())['plugin'] == str(plugin))
            check(execs.stat().st_mode & 0o777 == 0o640)
            registered = execs.read_bytes()
            insertion = ('dofile('+loader.lua_string(script)+') -- Modesty Luma capture bootstrap').encode()
            check(registered == original.replace(loader.ANCHOR.encode(), loader.ANCHOR.encode()+b'\r\n'+insertion))
            snapshot = [path.read_bytes() for path in (marker, script, execs)]
            check(loader.enable() == plugin)
            check(snapshot == [path.read_bytes() for path in (marker, script, execs)])
            for contents in (loader.ANCHOR.encode(), loader.ANCHOR.encode()+b'\n'):
                check(loader.register(loader.register(contents, script), script) == loader.register(contents, script))

            # Restore failures leave the enabled marker and safe fallback intact.
            version = 'unsupported'
            before = len(calls)
            fails(loader.restore, 'supports only')
            check(calls[before:] == [['hyprctl', 'version', '-j']])
            check(snapshot == [path.read_bytes() for path in (marker, script, execs)])
            version = loader.SUPPORTED_BUILD
            active.clear()
            load_error = 'ABI mismatch'
            fails(loader.restore, 'load failed')
            check(snapshot == [path.read_bytes() for path in (marker, script, execs)])
            load_error = None
            check(loader.restore() == plugin)

            stdout = io.StringIO()
            with patch.object(sys, 'argv', ['luma-capture.py', 'status']), contextlib.redirect_stdout(stdout):
                loader.main()
            state = json.loads(stdout.getvalue())
            check(state['enabled'] and state['loaded'] and state['supported'])
            check(state['supportedBuild'] == loader.SUPPORTED_BUILD)
            for command in ('build', 'test'):
                with patch.object(sys, 'argv', ['luma-capture.py', command]), \
                        contextlib.redirect_stdout(io.StringIO()), \
                        patch.object(subprocess, 'run') as run:
                    loader.main()
                    if command == 'test':
                        run.assert_called_once_with(['python3', str(loader.ROOT/'tests/luma-capture-live.py'),
                                                     '--plugin', str(plugin)], check=True)
                    else:
                        run.assert_not_called()
                    check(True)

            # Check actual Lua syntax and enabled/disabled semantics with a stub hl.
            def check_lua(enabled):
                luac, lua = shutil.which('luac'), shutil.which('lua')
                if luac:
                    for path in (script, execs):
                        real_run([luac, '-p', str(path)], check=True, capture_output=True)
                        check(True)
                if lua:
                    source = '''local rules, callback = {}, nil
hl = {
 layer_rule = function(rule) table.insert(rules, rule) end,
 on = function(event, action) assert(event == "hyprland.start"); callback = action end,
 exec_cmd = function(command) io.write(command) end
}
dofile('''+loader.lua_string(script)+''')
assert(#rules == '''+('2' if enabled else '0')+''')
'''
                    if enabled:
                        source += '''assert(rules[1].match.namespace == "^modesty-command-canvas$")
assert(rules[2].match.namespace == "^modesty-island$")
assert(rules[1].no_screen_share and rules[2].no_screen_share)
assert(callback); callback()
'''
                    else:
                        source += 'assert(callback == nil)\n'
                    result = real_run([lua, '-'], input=source, text=True, check=True, capture_output=True)
                    expected = [sys.executable, str(Path(loader.__file__).resolve()), 'restore'] if enabled else []
                    check(shlex.split(result.stdout) == expected)
                return bool(luac), bool(lua)

            # Also round-trip a helper path containing shell and Lua metacharacters.
            with patch.object(loader, '__file__', str(root/'helper $() "quote" é\n.py')):
                script.write_bytes(loader.bootstrap(marker))
                lua_checks = check_lua(True)
            script.write_bytes(loader.bootstrap(marker))
            # Never stack internal renderer hooks from two compiled builds.
            loader.SOURCE.write_text('// changed fake compiler input\n')
            snapshot = [path.read_bytes() for path in (marker, script, execs)]
            before = len([call for call in calls if call[:3] == ['hyprctl', 'plugin', 'load']])
            fails(loader.enable, 'different Luma capture build')
            check(before == len([call for call in calls if call[:3] == ['hyprctl', 'plugin', 'load']]))
            check(snapshot == [path.read_bytes() for path in (marker, script, execs)])
            # A fresh session rebuilds changed source and records the new loaded path.
            active.clear()
            loader.SOURCE.write_text('// changed fake compiler input\n')
            previous_marker = marker.read_bytes()
            with patch.object(loader, 'atomic_write', side_effect=OSError('mock restore disk failure')):
                try:
                    loader.restore()
                except OSError as error:
                    check('mock restore disk failure' in str(error))
                else:
                    raise AssertionError('Expected restore persistence failure')
            check(marker.read_bytes() == previous_marker and not active)
            replacement = loader.restore()
            check(replacement != plugin)
            check(json.loads(marker.read_text())['plugin'] == str(replacement))
            plugin = replacement
            execs.write_bytes(registered+b'\r\n-- unrelated edit after enable\r\n')
            edited = execs.read_bytes()
            loader.disable()
            check(not marker.exists() and not active and execs.read_bytes() == edited)
            check(calls[-1] == ['hyprctl', 'plugin', 'unload', str(plugin)])
            check_lua(False)
            before = list(calls)
            check(loader.restore() is None)
            loader.disable()
            check(calls == before)
            marker.write_text(json.dumps({'plugin': str(plugin)}))
            active.add(str(plugin))
            reload_error = 'reload rejected'
            fails(loader.disable, 'reload rejected')
            check(not marker.exists() and not active and execs.read_bytes() == edited)

print(f'PASS {checks} checks; mocked build/load/reload/unload; Lua parse={lua_checks[0]}, runtime={lua_checks[1]}')
