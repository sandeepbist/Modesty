#!/usr/bin/env python3
"""Observe camera device ownership without opening or reading camera devices."""
import ctypes
import json
import os
from pathlib import Path
import re
import select
import struct
import time


def camera_users(devices):
    """Only inspect accessible process metadata and descriptor symlinks."""
    users = []
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            holds_camera = False
            for fd in (process / 'fd').iterdir():
                try:
                    if os.readlink(fd) in devices:
                        holds_camera = True
                        break
                except OSError:
                    continue
            if not holds_camera:
                continue
            name = (process / 'comm').read_text().strip()
            users.append({'pid': int(process.name), 'label': name.replace('-', ' ').title(), 'directCamera': True})
        except (OSError, PermissionError):
            continue
    return users


def watch(directory=Path('/dev')):
    # Device open/close events avoid repeatedly scanning every process at idle.
    libc = ctypes.CDLL(None, use_errno=True)
    libc.inotify_init1.argtypes = [ctypes.c_int]
    libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
    descriptor = libc.inotify_init1(os.O_CLOEXEC | os.O_NONBLOCK)
    if descriptor < 0:
        raise OSError(ctypes.get_errno(), 'Cannot observe camera devices')
    directory_watch = libc.inotify_add_watch(descriptor, os.fsencode(directory), 0x100 | 0x200 | 0x40 | 0x80)
    if directory_watch < 0:
        os.close(descriptor)
        raise OSError(ctypes.get_errno(), 'Cannot observe device directory')
    watched = {}
    last = None
    deadline = 0
    refresh_at = 0
    try:
        while True:
            now = time.monotonic()
            if now >= deadline:
                devices = {str(p) for p in directory.iterdir() if re.fullmatch(r'video\d+', p.name)}
                for path in devices - watched.keys():
                    number = libc.inotify_add_watch(descriptor, os.fsencode(path), 0x20 | 0x8 | 0x10 | 0x400 | 0x800)
                    if number >= 0:
                        watched[path] = number
                for path in list(watched):
                    if path not in devices:
                        watched.pop(path)
                users = camera_users(devices) if devices else []
                users.sort(key=lambda user: user['pid'])
                payload = json.dumps(users, separators=(',', ':'))
                if payload != last:
                    print(payload, flush=True)
                    last = payload
                # Safety reconciliation also catches inaccessible watches or missed events.
                refresh_at = now + 15
                deadline = refresh_at
            if select.select([descriptor], [], [], max(0, deadline - time.monotonic()))[0]:
                data = os.read(descriptor, 65536)
                offset = 0
                changed = False
                while offset < len(data):
                    number, mask, _, length = struct.unpack_from('iIII', data, offset)
                    name = data[offset + 16:offset + 16 + length].split(b'\0', 1)[0]
                    if number != directory_watch or re.fullmatch(rb'video\d+', name) or mask & 0x4000:
                        changed = True
                    if mask & 0x8000:
                        watched = {path: value for path, value in watched.items() if value != number}
                    offset += 16 + length
                if changed:
                    deadline = min(refresh_at, time.monotonic() + .15)
    finally:
        os.close(descriptor)


if __name__ == '__main__':
    try:
        watch()
    except (OSError, BrokenPipeError):
        pass
