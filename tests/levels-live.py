#!/usr/bin/env python3
"""Opt-in native timing check; briefly changes levels and restores them in finally."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

if '--live' not in sys.argv:
    raise SystemExit('Pass --live to test real volume/backlight feedback; levels are restored.')
ROOT = Path(__file__).resolve().parents[1]
BASE = ['quickshell', 'ipc', '-p', str(ROOT / 'shell.qml'), 'call', 'island']


def call(name):
    return json.loads(subprocess.check_output(BASE + [name], text=True, timeout=4))


health = call('health')
assert not health['locked'] and not health['secure'] and not health['preview'], health
initial = call('geometry')
assert initial['menu'] == 'none', 'Close menus before timing the resting clock'
raw = subprocess.check_output(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'], text=True)
volume = float(raw.split()[1])
backlights = list(Path('/sys/class/backlight').glob('*'))
records = {}


def exercise(kind, apply, original, step):
    time.sleep(2.3)
    samples, errors = [], []
    started = time.monotonic()

    def feed():
        try:
            for index in range(22):
                apply(original + step * (index % 6 + 1))
                time.sleep(.075)
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=feed)
    worker.start()
    try:
        while worker.is_alive():
            state = call('geometry')
            stage = state['stages'][1]
            samples.append({'seconds': round(time.monotonic() - started, 3),
                            'panel': state['panel'], 'level': state['level'],
                            'width': stage['width'], 'target': stage['targetWidth'],
                            'height': stage['height']})
            time.sleep(.025)
    finally:
        worker.join(timeout=5)
        apply(original)
    assert not errors, errors
    showing = [s for s in samples if s['panel'] == 'context' and s['level']['kind'] == kind]
    assert showing, (kind, samples)
    settled = next((s for s in showing if s['level']['progress'] == 1
                    and abs(s['width'] - s['target']) < .1), None)
    assert settled and settled['seconds'] - showing[0]['seconds'] < .7, (kind, samples)
    assert len({round(s['level']['value'], 4) for s in showing}) >= 3, (kind, samples)
    assert all(s['height'] == initial['stages'][1]['height'] for s in showing)
    records[kind] = samples
    print(f"PASS native {kind}: settled in {settled['seconds'] - showing[0]['seconds']:.3f}s while updates continued; restored level")


exercise('volume', lambda value: subprocess.run(
    ['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', str(value)],
    check=True, stdout=subprocess.DEVNULL), volume, -.005 if volume > .04 else .005)
if backlights:
    device = backlights[0]
    original = int((device / 'brightness').read_text())
    maximum = int((device / 'max_brightness').read_text())
    step = max(1, maximum // 500) * (-1 if original > maximum * .04 else 1)
    exercise('brightness', lambda value: subprocess.run(
        ['brightnessctl', '-d', device.name, 'set', str(int(value))],
        check=True, stdout=subprocess.DEVNULL), original, step)
Path('/tmp/modesty-level-timing.json').write_text(json.dumps(records, indent=2))
