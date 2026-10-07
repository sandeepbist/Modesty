#!/usr/bin/env python3
"""Run in dbus-run-session: actual Agent1 calls against a fake BlueZ service."""
import json
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
name = dbus.service.BusName('org.bluez', bus)
PATH = '/org/bluez/hci0/dev_00_11_22_33_44_55'
BLUEZ_DEVICE = 'org.bluez.Device1'

class Manager(dbus.service.Object):
    sender = ''
    path = ''
    @dbus.service.method('org.bluez.AgentManager1', in_signature='os', sender_keyword='sender')
    def RegisterAgent(self, path, capability, sender):
        assert capability == 'KeyboardDisplay'
        self.sender, self.path = sender, path

manager = Manager(bus, '/org/bluez')

class Device(dbus.service.Object):
    mode = 'confirm'
    trusted = False
    connected = False
    received = None
    @dbus.service.method(BLUEZ_DEVICE, async_callbacks=('success', 'failure'))
    def Pair(self, success, failure):
        agent = dbus.Interface(bus.get_object(manager.sender, manager.path), 'org.bluez.Agent1')
        def accepted(*values):
            self.received = values
            success()
        if self.mode == 'pin':
            agent.RequestPinCode(PATH, reply_handler=accepted, error_handler=failure)
        elif self.mode == 'passkey':
            agent.RequestPasskey(PATH, reply_handler=accepted, error_handler=failure)
        elif self.mode == 'authorize':
            agent.RequestAuthorization(PATH, reply_handler=accepted, error_handler=failure)
        elif self.mode == 'display':
            agent.DisplayPasskey(PATH, dbus.UInt32(1234), dbus.UInt16(2), reply_handler=lambda: success(), error_handler=failure)
        else:
            agent.RequestConfirmation(PATH, dbus.UInt32(1234), reply_handler=accepted, error_handler=failure)
    @dbus.service.method(BLUEZ_DEVICE)
    def CancelPairing(self):
        pass
    @dbus.service.method(BLUEZ_DEVICE)
    def Connect(self):
        self.connected = True
    @dbus.service.method(BLUEZ_DEVICE)
    def Disconnect(self):
        self.connected = False
    @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='ssv')
    def Set(self, interface, key, value):
        assert interface == BLUEZ_DEVICE and key == 'Trusted'
        self.trusted = bool(value)

device = Device(bus, PATH)
class Adapter(dbus.service.Object):
    removed = False
    @dbus.service.method('org.bluez.Adapter1', in_signature='o')
    def RemoveDevice(self, path):
        assert path == PATH
        self.removed = True
adapter = Adapter(bus, '/org/bluez/hci0')

def pump():
    context = GLib.MainContext.default()
    while context.pending():
        context.iteration(False)

def run(mode, response=None, operation='pair'):
    device.mode, device.trusted, device.received = mode, False, None
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve().parents[1]/'scripts/bluetooth.py'), operation, PATH, '--session-bus'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    events = []
    try:
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            pump()
            if select.select([proc.stdout], [], [], .01)[0]:
                line = proc.stdout.readline()
                if not line:
                    break
                event = json.loads(line); events.append(event)
                if event['event'] == 'prompt' and mode != 'display':
                    assert device.trusted is False and device.received is None, 'Agent accepted without user input'
                    if mode == 'confirm':
                        assert event['code'] == '001234'
                    proc.stdin.write(json.dumps(response) + '\n'); proc.stdin.flush()
                if event['event'] == 'result':
                    proc.wait(timeout=2)
                    return event, events
        raise AssertionError(f'No result: {events}; process status {proc.poll()}')
    finally:
        if proc.poll() is None:
            proc.terminate(); proc.wait(timeout=2)

for mode, answer in [('confirm', ''), ('pin', 'AB-123'), ('passkey', '001234'), ('authorize', '')]:
    result, _ = run(mode, {'accept': True, 'value': answer})
    assert result['ok'] and device.trusted and device.connected, result
    if mode == 'pin': assert device.received[0] == answer
    if mode == 'passkey': assert device.received[0] == 1234
    print(f'PASS {mode}: explicit input, pairing, trust and connection', flush=True)
for response in [{'accept': False}, {'cancel': True}]:
    result, _ = run('confirm', response)
    assert not result['ok'] and not device.trusted, result
print('PASS rejected/cancelled pairing never trusts device', flush=True)
result, _ = run('passkey', {'accept': True, 'value': 'bad'})
assert not result['ok'] and not device.trusted
result, events = run('display')
assert result['ok'] and any(e.get('code') == '001234' for e in events)
result, _ = run('', operation='disconnect'); assert result['ok'] and not device.connected
result, _ = run('', operation='connect'); assert result['ok'] and device.connected
result, _ = run('', operation='forget'); assert result['ok'] and adapter.removed
print('PASS invalid code, keyboard display, reconnect, disconnect and forget', flush=True)
