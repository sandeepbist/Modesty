#!/usr/bin/env python3
"""Event-driven logind bridge, keeping its sleep delay until the compositor locks."""
import json
import os
import sys
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

def emit(event, **data):
    print(json.dumps(dict(event=event, **data)), flush=True)

def main():
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus() if '--session-bus' in sys.argv[1:] else dbus.SystemBus()
    manager = dbus.Interface(bus.get_object('org.freedesktop.login1', '/org/freedesktop/login1'), 'org.freedesktop.login1.Manager')
    loop = GLib.MainLoop()
    inhibitor = None
    idle_inhibitor = None
    def acquire():
        nonlocal inhibitor
        if inhibitor is None:
            inhibitor = manager.Inhibit('sleep', 'Modesty', 'Lock screen before sleeping', 'delay').take()
    def release():
        nonlocal inhibitor
        if inhibitor is not None:
            os.close(inhibitor); inhibitor = None
    def keep_awake(enabled):
        nonlocal idle_inhibitor
        if enabled and idle_inhibitor is None:
            idle_inhibitor = manager.Inhibit('idle', 'Modesty', 'Keep Awake', 'block').take()
        elif not enabled and idle_inhibitor is not None:
            os.close(idle_inhibitor); idle_inhibitor = None
        emit('awake', active=idle_inhibitor is not None)
    def sleep_changed(sleeping):
        if sleeping:
            emit('sleep')
        else:
            acquire(); emit('resume')
    manager.connect_to_signal('PrepareForSleep', sleep_changed)
    session_id = os.environ.get('XDG_SESSION_ID')
    path = manager.GetSession(session_id) if session_id else manager.GetSessionByPID(os.getpid())
    session = dbus.Interface(bus.get_object('org.freedesktop.login1', path), 'org.freedesktop.login1.Session')
    session.connect_to_signal('Lock', lambda: emit('lock'))
    def read(_source, condition):
        if condition & GLib.IO_IN:
            line = sys.stdin.readline()
            if not line:
                loop.quit(); return False
            data = json.loads(line)
            if 'awake' in data:
                try: keep_awake(bool(data['awake']))
                except Exception as error: emit('awake', active=False, error=str(error))
            if 'locked' in data:
                session.SetLockedHint(bool(data['locked']))
            if data.get('secure'):
                release()
        elif condition & (GLib.IO_HUP | GLib.IO_ERR):
            loop.quit(); return False
        return True
    GLib.io_add_watch(sys.stdin, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, read)
    acquire()
    emit('ready')
    try:
        loop.run()
    finally:
        release()
        if idle_inhibitor is not None: os.close(idle_inhibitor)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        emit('error', message=str(exc)); sys.exit(1)
