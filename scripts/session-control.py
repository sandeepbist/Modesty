#!/usr/bin/env python3
"""Start Modesty and manage the optional Caelestia/Hyprland handoff."""
import importlib.util
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'modesty'
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'hypr'
MARKER = STATE/'main-shell'
BACKUP = STATE/'hyprland-handoff.json'
SHELL = str(ROOT/'shell.qml')
SETTINGS_BIND = f'\n-- Modesty settings\ncreate_bind("SUPER + comma", hl.dsp.exec_cmd("quickshell ipc -p {SHELL} call island toggle settings"))\n'
POLKIT = '/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1'

def run(args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True, timeout=12)

def control(command):
    return json.dumps(shlex.join(['python3', str(Path(__file__).resolve()), command]))

def changes():
    return {
        CONFIG/'hyprland/execs.lua': [
            ('hl.exec_cmd("caelestia shell -d")', f'hl.exec_cmd({control("start")})'),
            (f'hl.exec_cmd("{POLKIT}")', f'hl.exec_cmd({control("auth")})'),
        ],
        CONFIG/'hyprland/keybinds.lua': [
            ('hl.dsp.global("caelestia:launcher")', f'hl.dsp.exec_cmd("quickshell ipc -p {SHELL} call island toggle launcher")'),
            ('hl.dispatch(hl.dsp.exec_cmd("caelestia shell -d"))\n    hl.dispatch(hl.dsp.global("caelestia:lock"))', f'hl.dispatch(hl.dsp.exec_cmd({control("restore-lock")}))'),
            ('hl.dsp.exec_cmd("qs -c caelestia kill")', f'hl.dsp.exec_cmd({control("stop")})'),
            ('hl.dsp.exec_cmd("qs -c caelestia kill; sleep .1; caelestia shell -d")', f'hl.dsp.exec_cmd({control("restart")})'),
        ],
    }

def prepare():
    planned = {}
    for path, replacements in changes().items():
        original = path.read_text()
        updated = original
        for old, new in replacements:
            if new in updated: continue
            if updated.count(old) != 1:
                raise RuntimeError(f'Expected shell command changed in {path}; no configuration was written.')
            updated = updated.replace(old, new)
        if path.name == "keybinds.lua" and "call island toggle settings" not in updated:
            updated += SETTINGS_BIND
        planned[path] = (original, updated)
    return planned

def preflight():
    for executable in ['quickshell', 'hyprctl', 'nmcli', 'bluetoothctl', 'brightnessctl', 'nm-connection-editor']:
        if not shutil.which(executable): raise RuntimeError(f'Missing dependency: {executable}')
    for module in ['dbus', 'gi']:
        if importlib.util.find_spec(module) is None: raise RuntimeError(f'Missing Python module: {module}')
    if not (ROOT/'assets/fonts/InterVariable.ttf').is_file(): raise RuntimeError('Bundled Inter font is missing')
    return {} if MARKER.exists() else prepare()

def health():
    result = run(['quickshell', 'ipc', '-p', str(ROOT/'shell.qml'), 'call', 'island', 'health'], check=False)
    try: return json.loads(result.stdout)
    except ValueError: return None

def assert_unlocked():
    state = health()
    if state and state['locked']: raise RuntimeError('Unlock before changing or restarting the shell.')
    session = os.environ.get('XDG_SESSION_ID')
    if session and run(['loginctl', 'show-session', session, '-p', 'LockedHint', '--value'], check=False).stdout.strip() == 'yes':
        raise RuntimeError('Unlock the current session before switching shells.')
    layers = json.loads(run(['hyprctl', 'layers', '-j']).stdout)
    for monitor in layers.values():
        for surfaces in monitor.get('levels', {}).values():
            for surface in surfaces:
                if 'lock' in surface.get('namespace', '').lower():
                    raise RuntimeError('A lock surface is active; unlock before switching shells.')

def stop_modesty():
    if (STATE/'bindings.json').exists():
        run(['python3',str(ROOT/'scripts/bindings.py'),'--clear-live'],check=False)
    instances = run(['quickshell', 'list', '-p', str(ROOT/'shell.qml')], check=False).stdout
    pids = re.findall(r'Process ID: (\d+)', instances)
    run(['quickshell', 'kill', '-p', str(ROOT/'shell.qml')], check=False)
    deadline = time.monotonic() + 5
    while any(Path('/proc', pid).exists() for pid in pids):
        if time.monotonic() >= deadline:
            raise RuntimeError('The previous shell is still exiting; a duplicate was not started.')
        time.sleep(.05)

