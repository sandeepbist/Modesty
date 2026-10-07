#!/usr/bin/env python3
"""Open the normal Flameshot editor with its clipboard daemon available."""
import fcntl
import os
from pathlib import Path
import subprocess
import time
import dbus
from desktop_environment import clean_environment


def main():
    env = clean_environment()
    env['QT_QPA_PLATFORM'] = 'wayland'
    env['QT_QPA_PLATFORMTHEME'] = 'generic'
    runtime = Path(env.get('XDG_RUNTIME_DIR', '/tmp'))
    with (runtime / f'modesty-capture-{os.getuid()}.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        bus = dbus.SessionBus()
        if not bus.name_has_owner('org.flameshot.Flameshot'):
            state = Path(env.get('XDG_STATE_HOME', str(Path.home()/'.local/state'))) / 'modesty'
            state.mkdir(parents=True, exist_ok=True)
            with (state/'flameshot.log').open('a') as log:
                subprocess.Popen(['flameshot'], env=env, stdout=log, stderr=log, start_new_session=True)
            deadline = time.monotonic() + 5
            while not bus.name_has_owner('org.flameshot.Flameshot'):
                if time.monotonic() >= deadline:
                    subprocess.run(['notify-send', 'Screenshot unavailable', 'The Flameshot clipboard service could not start.'], env=env)
                    return
                time.sleep(.05)
        # No final-action flags: retain Copy, Save, Pin and annotation shortcuts.
        subprocess.run(['flameshot', 'gui'], env=env)


if __name__ == '__main__':
    main()
