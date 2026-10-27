#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='modesty-notes-bindings-') as directory:
    temporary = Path(directory)
    executable = temporary / 'hyprctl'
    executable.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
if sys.argv[1:]==['-j','binds']:
    print(os.environ['MOCK_BINDS'])
else:
    with Path(os.environ['MOCK_LOG']).open('a') as log:
        log.write(json.dumps(sys.argv[1:])+'\\n')
    print('ok')
''')
    executable.chmod(0o700)
    environment = dict(os.environ, PATH=str(temporary) + os.pathsep + os.environ['PATH'],
                       MODESTY_PREVIEW='0', XDG_STATE_HOME=str(temporary / 'state'),
                       MOCK_LOG=str(temporary / 'calls.jsonl'))
    state = temporary / 'state/modesty/bindings.json'
    live = [{'modmask': 64, 'key': 'N', 'description': 'Existing user shortcut'}]

    def restore(bindings=None, current=None):
        if state.exists():
            state.unlink()
        if bindings is not None:
            state.parent.mkdir(parents=True, exist_ok=True)
            state.write_text(json.dumps(bindings))
        environment['MOCK_BINDS'] = json.dumps(live if current is None else current)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/bindings.py')],
                                env=environment, capture_output=True, text=True, check=True)
        response = json.loads(result.stdout)
        assert response['ok'], response
        return response

    response = restore()
    assert response['bindings'] == {'notes': 'SUPER + ALT + N', 'dock': 'SUPER + ALT + D'}
    commands = (temporary / 'calls.jsonl').read_text()
    assert 'call island action notes' in commands
    assert 'SUPER + N' not in commands, 'Default replaced existing Super+N'
    response = restore({'reminder': 'SUPER + ALT + T'})
    assert response['bindings'] == {'reminder': 'SUPER + ALT + T', 'notes': 'SUPER + ALT + N', 'dock': 'SUPER + ALT + D'}
    response = restore({'notes': '', 'reminder': 'SUPER + ALT + T'})
    assert response['bindings']['notes'] == '', 'Explicitly disabled default was restored'
    response = restore({'notes': 'SUPER + SHIFT + N'})
    assert response['bindings']['notes'] == 'SUPER + SHIFT + N', 'Custom Notes shortcut was replaced'
    collision = live + [{'modmask': 72, 'key': 'N', 'description': 'Desktop action'}]
    response = restore(current=collision)
    assert response['bindings'] == {'dock': 'SUPER + ALT + D'} and 'already used' in response['defaultError']
    assert json.loads(state.read_text()) == {'dock': 'SUPER + ALT + D'}, 'Colliding Notes default persisted an opt-out'
    response = restore({'reminder': 'SUPER + ALT + T'}, collision)
    assert response['bindings'] == {'reminder': 'SUPER + ALT + T', 'dock': 'SUPER + ALT + D'}
    response = restore({'reminder': 'SUPER + ALT + N'})
    assert response['bindings'] == {'reminder': 'SUPER + ALT + N', 'dock': 'SUPER + ALT + D'}
    assert 'assigned more than once' in response['defaultError']
print('PASS Notes bindings: default, collisions, custom chords, opt-out and preserved Super+N')