def validate_shell(root=ROOT, headless=False):
    """A Quickshell load failure can exit zero; require the completion marker too."""
    from desktop_environment import clean_environment
    env = dict(clean_environment(), QT_QPA_PLATFORM='offscreen', MODESTY_PREVIEW='1',
               MODESTY_COMPAT='0')
    result = subprocess.run(['quickshell', '--no-color', '-p', str(root/'typecheck.qml')],
                            env=env, capture_output=True, text=True, timeout=15)
    output = result.stdout + result.stderr
    from compatibility import QtMismatch, qt_mismatch
    if qt_mismatch(output):
        raise QtMismatch('Quickshell reports a Qt mismatch. Finish a full Arch upgrade and rebuild your installed Quickshell package. The running shell was kept.\n'+output[-3000:])
    checked = output
    if headless:
        # Before the first desktop login there may be no PipeWire server. This
        # connection error does not prevent checking QML imports and bindings.
        checked = re.sub(r'^.*ERROR quickshell.service.pipewire.loop: Failed to connect pipewire context\. Errno: \d+\s*$', '', output, flags=re.M)
    if result.returncode or 'VALIDATION COMPLETE' not in output or re.search(r'\bERROR\b|WARN scene:|VALIDATION FAILED|ReferenceError:|TypeError:', checked):
        raise RuntimeError('Modesty validation failed; the running shell was kept.\n' + output[-5000:])
    if os.environ.get('WAYLAND_DISPLAY'):
        env['QT_QPA_PLATFORM'] = 'wayland'
        result = subprocess.run(['quickshell', '--no-color', '-p', str(root/'layercheck.qml')],
                                env=env, capture_output=True, text=True, timeout=15)
        output = result.stdout + result.stderr
        if result.returncode or 'VALIDATION COMPLETE' not in output or re.search(r'\bERROR\b|ReferenceError:|TypeError:', output):
            raise RuntimeError('Modesty layer validation failed; the running shell was kept.\n' + output[-5000:])

def restart():
    assert_unlocked()
    if MARKER.exists():
        validate_shell()
        # Authentication could have started while validation was running.
        assert_unlocked()
        stop_modesty()
    else:
        run(['quickshell', 'kill', '-c', 'caelestia'], check=False)
    start()

def stop_agent():
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit(): continue
        try:
            if (proc/'cmdline').read_bytes().split(b'\0')[0].decode() == POLKIT:
                os.kill(int(proc.name), signal.SIGTERM)
        except (OSError, UnicodeError): pass

def auth():
    if not MARKER.exists():
        subprocess.Popen([POLKIT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

def start():
    if not MARKER.exists():
        run(['caelestia', 'shell', '-d']); return
    from desktop_environment import clean_environment
    env = dict(clean_environment(), MODESTY_COMPAT='1', MODESTY_PREVIEW='0')
    subprocess.run(['quickshell', '-d', '--no-duplicate', '-p', str(ROOT/'shell.qml')], env=env, check=True, timeout=12)
    end = time.monotonic() + 8
    while time.monotonic() < end:
        info = health()
        if info and info['compatibility'] and not info['preview'] and info['policyAgent']:
            return
        time.sleep(.1)
    raise RuntimeError('Modesty did not start with its permission agent. Caelestia can be restored with --restore.')

def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.modesty-tmp')
    temp.write_text(text)
    if path.exists(): temp.chmod(path.stat().st_mode & 0o777)
    temp.replace(path)

def restore():
    if not BACKUP.exists():
        raise RuntimeError('No Caelestia handoff to restore. Restore fresh-install files from modesty-install-backups instead.')
    assert_unlocked()
    # Replace only our commands, retaining unrelated edits made since installation.
    for path, replacements in changes().items():
        if not path.exists(): continue
        text = path.read_text()
        for old, new in replacements: text = text.replace(new, old)
        if path.name == "keybinds.lua": text = text.replace(SETTINGS_BIND, "")
        atomic(path, text)
    MARKER.unlink(missing_ok=True)
    stop_modesty()
    auth(); start()
    run(['hyprctl', 'reload'])
    print('Caelestia restored. Other Hyprland settings were preserved.')

def enable():
    planned = preflight()
    validate_shell()
    assert_unlocked()
    if not BACKUP.exists():
        atomic(BACKUP, json.dumps({str(p): original for p, (original, _) in planned.items()}, indent=2))
    for path, (_, updated) in planned.items(): atomic(path, updated)
    atomic(MARKER, str(ROOT)+'\n')
    try:
        stop_modesty()
        run(['quickshell', 'kill', '-c', 'caelestia'], check=False)
        stop_agent()
        start()
        run(['hyprctl', 'reload'])
    except Exception:
        restore()
        raise
    print('Modesty is now the main shell. Keybinds and gaps are preserved. Use --restore to return to Caelestia.')

if __name__ == '__main__':
    try:
        mode = sys.argv[1] if len(sys.argv)>1 else 'check'
        if mode == 'check':
            for path in preflight(): print(f'Ready: {path}')
            print('App/workspace keybinds, gaps, clipboard, wallpaper helpers and night light remain intact.')
        elif mode == 'enable': enable()
        elif mode == 'restore': restore()
        elif mode == 'auth': auth()
        elif mode == 'start': start()
        elif mode == 'restart':
            restart()
        elif mode == 'stop':
            assert_unlocked()
            if MARKER.exists(): stop_modesty()
            else: run(['quickshell', 'kill', '-c', 'caelestia'], check=False)
        elif mode == 'restore-lock':
            start()
            if MARKER.exists(): run(['quickshell','ipc','-p',str(ROOT/'shell.qml'),'call','island','lock'])
            else: run(['hyprctl','eval','hl.dispatch(hl.dsp.global("caelestia:lock"))'])
        else: raise ValueError('Unknown session-control command')
    except Exception as exc:
        print(str(exc), file=sys.stderr); sys.exit(1)
