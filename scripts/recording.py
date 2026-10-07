#!/usr/bin/env python3
"""Own one recorder process; finalize only that process and retain session status."""
import fcntl,json,os,re,signal,subprocess,sys,time
from datetime import datetime
from pathlib import Path
STATE=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'modesty'
STATUS=STATE/'recording.json'

def write(data):
    tmp=STATUS.with_suffix('.tmp');tmp.write_text(json.dumps(data));tmp.replace(STATUS)
def read():
    try:return json.loads(STATUS.read_text())
    except (OSError,ValueError):return {}
def ticks(pid):
    try:return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
    except (OSError,IndexError):return ''
def alive(data):return bool(data.get('pid') and ticks(data['pid'])==data.get('token'))
def control(action):
    data=read()
    if alive(data):
        try:os.kill(data['pid'],signal.SIGUSR2 if action=='pause' else signal.SIGTERM)
        except ProcessLookupError:pass
def run(region,sound):
    STATE.mkdir(parents=True,exist_ok=True)
    lock=(STATE/'recording.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:return
    try:prefs=json.loads((STATE/'preferences.json').read_text())
    except (OSError,ValueError):prefs={}
    data={'pid':os.getpid(),'token':ticks(os.getpid()),'phase':'preparing','sound':sound,'region':region,'started':0,'elapsed':0,'path':'','error':''}
    child=None;selector=None;cancelled=False;paused=False;paused_at=0;paused_total=0
    def stop(*_):
        nonlocal cancelled
        cancelled=True
        if child and child.poll() is None:child.send_signal(signal.SIGINT)
        if selector and selector.poll() is None:selector.terminate()
    def pause(*_):
        nonlocal paused,paused_at,paused_total
        if child and child.poll() is None and data['phase'] in ('recording','paused'):
            child.send_signal(signal.SIGUSR2)
            paused=not paused
            if paused:paused_at=time.monotonic()
            else:paused_total+=time.monotonic()-paused_at
            data['phase']='paused' if paused else 'recording';write(data)
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGUSR2,pause)
    write(data)
    try:
        # Allow the panel to finish closing before any capture/selection begins.
        time.sleep(.4)
        if cancelled:return
        if region:
            data['phase']='selecting';write(data);time.sleep(.15)
            if cancelled:return
            selector=subprocess.Popen(['slurp','-f','%wx%h+%x+%y'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            output,_=selector.communicate(timeout=120)
            if selector.returncode or cancelled:data['phase']='cancelled';return
            geometry=output.strip()
            if not re.fullmatch(r'\d+x\d+\+-?\d+\+-?\d+',geometry):raise ValueError('Invalid region selection')
            args=['-w','region','-region',geometry]
        else:
            monitors=json.loads(subprocess.check_output(['hyprctl','-j','monitors'],text=True,timeout=3))
            monitor=next((m for m in monitors if m.get('focused')),monitors[0])
            args=['-w',monitor['name']]
        delay=max(0,min(5,int(prefs.get('recordCountdown',3))))
        for remaining in range(delay,0,-1):
            if cancelled:data['phase']='cancelled';return
            data.update(phase='countdown',remaining=remaining);write(data);time.sleep(1)
        if cancelled:return
        folder=Path.home()/'Videos'/'Recordings';folder.mkdir(parents=True,exist_ok=True)
        path=folder/(datetime.now().strftime('Recording %Y-%m-%d %H-%M-%S')+f'-{os.getpid()}.mp4')
        args+=['-f',str(60 if prefs.get('recordFps',60)==60 else 30),'-k','h264','-cursor','yes' if prefs.get('recordCursor',True) else 'no']
        if sound:args+=['-a','default_output']
        log=(STATE/'recording.log').open('w')
        child=subprocess.Popen(['gpu-screen-recorder',*args,'-o',str(path)],stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        start=time.monotonic();data.update(phase='recording',started=time.time(),path=str(path));write(data)
        while child.poll() is None:
            now=paused_at if paused else time.monotonic()
            data['elapsed']=int(now-start-paused_total)
            if cancelled:data['phase']='saving'
            write(data);time.sleep(.5)
        log.close()
        if child.returncode not in (0,130,-signal.SIGINT):raise RuntimeError('Recording failed. See ~/.local/state/modesty/recording.log')
        if not path.exists() or path.stat().st_size==0:raise RuntimeError('The recorder did not produce a video.')
        data['phase']='saved'
    except Exception as error:
        data.update(phase='error',error=str(error))
        if child and child.poll() is None:
            child.send_signal(signal.SIGINT)
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill();child.wait()
    finally:
        if selector and selector.poll() is None:selector.terminate()
        if data['phase'] in ('preparing','selecting','countdown'):data['phase']='cancelled'
        write(data)

if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'toggle'
    if action=='folder':
        folder=Path.home()/'Videos'/'Recordings';folder.mkdir(parents=True,exist_ok=True)
        subprocess.Popen(['xdg-open',str(folder)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    elif action=='run':run('--region' in sys.argv,'--sound' in sys.argv)
    elif action in ('stop','pause'):control(action)
    elif action=='status':
        STATE.mkdir(parents=True,exist_ok=True)
        if not STATUS.exists():write({'phase':'idle'})
        data=read()
        if data.get('phase') in ('preparing','selecting','countdown','recording','paused','saving') and not alive(data):data.update(phase='error',error='The recorder is no longer running.');write(data)
        print(json.dumps(data))
    elif action in ('start','toggle'):
        if alive(read()):
            if action=='toggle':control('stop')
        else:
            STATE.mkdir(parents=True,exist_ok=True)
            subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'run',*sys.argv[2:]],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
