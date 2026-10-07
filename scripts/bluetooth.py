#!/usr/bin/env python3
"""One BlueZ operation with an explicit pairing agent; JSON lines over private pipes."""
import json
import re
import sys
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

BLUEZ = 'org.bluez'
AGENT = 'org.bluez.Agent1'
AGENT_PATH = '/org/modesty/PairAgent'
DEVICE = 'org.bluez.Device1'
PROPS = 'org.freedesktop.DBus.Properties'

class Rejected(dbus.DBusException):
    _dbus_error_name = 'org.bluez.Error.Rejected'

def emit(**payload):
    print(json.dumps(payload), flush=True)

class PairAgent(dbus.service.Object):
    def __init__(self, bus, path):
        super().__init__(bus, AGENT_PATH)
        self.device_path = path
        self.pending = None

    def check(self, device):
        if str(device) != self.device_path:
            raise Rejected('This device was not selected')

    def prompt(self, device, kind, success, failure, code=''):
        self.check(device)
        self.reject()
        self.pending = (kind, success, failure)
        emit(event='prompt', kind=kind, code=code)

    def reject(self):
        if self.pending:
            _, _, failure = self.pending
            self.pending = None
            failure(Rejected('Pairing cancelled'))

    def answer(self, data):
        if not self.pending:
            return
        kind, success, failure = self.pending
        self.pending = None
        value = str(data.get('value', ''))
        if not data.get('accept'):
            failure(Rejected('Pairing declined'))
        elif kind == 'pin':
            if not 1 <= len(value) <= 16:
                failure(Rejected('PIN must contain 1–16 characters'))
            else:
                success(value)
        elif kind == 'passkey':
            if not re.fullmatch(r'[0-9]{1,6}', value):
                failure(Rejected('Passkey must contain 1–6 digits'))
            else:
                success(dbus.UInt32(int(value)))
        else:
            success()
        emit(event='waiting')

    @dbus.service.method(AGENT, in_signature='', out_signature='')
    def Release(self):
        self.reject()

    @dbus.service.method(AGENT, in_signature='', out_signature='')
    def Cancel(self):
        self.reject()
        emit(event='waiting')

    @dbus.service.method(AGENT, in_signature='o', out_signature='s', async_callbacks=('success', 'failure'))
    def RequestPinCode(self, device, success, failure):
        self.prompt(device, 'pin', success, failure)

    @dbus.service.method(AGENT, in_signature='o', out_signature='u', async_callbacks=('success', 'failure'))
    def RequestPasskey(self, device, success, failure):
        self.prompt(device, 'passkey', success, failure)

    @dbus.service.method(AGENT, in_signature='ou', out_signature='', async_callbacks=('success', 'failure'))
    def RequestConfirmation(self, device, passkey, success, failure):
        self.prompt(device, 'confirm', success, failure, f'{int(passkey):06d}')

    @dbus.service.method(AGENT, in_signature='o', out_signature='', async_callbacks=('success', 'failure'))
    def RequestAuthorization(self, device, success, failure):
        self.prompt(device, 'authorize', success, failure)

    @dbus.service.method(AGENT, in_signature='os', out_signature='')
    def DisplayPinCode(self, device, pincode):
        self.check(device)
        emit(event='prompt', kind='display', code=str(pincode))

    @dbus.service.method(AGENT, in_signature='ouq', out_signature='')
    def DisplayPasskey(self, device, passkey, entered):
        self.check(device)
        emit(event='prompt', kind='display', code=f'{int(passkey):06d}', entered=int(entered))

    @dbus.service.method(AGENT, in_signature='os', out_signature='')
    def AuthorizeService(self, device, uuid):
        self.check(device)

def main():
    mode, path = sys.argv[1:3]
    if mode not in {'pair', 'connect', 'disconnect', 'forget'} or not re.fullmatch(r'/org/bluez/hci[0-9]+/dev_(?:[0-9A-Fa-f]{2}_){5}[0-9A-Fa-f]{2}', path):
        raise ValueError('Select a valid Bluetooth device')
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus() if '--session-bus' in sys.argv[3:] else dbus.SystemBus()
    loop = GLib.MainLoop()
    agent = PairAgent(bus, path)
    obj = bus.get_object(BLUEZ, path)
    device = dbus.Interface(obj, DEVICE)
    finished = False

    def done(ok=True, message=''):
        nonlocal finished
        if finished:
            return
        finished = True
        emit(event='result', ok=ok, error=message)
        loop.quit()

    def failed(error):
        done(False, str(error))

    def cancel():
        agent.reject()
        if mode == 'pair':
            device.CancelPairing(reply_handler=lambda: None, error_handler=lambda _: None)
        done(False, 'Pairing cancelled' if mode == 'pair' else 'Operation cancelled')

    def read_input(_source, condition):
        if condition & GLib.IO_IN:
            line = sys.stdin.readline()
            if not line:
                cancel(); return False
            try:
                data = json.loads(line)
                if data.get('cancel'):
                    cancel()
                else:
                    agent.answer(data)
            except (ValueError, TypeError):
                cancel()
        elif condition & (GLib.IO_HUP | GLib.IO_ERR):
            cancel(); return False
        return not finished

    GLib.io_add_watch(sys.stdin, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, read_input)
    def expired():
        agent.reject()
        if mode == 'pair':
            device.CancelPairing(reply_handler=lambda: None, error_handler=lambda _: None)
        done(False, 'Device did not respond. Put it in pairing mode and try again.')
        return False
    GLib.timeout_add_seconds(90 if mode == 'pair' else 40, expired)

    def connect():
        device.Connect(reply_handler=lambda: done(), error_handler=failed, timeout=35)

    if mode == 'pair':
        manager = dbus.Interface(bus.get_object(BLUEZ, '/org/bluez'), 'org.bluez.AgentManager1')
        manager.RegisterAgent(AGENT_PATH, 'KeyboardDisplay')
        def paired():
            # Trust only the device explicitly paired by the user.
            props = dbus.Interface(obj, PROPS)
            props.Set(DEVICE, 'Trusted', dbus.Boolean(True), reply_handler=connect, error_handler=failed)
        device.Pair(reply_handler=paired, error_handler=failed, timeout=85)
    elif mode == 'connect':
        connect()
    elif mode == 'disconnect':
        device.Disconnect(reply_handler=lambda: done(), error_handler=failed, timeout=35)
    else:
        adapter = dbus.Interface(bus.get_object(BLUEZ, path.rsplit('/', 1)[0]), 'org.bluez.Adapter1')
        adapter.RemoveDevice(path, reply_handler=lambda: done(), error_handler=failed, timeout=35)
    loop.run()

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        emit(event='result', ok=False, error=str(exc))
        sys.exit(1)
