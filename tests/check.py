#!/usr/bin/env python3
"""Run offline regression checks; native input tests require explicit --live."""
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
commands = [
    ['node', 'tests/layout.cjs'], ['node', 'tests/search.cjs'],
    *[[sys.executable, f'tests/{name}.py'] for name in
      ('release', 'install', 'installation', 'updates', 'structure', 'backend', 'appearance', 'session-control', 'night-light',
       'launcher', 'voice', 'luma', 'luma-system', 't3-status', 'levels', 'conversation', 'calculator', 'control-tiles', 'companion')],
    *[['dbus-run-session', '--', sys.executable, f'tests/{name}.py'] for name in
      ('bluetooth', 'notifications', 'session-events')],
]
for command in commands:
    print('CHECK ' + ' '.join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True, timeout=60)
spec = importlib.util.spec_from_file_location('session_control', ROOT / 'scripts/session-control.py')
session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session)
session.validate_shell()
print('PASS all offline checks and QML validation')
