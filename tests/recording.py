#!/usr/bin/env python3
"""Exercise recorder process ownership and failures without capturing the desktop."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('recording', ROOT / 'scripts/recording.py')
recording = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recording)
# An unreaped child still has a /proc entry and start token, but cannot record.
exited = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(.1)'])
try:
    token = recording.ticks(exited.pid)
    assert token and recording.alive({'pid':exited.pid,'token':token})
    os.waitid(os.P_PID, exited.pid, os.WEXITED | os.WNOWAIT)
    assert not recording.alive({'pid':exited.pid,'token':token})
    assert not recording.alive({'pid':exited.pid,'token':''})
finally:
    exited.wait(timeout=3)
with tempfile.TemporaryDirectory(prefix='modesty-recording-check-') as temporary:
    folder = Path(temporary)
    home = folder / 'home'
    home.mkdir()
    state = folder / 'state/modesty'
    state.mkdir(parents=True)
    binaries = folder / 'bin'
    binaries.mkdir()
    status = state / 'recording.json'
    env = dict(os.environ, HOME=str(home), XDG_STATE_HOME=str(folder / 'state'), PATH=str(binaries))
    processes = []
    def executable(name, source):
        path = binaries / name
        path.write_text('#!'+sys.executable+'\n'+source)
        path.chmod(0o755)
        return path
    executable('hyprctl', 'print(\'[ {"name":"fixture-monitor","focused":true} ]\')\n')
    executable('slurp', 'raise SystemExit(1)\n')
    recorder = executable('gpu-screen-recorder', '''import os, pathlib, signal, sys, time
path=pathlib.Path(sys.argv[sys.argv.index('-o')+1])
path.write_bytes(b'fixture video bytes')
(path.parent/'child.pid').write_text(str(os.getpid()))
signal.signal(signal.SIGUSR2,lambda *_:None)
signal.signal(signal.SIGINT,signal.SIG_IGN if os.getenv('MODESTY_HUNG_RECORDER') else lambda *_:sys.exit(0))
while True:time.sleep(.05)
''')
    (state / 'preferences.json').write_text('{"recordCountdown":0}')
    personal = home / 'personal.txt'
    personal.write_text('keep me')
    def cli(action, *flags, extra=None):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/recording.py'), action, *flags], env=dict(env, **(extra or {})), capture_output=True, text=True, timeout=4)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout
    def wait(phase, timeout=5):
        end = time.monotonic() + timeout
        last = {}
        while time.monotonic() < end:
            try:last = json.loads(status.read_text())
            except (OSError, ValueError):pass
            if last.get('phase') == phase:
                if last.get('pid') and last['pid'] not in processes:processes.append(last['pid'])
                return last
            time.sleep(.03)
        raise AssertionError(('Expected '+phase, last))
    def alive(pid):
        path = Path('/proc') / str(pid) / 'stat'
        try:return path.read_text().rsplit(')',1)[1].split()[0] != 'Z'
        except FileNotFoundError:return False
    try:
        cli('start')
        running = wait('recording')
        cli('start')
        time.sleep(.15)
        assert json.loads(status.read_text())['pid'] == running['pid'], 'Second start replaced recorder'
        cli('pause');wait('paused')
        cli('pause');wait('recording')
        cli('stop');saved = wait('saved')
        assert Path(saved['path']).read_bytes() == b'fixture video bytes'
        assert personal.read_text() == 'keep me'
        # A stale receipt must not signal an unrelated live process with a reused PID.
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])
        try:
            status.write_text(json.dumps({'pid':unrelated.pid,'token':'wrong-start-token','phase':'recording'}))
            cli('stop');cli('pause')
            assert unrelated.poll() is None
            assert json.loads(cli('status'))['phase'] == 'error'
        finally:
            unrelated.terminate();unrelated.wait(timeout=3)
        cli('start', '--region');wait('cancelled')
        recorder.unlink()
        cli('start');failed = wait('error')
        assert 'gpu-screen-recorder' in failed['error']
        executable('gpu-screen-recorder', '''import pathlib, signal, sys, time
path=pathlib.Path(sys.argv[sys.argv.index('-o')+1]);path.write_bytes(b'incomplete fixture')
signal.signal(signal.SIGINT,signal.SIG_IGN)
(path.parent/'child.pid').write_text(str(__import__('os').getpid()))
while True:time.sleep(.05)
''')
        cli('start');hung = wait('recording')
        child = int((Path(hung['path']).parent / 'child.pid').read_text())
        cli('stop');failed = wait('error',timeout=13)
        assert '10 seconds' in failed['error'] and Path(failed['path']).exists()
        assert not alive(child), 'Hung recorder child survived timeout'
        assert Path(saved['path']).read_bytes() == b'fixture video bytes', 'Later failure altered completed recording'
    finally:
        # Only terminate fixture wrappers/children we created in this private test.
        for pid in processes:
            if alive(pid):
                try:os.kill(pid,15)
                except ProcessLookupError:pass
        child_file = home / 'Videos/Recordings/child.pid'
        if child_file.exists():
            pid = int(child_file.read_text())
            if alive(pid):
                try:os.kill(pid,9)
                except ProcessLookupError:pass
print('PASS recorder start/pause/resume/save, stale PID refusal, selection cancel, missing backend and bounded hung-recorder cleanup')
