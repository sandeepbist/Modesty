#!/usr/bin/env python3
"""Inspect, change or launch the receipt-owned optional Modesty Kitty profile."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import installation
from desktop_environment import clean_environment

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME') or HOME / '.config')
STATE = Path(os.environ.get('XDG_STATE_HOME') or HOME / '.local/state')
PROFILE = CONFIG / 'kitty/modesty.conf'
EFFECTS = CONFIG / 'kitty/modesty-effects.conf'
OPTIONAL = (PROFILE, EFFECTS, CONFIG / 'kitty/modesty-generated.conf', CONFIG / 'fish/functions/modesty-terminal.fish')


def validate_profile(profile, expected=None):
    executable = shutil.which('kitty')
    if not executable:
        raise RuntimeError('Kitty is not installed.')
    code = (
        'import json; from kitty.config import load_config; bad=[]; '
        f'p=load_config({str(profile)!r},accumulate_bad_lines=bad); '
        'assert not bad,bad; '
        'assert hasattr(p,"cursor_trail"),"Native cursor trail is unavailable"; '
        'assert p.cursor_trail in (0,1),"Unsupported cursor trail value"; '
        'print("MODESTY_TRAIL="+json.dumps(p.cursor_trail))'
    )
    result = subprocess.run([executable, '+runpy', code], capture_output=True, text=True,
                            timeout=10, env=clean_environment())
    match = re.search(r'^MODESTY_TRAIL=([01])$', result.stdout, re.M)
    if result.returncode or not match:
        raise RuntimeError('Kitty cannot parse the native cursor trail profile.')
    value = int(match[1])
    if expected is not None and value != expected:
        raise RuntimeError('Kitty did not apply the requested cursor trail value.')
    return value


def require_mutation():
    if os.environ.get('MODESTY_PREVIEW') == '1':
        raise RuntimeError('Preview session actions are disabled.')
    if any(os.environ.get(key) for key in ('WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE', 'XDG_SESSION_ID')):
        spec = importlib.util.spec_from_file_location('terminal_session', ROOT / 'scripts/session-control.py')
        session = importlib.util.module_from_spec(spec); spec.loader.exec_module(session)
        session.assert_unlocked()


def managed():
    for path in (*OPTIONAL, STATE / 'modesty-install/receipt.json', STATE / 'modesty-install/operation.lock', STATE / 'modesty-install/transaction.json'):
        installation.safe_target(path, HOME, STATE)
        if path.is_symlink():
            raise RuntimeError('Optional terminal paths must be regular files.')
    if (STATE / 'modesty-install/transaction.json').exists():
        raise RuntimeError('Recover the interrupted installation before using terminal effects.')
    data = installation.receipt(ROOT, HOME, STATE)
    if not any(path.exists() for path in OPTIONAL):
        return 'absent'
    if any(not path.is_file() or str(path) not in data['files'] for path in OPTIONAL):
        return 'unmanaged'
    return 'ready'


def status():
    try:
        availability = managed()
        if availability != 'ready':
            return dict(availability=availability, enabled=False, message='Install the optional profile with approved setup.')
        if not shutil.which('kitty'):
            return dict(availability='missing-kitty', enabled=False, message='Kitty is missing. Run optional setup to repair it.')
        if not shutil.which('fish'):
            return dict(availability='error', enabled=False, message='Fish is required by this profile. Run the desktop installer to review required package setup.')
        try:
            enabled = bool(validate_profile(PROFILE))
        except (RuntimeError, subprocess.SubprocessError) as error:
            return dict(availability='unsupported', enabled=False, message=str(error))
        return dict(availability='ready', enabled=enabled, message='New Modesty Kitty windows use this setting.')
    except (RuntimeError, ValueError, OSError) as error:
        return dict(availability='error', enabled=False, message=str(error))


def set_trail(enabled):
    require_mutation()
    installation.safe_target(STATE / 'modesty-install/operation.lock', HOME, STATE)
    if (STATE / 'modesty-install/operation.lock').is_symlink():
        raise RuntimeError('Optional terminal lock must be a regular file.')
    with installation.locked(STATE):
        current = status()
        if current['availability'] != 'ready':
            raise RuntimeError(current['message'])
        if current['enabled'] == enabled:
            return current
        content = EFFECTS.read_text()
        if len(re.findall(r'^cursor_trail[ \t]+[01][ \t]*$', content, re.M)) != 1:
            raise RuntimeError('The effects include must contain one cursor_trail value of 0 or 1.')
        candidate = re.sub(r'^cursor_trail[ \t]+[01][ \t]*$', 'cursor_trail ' + str(int(enabled)), content, flags=re.M)
        with tempfile.TemporaryDirectory(prefix='modesty-trail-') as folder:
            directory = Path(folder)
            for path in OPTIONAL[:3]:
                (directory / path.name).write_bytes(candidate.encode() if path == EFFECTS else path.read_bytes())
            validate_profile(directory / PROFILE.name, expected=int(enabled))
        installation.transaction([(EFFECTS, candidate.encode(), EFFECTS.stat().st_mode & 0o777)], ROOT, HOME, STATE)
        return dict(availability='ready', enabled=enabled, message='New Modesty Kitty windows use this setting.')


def launch():
    require_mutation()
    current = status()
    if current['availability'] != 'ready':
        raise RuntimeError(current['message'])
    subprocess.Popen([shutil.which('kitty'), '--config', str(PROFILE)], env=clean_environment(),
                     start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--status', action='store_true')
    action.add_argument('--set-trail', choices=('on', 'off'))
    action.add_argument('--open', action='store_true')
    args = parser.parse_args()
    try:
        result = set_trail(args.set_trail == 'on') if args.set_trail else launch() if args.open else status()
        print(json.dumps(result))
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps(dict(availability='error', enabled=False, message=str(error))))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
