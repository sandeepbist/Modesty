#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import shell_renderer as renderer

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    environment = {'XDG_STATE_HOME': str(root), 'WAYLAND_DISPLAY': 'test-display', 'PATH': '/usr/bin'}
    command = ['quickshell', '-d', '-p', 'shell.qml']
    success = subprocess.CompletedProcess(command, 0)
    with patch.object(renderer.subprocess, 'run', return_value=success) as run:
        renderer.run_shell(command, environment)
        assert run.call_count == 1 and run.call_args.kwargs['env'] == environment
        assert 'pass_fds' not in run.call_args.kwargs
    path = renderer.selection_file(environment)
    path.parent.mkdir(parents=True)
    path.write_text('{broken')
    with patch.object(renderer.subprocess, 'run', return_value=success) as run:
        renderer.run_shell(command, environment)
        assert run.call_count == 1 and run.call_args.kwargs['env'] == environment
    print('PASS default and invalid local selection preserve the ordinary shell command/environment')

    fingerprint = {'egl_vendor': 'Mesa Project', 'gpu_vendor': '0x1002'}
    path.write_text(json.dumps(fingerprint))
    for value in (None, dict(fingerprint, gpu_vendor='0x10de')):
        with patch.object(renderer, 'compatible_device', return_value=value), patch.object(renderer.subprocess, 'run', return_value=success) as run:
            renderer.run_shell(command, environment)
            assert run.call_count == 1 and run.call_args.kwargs['env'] == environment
    with patch.object(renderer, 'compatible_device', return_value=fingerprint), patch.object(renderer, 'bootstrap_library', return_value=None), patch.object(renderer.subprocess, 'run', return_value=success) as run:
        renderer.run_shell(command, environment)
        assert run.call_count == 1 and run.call_args.kwargs['env'] == environment
    print('PASS changed GPU, unsupported host and unavailable compiler keep ordinary startup')

    for key in renderer.GPU_OVERRIDES:
        for value in ('', 'caller-value'):
            with patch.object(renderer.subprocess, 'run') as run:
                assert renderer.compatible_device(dict(environment, **{key: value})) is None
                run.assert_not_called()
    with patch.object(renderer.subprocess, 'run') as run:
        assert renderer.compatible_device({}) is None
        run.assert_not_called()
    for key in renderer.WAYLAND_PLATFORMS:
        for value in ('', 'xcb', 'caller-value'):
            with patch.object(renderer.subprocess, 'run') as run:
                assert renderer.compatible_device(dict(environment, **{key: value})) is None
                run.assert_not_called()
    for value in ('', '.', '/custom/lib', '/usr/lib:'):
        with patch.object(renderer.subprocess, 'run') as run:
            assert renderer.compatible_device(dict(environment, LD_LIBRARY_PATH=value)) is None
            run.assert_not_called()
    isolated = root/'root'
    isolated.mkdir()
    for key in ('__NV_PRIME_RENDER_OFFLOAD', '__EGL_VENDOR_LIBRARY_DIRS', 'QSG_RHI_BACKEND'):
        (isolated/'shell.qml').write_text(f'//@ pragma DefaultEnv {key}=explicit\n')
        with patch.object(renderer, 'ROOT', isolated), patch.object(renderer.subprocess, 'run') as run:
            assert renderer.compatible_device(environment) is None
            run.assert_not_called()
    print('PASS every explicit GPU override, including empty values, bypasses optimization')

    library = root/'bootstrap.so'
    library.write_bytes(b'inert mocked library')
    restored = subprocess.CompletedProcess([], 0, json.dumps({'LD_PRELOAD': None, '__EGL_VENDOR_LIBRARY_FILENAMES': None, '__EGL_VENDOR_LIBRARY_DIRS': None}))
    with patch.object(renderer, 'compatible_device', return_value=fingerprint), patch.object(renderer, 'bootstrap_library', return_value=library):
        with patch.object(renderer.subprocess, 'run', side_effect=[restored, success]) as run:
            renderer.run_shell(command, environment)
            calls = run.call_args_list
            assert len(calls) == 2 and calls[1].kwargs['env']['LD_PRELOAD'].startswith('/proc/self/fd/')
            assert calls[1].kwargs['pass_fds'] and environment.get('LD_PRELOAD') is None
        failed_init = subprocess.CompletedProcess(command, 78)
        with patch.object(renderer.subprocess, 'run', side_effect=[restored, failed_init, success]) as run:
            renderer.run_shell(command, environment)
            assert run.call_count == 3 and run.call_args.kwargs['env'] == environment
            assert 'pass_fds' not in run.call_args.kwargs
        wrong_environment = subprocess.CompletedProcess([], 0, '{"LD_PRELOAD":"leaked"}')
        with patch.object(renderer.subprocess, 'run', side_effect=[wrong_environment, success]) as run:
            renderer.run_shell(command, environment)
            assert run.call_count == 2 and run.call_args.kwargs['env'] == environment
        failed_app = subprocess.CompletedProcess(command, 7)
        with patch.object(renderer.subprocess, 'run', side_effect=[restored, failed_app]) as run:
            try:
                renderer.run_shell(command, environment)
            except subprocess.CalledProcessError as error:
                assert error.returncode == 7 and run.call_count == 2
            else:
                raise AssertionError('An application error was hidden by the optional fallback')
    print('PASS pinned descriptor, environment check, initialization retry and application-error propagation')
