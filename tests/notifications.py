#!/usr/bin/env python3
"""Run with dbus-run-session -- python3 tests/notifications.py."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '''import QtQuick
import Quickshell
import Quickshell.Io
import qs.services
ShellRoot {
    property var notifications: Notifications.list
    IpcHandler {
        target: "check"
        function debug(): string { return JSON.stringify(Notifications.list.map(n => ({ serial:n.serial, popup:n.popup, closing:n.popupClosing, hovered:n.popupHovered, source:!!n.notification, timeout:n.timeout, appName:n.appName, appIcon:n.appIcon, summary:n.summary, body:n.body, sameHistory:Notifications.historyModel.get(0).record===n }))); }
        function count(): int { return Notifications.list.length; }
        function popups(): int { return Notifications.popups.length; }
        function dnd(): void { Notifications.dnd = true; }
        function invoke(): void { Notifications.list[0].invokeAction("default"); }
        function hover(): void { Notifications.list[0].popupHovered = true; }
        function unhover(): void { Notifications.list[0].popupHovered = false; }
        function burst(): void {
            for (let i = 0; i < 80; i++) Notifications.remind("burst-" + i, "Burst " + i, "", () => {}, () => {});
        }
        function oldest(): string { return Notifications.list[Notifications.list.length - 1]?.summary || ""; }
    }
}
'''

def wait_for(predicate):
    end = time.monotonic() + 5
    while time.monotonic() < end:
        while GLib.MainContext.default().pending(): GLib.MainContext.default().iteration(False)
        if predicate(): return
        time.sleep(.05)
    raise AssertionError('Timed out waiting for notification state')

with tempfile.TemporaryDirectory(prefix='modesty-notifications-') as tmp:
    directory = Path(tmp)
    for name in ['services', 'theme', 'modules', 'components', 'scripts', 'assets']:
        (directory / name).symlink_to(ROOT / name, target_is_directory=True)
    (directory / 'shell.qml').write_text(SOURCE)
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', MODESTY_PREVIEW='', XDG_STATE_HOME=str(directory/'state'))
    with (directory/'log').open('w+') as log:
        proc = subprocess.Popen(['quickshell','-p',str(directory),'--no-color'], env=env, stdout=log, stderr=subprocess.STDOUT)
        def call(method):
            result = subprocess.run(['quickshell','ipc','--pid',str(proc.pid),'call','check',method],capture_output=True,text=True,timeout=3)
            return result.stdout.strip() if result.returncode == 0 else ''
        try:
            wait_for(lambda: call('count') == '0')
            DBusGMainLoop(set_as_default=True)
            bus = dbus.SessionBus()
            obj = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
            service = dbus.Interface(obj, 'org.freedesktop.Notifications')
            closed, actions = [], []
            service.connect_to_signal('NotificationClosed', lambda ident, reason: closed.append((int(ident), int(reason))))
            service.connect_to_signal('ActionInvoked', lambda ident, action: actions.append(str(action)))
            def notify(title, timeout, with_action=False, replace=0, app='Modesty test', icon='', body='Isolated test bus', hints=None):
                return int(service.Notify(app, dbus.UInt32(replace), icon, title, body, dbus.Array(['default', 'Open'] if with_action else [], signature='s'), dbus.Dictionary(hints or {}, signature='sv'), dbus.Int32(timeout)))
            def newest():
                return json.loads(call('debug'))[0]
            ident = notify('Original', 0)
            wait_for(lambda: call('count') == '1')
            serial = newest()['serial']
            assert notify('Updated', 700, replace=ident, app='Updated app', icon='dialog-information', body='Updated body') == ident
            wait_for(lambda: newest()['summary'] == 'Updated')
            updated = newest()
            assert (updated['appName'], updated['appIcon'], updated['body'], updated['timeout']) == ('Updated app', 'dialog-information', 'Updated body', 700), updated
            assert updated['serial'] == serial and updated['sameHistory'] and call('count') == '1'
            wait_for(lambda: (ident, 1) in closed)
            assert newest()['summary'] == 'Updated' and newest()['body'] == 'Updated body' and not newest()['source']
            print('PASS replacement updates retained metadata, deadline, identity and final history')
            ident = notify('Renew me', 1200)
            wait_for(lambda: call('popups') == '1')
            time.sleep(.75)
            assert notify('Renewed title', 1200, replace=ident) == ident
            wait_for(lambda: newest()['summary'] == 'Renewed title')
            time.sleep(.65)
            assert newest()['popup'] and not newest()['closing'], newest()
            time.sleep(.15)
            notify('Renewed title', 1200, replace=ident, hints={'urgency': dbus.Byte(2)})
            time.sleep(.65)
            assert newest()['popup'] and not newest()['closing'], newest()
            call('hover')
            notify('Hovered replacement', 700, replace=ident)
            wait_for(lambda: newest()['summary'] == 'Hovered replacement')
            time.sleep(.9)
            assert newest()['hovered'] and newest()['popup'] and not newest()['closing'], newest()
            call('unhover')
            wait_for(lambda: (ident, 1) in closed)
            print('PASS unchanged-timeout metadata and hints renew expiry; hover still pauses')
            ident = notify('Final before close', 0)
            wait_for(lambda: call('popups') == '1')
            notify('Final at close', 0, replace=ident, body='Final body')
            service.CloseNotification(dbus.UInt32(ident))
            wait_for(lambda: not newest()['source'])
            assert newest()['summary'] == 'Final at close' and newest()['body'] == 'Final body', newest()
            wait_for(lambda: call('popups') == '0')
            print('PASS immediate sender close preserves final replacement snapshot')
            ident = notify('Expiry check', 700)
            wait_for(lambda: call('popups') == '1')
            wait_for(lambda: (ident, 1) in closed)
            assert call('popups') == '0'
            assert call('count') == '4'
            print('PASS real D-Bus delivery, expiry signal, history retained')
            notify('Action check', 0, True)
            wait_for(lambda: call('popups') == '1')
            call('invoke')
            wait_for(lambda: 'default' in actions)
            print('PASS real notification action reaches sender')
            call('dnd')
            ident = notify('Quiet notification', 1000)
            wait_for(lambda: call('count') == '6')
            quiet = newest()
            notify('Quiet replacement', 700, replace=ident)
            wait_for(lambda: newest()['summary'] == 'Quiet replacement')
            assert not newest()['popup'] and not newest()['closing'] and newest()['serial'] == quiet['serial'], newest()
            wait_for(lambda: call('popups') == '0')
            print('PASS DND stores history without showing a popup')
            call('burst')
            wait_for(lambda: call('count') == '50')
            assert call('oldest') == 'Burst 30'
            print('PASS notification burst retains exactly the newest 50 records after close animations')
        finally:
            proc.terminate(); proc.wait(timeout=5)
            log.seek(0); content = log.read()
            if 'ERROR' in content or 'WARN scene' in content:
                raise AssertionError(content)
