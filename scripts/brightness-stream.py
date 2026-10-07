#!/usr/bin/env python3
"""Apply a stream of backlight targets through logind, without per-frame processes."""
import json
import os
from pathlib import Path
import re
import sys


def serve(device, fd=0):
    import dbus
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', device):
        raise ValueError('Invalid backlight device')
    maximum = int((Path('/sys/class/backlight') / device / 'max_brightness').read_text())
    bus = dbus.SystemBus()
    session = dbus.Interface(bus.get_object('org.freedesktop.login1', '/org/freedesktop/login1/session/auto'),
                             'org.freedesktop.login1.Session')
    pending = b''
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            return
        pending += chunk
        lines = pending.split(b'\n')
        pending = lines.pop()
        if not lines:
            continue
        # If input accumulated while logind was busy, apply only the newest target.
        sequence = -1
        try:
            request = json.loads(lines[-1])
            sequence = int(request['sequence'])
            value = max(1, min(maximum, int(request['value'])))
            session.SetBrightness('backlight', device, dbus.UInt32(value), timeout=2)
            result = {'ok': True, 'sequence': sequence, 'value': value / maximum}
        except Exception as error:
            result = {'ok': False, 'sequence': sequence, 'error': str(error)}
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    try:
        serve(sys.argv[1])
    except Exception as error:
        print(json.dumps({'ok': False, 'error': str(error)}), flush=True)
        sys.exit(1)
