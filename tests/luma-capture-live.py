#!/usr/bin/env python3
"""Verify private capture in a separate compositor. Never load plugins in the parent."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BLUE, GREEN, RED = (36, 104, 172), (56, 172, 100), (255, 34, 68)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin', type=Path)
    parser.add_argument('--with-plugin', type=Path, action='append', default=[])
    parser.add_argument('--production', action='store_true')
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--session-client', type=Path)
    parser.add_argument('--loader', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.baseline and not args.plugin:
        parser.error('Pass --plugin PATH or --baseline')
    for name in ('Hyprland', 'hyprctl', 'qs', 'grim', 'wtype', 'wf-recorder', 'ffmpeg'):
        if not shutil.which(name):
            raise SystemExit('Missing verification tool: '+name)
    if args.output:
        out = args.output.resolve()
        out.mkdir(parents=True, exist_ok=False)
    else:
        destination = ROOT/'output/luma-capture'
        destination.mkdir(parents=True, exist_ok=True)
        out = Path(tempfile.mkdtemp(prefix='run-', dir=destination))
    print('Evidence: '+str(out), flush=True)
    artifacts = [ROOT/'plugins/luma-capture/plugin.cpp', Path(__file__), ROOT/'tests/fixtures/luma-capture.qml']
    if args.plugin:
        artifacts.append(args.plugin.resolve(strict=True))
    artifacts.extend(path.resolve(strict=True) for path in args.with_plugin)
    (out/'manifest.json').write_text(json.dumps({str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts}, indent=2)+'\n')
    fixture = out/'fixture'
    fixture.mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'tests/fixtures/luma-capture.qml', fixture/'shell.qml')
    config = out/'nested.lua'
    config.write_text('''hl.monitor({output="",mode="800x600@60",position="0x0",scale=1})
hl.config({misc={disable_hyprland_logo=true,disable_splash_rendering=true},ecosystem={no_donation_nag=true,no_update_news=true},general={gaps_in=0,gaps_out=0,border_size=0},animations={enabled=false},decoration={rounding=0,blur={enabled=false},shadow={enabled=false}}})
''')
    parent = dict(os.environ)
    environment = dict(parent, AQ_DRM_DEVICES='/dev/dri/modesty-no-kms', HYPRLAND_NO_SD_NOTIFY='1', HYPRLAND_NO_SD_VARS='1',
                       XDG_CONFIG_HOME=str(out/'config'), XDG_STATE_HOME=str(out/'state'), XDG_CACHE_HOME=str(out/'cache'), QS_NO_RELOAD_POPUP='1')
    if args.loader:
        execs = Path(environment['XDG_CONFIG_HOME'])/'hypr/hyprland/execs.lua'
        execs.parent.mkdir(parents=True)
        execs.write_text('local fn   = require("utils.functions")\n')
        with config.open('a') as stream:
            stream.write('package.preload["utils.functions"]=function() return {} end\ndofile('+json.dumps(str(execs))+')\n')
    processes, measurements = [], []

    def run(command, env=None, timeout=12):
        result = subprocess.run(command, env=env or environment, capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            raise AssertionError(f'{command}: {result.stdout}\n{result.stderr}')
        return result.stdout.strip()

    def launch(command, name):
        log = (out/(name+'.log')).open('w')
        process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        log.close()
        processes.append(process)
        return process

    def wait(operation, label):
        deadline = time.monotonic()+12
        while time.monotonic() < deadline:
            if any(p.poll() is not None for p in processes):
                raise AssertionError('A fixture process exited. Read logs in '+str(out))
            try:
                value = operation()
                if value:
                    return value
            except (AssertionError, StopIteration, json.JSONDecodeError):
                pass
            time.sleep(.05)
        raise AssertionError('Timed out: '+label)

    def pixel_close(actual, expected, tolerance=3):
        return all(abs(a-b) <= tolerance for a, b in zip(actual, expected))

    def public_image(size, color, region=False):
        expected = Image.new('RGB', size, color)
        if not region:
            ImageDraw.Draw(expected).rectangle((20, 20, 79, 79), fill=(255, 255, 0))
        return expected

    def capture(name, expected=None, region=False):
        path = out/(name+'.png')
        command = ['grim', '-g', '100,140 500x300'] if region else ['grim', '-o', monitor]
        run([*command, str(path)])
        image = Image.open(path).convert('RGB')
        point = (50, 60) if region else (150, 200)
        actual = image.getpixel(point)
        measurements.append(dict(name=name, pixel=actual, size=image.size))
        if expected is not None:
            assert pixel_close(actual, expected), (name, actual, expected)
        if not region:
            assert pixel_close(image.getpixel((50, 50)), (255, 255, 0)), (name, 'background marker missing')
        if expected in (BLUE, GREEN):
            assert ImageChops.difference(image, public_image(image.size, expected, region)).getbbox() is None, (name, 'Unexpected captured pixels')
        return image

    def ipc(method, *values):
        return run(['qs', 'ipc', '--pid', str(shell.pid), 'call', 'capture-fixture', method, *map(str, values)])

    def local_capture(name, require_private=True):
        client = next(c for c in json.loads(run(['hyprctl', 'clients', '-j'], parent)) if c['pid'] == compositor.pid)
        x, y = client['at']
        width, height = client['size']
        nested_output = next(m for m in json.loads(run(['hyprctl', 'monitors', '-j'])) if m['name'] == monitor)
        width, height = min(width, nested_output['width']), min(height, nested_output['height'])
        path = out/(name+'.png')
        run(['grim', '-g', f'{x},{y} {width}x{height}', str(path)], parent)
        image = Image.open(path).convert('RGB')
        actual = image.getpixel((150, 200))
        if require_private:
            assert actual[0] > 180 and actual[1] < 100 and actual[2] < 130, ('local overlay missing', actual)
        return image

    try:
        compositor = launch(['Hyprland', '-c', str(config)], 'compositor')
        instance = wait(lambda: next(i for i in json.loads(run(['hyprctl', 'instances', '-j'], parent)) if i['pid'] == compositor.pid), 'nested compositor')
        assert instance['instance'] != parent.get('HYPRLAND_INSTANCE_SIGNATURE'), 'Refusing parent compositor'
        environment.update(WAYLAND_DISPLAY=instance['wl_socket'], HYPRLAND_INSTANCE_SIGNATURE=instance['instance'])

        def nested_monitor():
            monitors = json.loads(run(['hyprctl', 'monitors', '-j']))
            if not monitors:
                subprocess.run(['grim', '-g', '0,0 1x1', '-'], env=parent, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=3)
            return next(iter(monitors), None)

        monitor_data = wait(nested_monitor, 'nested monitor and parent presentation')
        assert monitor_data['hardwareDetails']['backend'] == 'wayland', 'Refusing physical compositor backend'
        monitor = monitor_data['name']
        assert not run(['hyprctl', 'configerrors']), 'Nested config errors'
        for extra in args.with_plugin:
            response = run(['hyprctl', 'plugin', 'load', str(extra.resolve(strict=True))])
            assert response == 'ok', response
        shell = launch(['qs', '-p', str(fixture)], 'fixture')
        wait(lambda: json.loads(ipc('state'))['opened'], 'private overlay')
        time.sleep(.25)
        capture('baseline-leak', RED)
        local_capture('baseline-local')
        run(['wtype', 'local typing'])
        assert json.loads(ipc('state'))['text'] == 'local typing', 'Local typing failed'
        run(['hyprctl', 'eval', 'hl.layer_rule({match={namespace="modesty-command-canvas"},no_screen_share=true})'])
        time.sleep(.1)
        run(['grim', '-o', monitor, str(out/'baseline-blackout.png')])
        blackout = Image.open(out/'baseline-blackout.png').convert('RGB')
        assert blackout.getpixel((150, 200)) == blackout.getpixel((700, 400)) == (0, 0, 0), 'Native masking baseline changed'
        run(['hyprctl', 'reload'])
        time.sleep(.2)
        capture('baseline-restored', RED)
        if args.baseline:
            print('PASS isolated leak, native blackout and local typing baselines')
            return
        plugin = args.plugin.resolve(strict=True)
        busy = launch(['wf-recorder', '-o', monitor, '-c', 'ffv1', '-x', 'bgr0', '-f', str(out/'preload-stream.mkv'), '-y'], 'preload-recorder')
        time.sleep(.35)
        refusal = run(['hyprctl', 'plugin', 'load', str(plugin)])
        assert 'Stop screen capture before loading' in refusal, 'Plugin accepted an existing capture session'
        busy.send_signal(signal.SIGINT)
        busy.wait(timeout=8)
        processes.remove(busy)
        time.sleep(.7)
        measurements.append(dict(name='active-load-refusal', refused=True))
        if args.loader:
            helper = ['python3', str(ROOT/'scripts/luma-capture.py')]
            plugin = Path(run([*helper, 'enable'], timeout=150))
            state = json.loads(run([*helper, 'status']))
            assert state['enabled'] and state['loaded'] and state['supported'], state
            assert run([*helper, 'restore']) == str(plugin)
            assert not run(['hyprctl', 'configerrors']), 'Generated bootstrap is invalid'
            measurements.append(dict(name='loader-enabled', status=state))
        else:
            response = run(['hyprctl', 'plugin', 'load', str(plugin)])
            assert response == 'ok', response
        assert 'luma-capture' in run(['hyprctl', 'plugin', 'list']), 'Plugin did not load'
        if args.session_client:
            result = run([str(args.session_client.resolve(strict=True))], dict(environment, MODESTY_CAPTURE_TEST='1'))
            assert compositor.poll() is None, 'Expired capture session crashed compositor'
            measurements.append(dict(name='expired-session', result=result, compositorAlive=True))
        local_capture('protected-local')
        for step in range(8):
            phase = step % 2
            ipc('phase', phase)
            ipc('popup', 'true' if phase else 'false')
            time.sleep(.08)
            expected = GREEN if phase else BLUE
            image = capture('protected-'+str(step), expected)
            assert pixel_close(image.getpixel((620, 50)), expected), 'Island leaks into capture'
            assert pixel_close(image.getpixel((600, 200)), expected), 'Popup leaks into capture'
            capture('region-'+str(step), expected, region=True)
        recorder = launch(['wf-recorder', '-o', monitor, '-c', 'ffv1', '-x', 'bgr0', '-r', '20', '-f', str(out/'stream.mkv'), '-y'], 'recorder')
        time.sleep(.25)
        for step in range(12):
            ipc('phase', step % 2)
            time.sleep(.1)
        recorder.send_signal(signal.SIGINT)
        recorder.wait(timeout=8)
        processes.remove(recorder)
        assert recorder.returncode == 0, 'Continuous capture failed'
        for old in out.glob('stream-frame-*.png'):
            old.unlink()
        run(['ffmpeg', '-v', 'error', '-i', str(out/'stream.mkv'), '-vf', 'fps=10', '-frames:v', '30', str(out/'stream-frame-%03d.png')])
        frames = sorted(out.glob('stream-frame-*.png'))
        assert len(frames) >= 8, 'Continuous capture produced too few frames'
        colors = set()
        for path in frames:
            image = Image.open(path).convert('RGB')
            actual = image.getpixel((150, 200))
            phase = next((i for i, color in enumerate((BLUE, GREEN)) if pixel_close(actual, color, tolerance=10)), None)
            assert phase is not None, ('Continuous capture leaks or blanks content', path, actual)
            assert pixel_close(image.getpixel((50, 50)), (255, 255, 0), tolerance=12), 'Continuous capture loses background'
            difference = ImageChops.difference(image, public_image(image.size, (BLUE, GREEN)[phase]))
            assert max(max(pair) for pair in difference.getextrema()) <= 1, 'Unexpected pixels in continuous capture'
            colors.add(phase)
        assert len(colors) == 2, 'Continuous capture freezes underlying desktop'
        measurements.append(dict(name='continuous', frames=len(frames), backgroundPhases=sorted(colors)))
        run(['hyprctl', 'eval', 'hl.config({animations={enabled=true}})'])
        for step in range(3):
            ipc('open', 'false')
            for frame in range(4):
                capture(f'closed-{step}-{frame}', GREEN)
            ipc('open', 'true')
            time.sleep(.3)
            capture('reopened-'+str(step), GREEN)
        run(['wtype', ' private'])
        assert json.loads(ipc('state'))['text'] == 'local typing private', 'Typing stopped after capture'
        local_capture('protected-local-final')
        run(['hyprctl', 'eval', 'hl.config({decoration={blur={enabled=true}}})'])
        ipc('publicContent', 'true')
        ipc('phase', 0)
        time.sleep(.5)
        public_images = []
        for name, opened in (('public-covered', 'true'), ('public-uncovered', 'false')):
            ipc('open', opened)
            time.sleep(.35)
            path = out/(name+'.png')
            run(['grim', '-o', monitor, str(path)])
            public_images.append(Image.open(path).convert('RGB'))
        crop = (140, 190, 400, 330)
        difference = ImageChops.difference(public_images[0].crop(crop), public_images[1].crop(crop))
        assert max(max(pair) for pair in difference.getextrema()) <= 2, 'Private overlay contaminates public blur'
        old_pixel = public_images[1].getpixel((150, 200))
        assert not pixel_close(old_pixel, BLUE), 'Public window was not rendered'
        ipc('phase', 1)
        time.sleep(.15)
        path = out/'public-background-changed.png'
        run(['grim', '-o', monitor, str(path)])
        new_pixel = Image.open(path).convert('RGB').getpixel((150, 200))
        assert not pixel_close(new_pixel, old_pixel, tolerance=8), 'Public blur cache freezes background'
        measurements.append(dict(name='public-blur', before=old_pixel, after=new_pixel, privateOverlayDifference=difference.getextrema()))
        run(['hyprctl', 'eval', 'hl.config({animations={enabled=false}})'])
        ipc('publicContent', 'false')
        run(['hyprctl', 'eval', 'hl.config({render={use_shader_blur_blend=false}})'])
        run(['hyprctl', 'eval', 'hl.layer_rule({match={namespace="modesty-capture-public-alpha"},blur=true,ignore_alpha=0.2})'])
        ipc('publicHoles', 'true')
        ipc('open', 'false')
        time.sleep(.5)
        run(['hyprctl', 'plugin', 'unload', str(plugin)])
        run(['grim', '-o', monitor, str(out/'legacy-blur-native.png')])
        native = Image.open(out/'legacy-blur-native.png').convert('RGB')
        time.sleep(.7)
        response = run(['hyprctl', 'plugin', 'load', str(plugin)])
        assert response == 'ok', response
        run(['grim', '-o', monitor, str(out/'legacy-blur-captured.png')])
        exported = Image.open(out/'legacy-blur-captured.png').convert('RGB')
        difference = ImageChops.difference(native, exported)
        assert max(max(pair) for pair in difference.getextrema()) <= 2, ('Legacy blur differs from local rendering', difference.getextrema())
        measurements.append(dict(name='legacy-stencil-blur', nativeDifference=difference.getextrema()))
        ipc('publicHoles', 'false')
        ipc('publicContent', 'true')
        run(['hyprctl', 'eval', 'hl.config({render={use_shader_blur_blend=true},animations={enabled=true}})'])
        time.sleep(.3)
        if 'scrolloverview' in run(['hyprctl', 'plugin', 'list']):
            run(['hyprctl', 'eval', 'hl.config({general={layout="scrolling"}})'])
            ipc('open', 'true')
            time.sleep(.3)
            before = local_capture('overview-local-before')
            run(['grim', '-o', monitor, str(out/'overview-capture-before.png')])
            run(['hyprctl', 'eval', 'hl.plugin.scrolloverview.overview("on all")'])
            time.sleep(.35)
            after = local_capture('overview-local-active', require_private=False)
            assert ImageChops.difference(before, after).getbbox() is not None, 'Overview did not change the local scene'
            run(['grim', '-o', monitor, str(out/'overview-capture-active.png')])
            before_capture = Image.open(out/'overview-capture-before.png').convert('RGB')
            active_capture = Image.open(out/'overview-capture-active.png').convert('RGB')
            assert ImageChops.difference(before_capture, active_capture).getbbox() is None, 'Overview bypasses clean capture'
            run(['hyprctl', 'eval', 'hl.plugin.scrolloverview.overview("off")'])
            time.sleep(.35)
            measurements.append(dict(name='active-overview', localChanged=True, captureDifference=0))
        ipc('publicContent', 'false')
        ipc('open', 'true')
        time.sleep(.4)
        run(['hyprctl', 'eval', f'hl.monitor({{output="{monitor}",mode="800x600@60",position="0x0",scale=1.25}})'])
        time.sleep(.25)
        refused = subprocess.run(['grim', '-o', monitor, str(out/'unsupported.png')], env=environment, capture_output=True, text=True, timeout=5)
        assert refused.returncode != 0 and 'failed to copy' in refused.stderr, 'Unsupported output did not refuse capture'
        assert compositor.poll() is None, 'Unsupported capture crashed compositor'
        measurements.append(dict(name='unsupported-scale', refused=True, error=refused.stderr.strip()))
        run(['hyprctl', 'eval', f'hl.monitor({{output="{monitor}",mode="800x600@60",position="0x0",scale=1}})'])
        wait(lambda: capture('supported-restored', GREEN), 'public clients repaint after scale restore')
        if args.production:
            ipc('open', 'false')
            environment.update(MODESTY_PREVIEW='1', MODESTY_COMPAT='0', MODESTY_SCREEN=monitor)
            production = launch(['qs', '-p', str(ROOT/'shell.qml')], 'production')

            def canvas(method, *values):
                return run(['qs', 'ipc', '--pid', str(production.pid), 'call', 'canvas', method, *values])

            wait(lambda: json.loads(canvas('status')), 'production canvas')
            canvas('search', 'private production fixture')
            wait(lambda: json.loads(canvas('status'))['inputFocused'], 'production input focus')
            run(['wtype', ' typing'])
            state = json.loads(canvas('status'))
            assert state['query'] == 'private production fixture typing', 'Production typing failed'
            time.sleep(.5)
            canvas('capture', str(out/'production-card.png'))
            wait(lambda: (out/'production-card.png').exists(), 'local production card')
            capture('production-captured', GREEN)
            client = next(c for c in json.loads(run(['hyprctl', 'clients', '-j'], parent)) if c['pid'] == compositor.pid)
            x, y = client['at']
            width, height = min(client['size'][0], 800), min(client['size'][1], 600)
            run(['grim', '-g', f'{x},{y} {width}x{height}', str(out/'production-local.png')], parent)
            ipc('phase', 0)
            time.sleep(.15)
            capture('production-captured-blue', BLUE)
            ipc('phase', 1)
            canvas('close')
            time.sleep(.4)
            run(['grim', '-o', monitor, str(out/'production-closed.png')])
            opened = Image.open(out/'production-captured.png').convert('RGB')
            closed = Image.open(out/'production-closed.png').convert('RGB')
            assert ImageChops.difference(opened, closed).getbbox() is None, 'Production canvas changes exported pixels'
            measurements.append(dict(name='production-canvas', query=state['query'], focused=state['inputFocused']))
            production.terminate()
            production.wait(timeout=5)
            processes.remove(production)
            environment.update(MODESTY_PREVIEW=parent.get('MODESTY_PREVIEW', '0'), MODESTY_COMPAT=parent.get('MODESTY_COMPAT', '0'))
            ipc('open', 'true')
            time.sleep(.4)
        unloading = launch(['wf-recorder', '-o', monitor, '-c', 'ffv1', '-x', 'bgr0', '-r', '20', '-f', str(out/'unload-stream.mkv'), '-y'], 'unload-recorder')
        time.sleep(.2)
        if args.loader:
            run([*helper, 'disable'])
            state = json.loads(run([*helper, 'status']))
            assert not state['enabled'] and not state['loaded'], state
            assert not run(['hyprctl', 'configerrors']), 'Disabled bootstrap is invalid'
            measurements.append(dict(name='loader-disabled', status=state))
        else:
            run(['hyprctl', 'plugin', 'unload', str(plugin)])
        ipc('phase', 0)
        time.sleep(.15)
        unloading.send_signal(signal.SIGINT)
        unloading.wait(timeout=8)
        processes.remove(unloading)
        assert compositor.poll() is None, 'Unloading during capture crashed compositor'
        measurements.append(dict(name='active-unload', compositorAlive=True))
        time.sleep(.1)
        capture('unloaded-leak', RED)
        if args.loader:
            time.sleep(.7)
            run([*helper, 'enable'], timeout=150)
            for process in (shell, compositor):
                process.terminate()
                process.wait(timeout=8)
                processes.remove(process)
            environment.update(WAYLAND_DISPLAY=parent['WAYLAND_DISPLAY'], HYPRLAND_INSTANCE_SIGNATURE=parent['HYPRLAND_INSTANCE_SIGNATURE'])
            compositor = launch(['Hyprland', '-c', str(config)], 'startup-compositor')
            instance = wait(lambda: next(i for i in json.loads(run(['hyprctl', 'instances', '-j'], parent)) if i['pid'] == compositor.pid), 'startup compositor')
            assert instance['instance'] != parent.get('HYPRLAND_INSTANCE_SIGNATURE'), 'Refusing parent compositor'
            environment.update(WAYLAND_DISPLAY=instance['wl_socket'], HYPRLAND_INSTANCE_SIGNATURE=instance['instance'])
            wait(nested_monitor, 'startup nested output')
            state = wait(lambda: (state if (state := json.loads(run([*helper, 'status'])))['loaded'] else None), 'startup plugin restore')
            assert state['enabled'] and state['supported'], state
            assert not run(['hyprctl', 'configerrors']), 'Startup bootstrap is invalid'
            measurements.append(dict(name='loader-cold-start', status=state))
            run([*helper, 'disable'])
        print('PASS isolated private full/region and continuous captures, changing background, popups, island, animated reopen, typing and unload')
    finally:
        (out/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=4)


if __name__ == '__main__':
    main()
