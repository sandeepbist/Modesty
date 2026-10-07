#!/usr/bin/env python3
"""Exercise the sleep delay and lock signals on an isolated logind test bus."""
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
name = dbus.service.BusName('org.freedesktop.login1', bus)
SESSION = '/org/freedesktop/login1/session/test'

class Manager(dbus.service.Object):
    read_fd = None
    @dbus.service.method('org.freedesktop.login1.Manager', in_signature='ssss', out_signature='h')
    def Inhibit(self, what, who, why, mode):
        assert what == 'sleep' and mode == 'delay'
        if self.read_fd is not None: os.close(self.read_fd)
        self.read_fd, fd = os.pipe()
        os.set_blocking(self.read_fd, False)
        result = dbus.types.UnixFd(fd); os.close(fd)
        return result
    @dbus.service.method('org.freedesktop.login1.Manager', in_signature='s', out_signature='o')
    def GetSession(self, ident): return SESSION
    @dbus.service.method('org.freedesktop.login1.Manager', in_signature='u', out_signature='o')
    def GetSessionByPID(self, pid): return SESSION
    @dbus.service.signal('org.freedesktop.login1.Manager', signature='b')
    def PrepareForSleep(self, active): pass
    def held(self):
        try: return os.read(self.read_fd, 1) != b''
        except BlockingIOError: return True

class Session(dbus.service.Object):
    locked = False
    @dbus.service.method('org.freedesktop.login1.Session', in_signature='b')
    def SetLockedHint(self, locked): self.locked = bool(locked)
    @dbus.service.signal('org.freedesktop.login1.Session')
    def Lock(self): pass

manager = Manager(bus, '/org/freedesktop/login1')
session = Session(bus, SESSION)
proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve().parents[1]/'scripts/session-events.py'), '--session-bus'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
events = []
def wait(check):
    end = time.monotonic() + 4
    while time.monotonic() < end:
        context = GLib.MainContext.default()
        while context.pending(): context.iteration(False)
        if select.select([proc.stdout], [], [], .01)[0]:
            line = proc.stdout.readline()
            if line: events.append(json.loads(line))
        if check(): return
    raise AssertionError(events)
def send(data): proc.stdin.write(json.dumps(data)+'\n'); proc.stdin.flush()
try:
    wait(lambda: any(e['event']=='ready' for e in events))
    assert manager.held()
    session.Lock(); wait(lambda: any(e['event']=='lock' for e in events))
    manager.PrepareForSleep(True); wait(lambda: any(e['event']=='sleep' for e in events))
    assert manager.held(), 'Sleep inhibitor released before secure acknowledgement'
    send({'locked': True, 'secure': True})
    wait(lambda: session.locked and not manager.held())
    manager.PrepareForSleep(False); wait(lambda: any(e['event']=='resume' for e in events))
    assert manager.held(), 'Sleep inhibitor was not reacquired after resume'
    send({'locked': False}); wait(lambda: not session.locked)
    print('PASS logind lock signal, hold until secure, resume rearm and unlock hint')
finally:
    proc.terminate(); proc.wait(timeout=3)
    if manager.read_fd is not None: os.close(manager.read_fd)
