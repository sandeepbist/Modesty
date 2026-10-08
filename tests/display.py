#!/usr/bin/env python3
"""Exercise display rollback on approval, EOF, timeout and process interruption."""
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='modesty-display-check-') as temporary:
    folder = Path(temporary)
    calls = folder / 'calls'
    helper = folder / 'hyprctl'
    helper.write_text('#!'+sys.executable+'''\nimport json, os, pathlib, sys
if sys.argv[1:]==['-j','monitors']:
    print(json.dumps([dict(name='fixture',width=1920,height=1080,refreshRate=60,scale=1,x=0,y=0,availableModes=['1920x1080@60.00Hz','1280x720@60.00Hz'])]))
else:
    with pathlib.Path(os.environ['MODESTY_DISPLAY_CALLS']).open('a') as stream:stream.write(sys.argv[-1]+'\\n')
    print('error: fixture apply failed' if os.getenv('MODESTY_DISPLAY_FAILURE') and '1280x720' in sys.argv[-1] else 'ok')
''')
    helper.chmod(0o755)
    env = dict(os.environ, PATH=str(folder), MODESTY_DISPLAY_CALLS=str(calls))
    env.pop('MODESTY_PREVIEW', None)
    def start(mode='1280x720@60.00', fail=False):
        calls.unlink(missing_ok=True)
        return subprocess.Popen([sys.executable, str(ROOT / 'scripts/display.py'), 'change',json.dumps(dict(name='fixture',mode=mode,scale=1))],env=dict(env, **({'MODESTY_DISPLAY_FAILURE':'1'} if fail else {})),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    def pending(process):
        assert select.select([process.stdout], [], [], 4)[0], 'Display guard did not start'
        assert json.loads(process.stdout.readline()).get('pending'), 'Display change did not ask for approval'
    def reverted():
        commands = calls.read_text().splitlines()
        assert len(commands)==2 and '1280x720' in commands[0] and '1920x1080' in commands[1], commands
    for answer in ('keep\n', 'revert\n', ''):
        process = start()
        try:
            pending(process)
            output, error = process.communicate(answer, timeout=4)
            assert process.returncode==0 and json.loads(output)['kept']==(answer=='keep\n'), output+error
            if answer=='keep\n': assert len(calls.read_text().splitlines())==1
            else:reverted()
        finally:
            if process.poll() is None:process.kill();process.wait()
    process = start()
    try:
        pending(process)
        process.terminate();output,error=process.communicate(timeout=4)
        assert process.returncode!=0 and 'Shell closed' in output,output+error
        reverted()
    finally:
        if process.poll() is None:process.kill();process.wait()
    process = start()
    try:
        pending(process)
        # Keep stdin open: the independent deadline must restore without the UI.
        assert process.wait(timeout=18)==0
        assert not json.loads(process.stdout.read())['kept']
        reverted()
    finally:
        if process.poll() is None:process.kill();process.wait()
    process = start(mode='1234x567@60.00')
    output,error=process.communicate(timeout=4)
    assert process.returncode!=0 and not calls.exists(),output+error
    process = start(fail=True)
    output,error=process.communicate(timeout=4)
    assert process.returncode!=0 and 'fixture apply failed' in output,output+error
    reverted()
print('PASS display approval, rejection, EOF, timeout, interruption, invalid mode and failed-apply rollback')
