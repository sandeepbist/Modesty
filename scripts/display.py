#!/usr/bin/env python3
"""Display changes use a separate rollback guard, including when the shell exits."""
import json, os, re, select, signal, subprocess, sys, time

def run(args):
    result=subprocess.run(args,capture_output=True,text=True,timeout=8)
    if result.returncode: raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()
def monitors(): return json.loads(run(['hyprctl','-j','monitors']))
def rule(m,mode,scale):
    if not re.fullmatch(r'[A-Za-z0-9_.:-]+',m['name']): raise ValueError('Invalid output name')
    if not re.fullmatch(r'\d+x\d+@\d+(?:\.\d+)?',mode): raise ValueError('Invalid display mode')
    if not 0.5<=scale<=3: raise ValueError('Invalid scale')
    return 'hl.monitor({output='+json.dumps(m['name'])+',mode='+json.dumps(mode)+',position='+json.dumps(str(m['x'])+'x'+str(m['y']))+',scale='+str(scale)+',transform='+str(m.get('transform',0))+'})'
def change(data):
    m=next(m for m in monitors() if m['name']==data['name'])
    mode=data.get('mode') or f"{m['width']}x{m['height']}@{m['refreshRate']:.2f}"
    mode=mode.removesuffix('Hz');scale=float(data.get('scale',m['scale']))
    if mode+'Hz' not in m['availableModes']: raise ValueError('This display does not advertise that mode')
    w,h=map(int,mode.split('@')[0].split('x'))
    if any(abs(n/scale-round(n/scale))>0.001 for n in (w,h)): raise ValueError('Choose a scale that gives whole logical pixels')
    old=rule(m,f"{m['width']}x{m['height']}@{m['refreshRate']:.2f}",m['scale'])
    keep=False
    def interrupt(*_): raise InterruptedError('Shell closed')
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
    try:
        result=run(['hyprctl','eval',rule(m,mode,scale)])
        if 'error' in result.lower(): raise RuntimeError(result)
        print(json.dumps({'pending':True}),flush=True)
        if select.select([sys.stdin],[],[],15)[0]: keep=sys.stdin.readline().strip()=='keep'
    finally:
        if not keep: run(['hyprctl','eval',old])
    return {'ok':True,'kept':keep}
def night(enabled,temp):
    if enabled:
        try: run(['hyprctl','hyprsunset','temperature',str(temp)])
        except RuntimeError:
            subprocess.Popen(['hyprsunset','--temperature',str(temp)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            for _ in range(20):
                time.sleep(.1)
                try: run(['hyprctl','hyprsunset','temperature',str(temp)]);break
                except RuntimeError: pass
            else: raise RuntimeError('Night Light could not start')
    else: run(['hyprctl','hyprsunset','identity'])
    return {'ok':True,'nightLight':enabled,'temperature':temp}
if __name__=='__main__':
    try:
        action=sys.argv[1];data=json.loads(sys.argv[2]) if len(sys.argv)>2 else {}
        if os.environ.get('MODESTY_PREVIEW')=='1' and action!='snapshot': raise ValueError('System changes are disabled in preview')
        result={'monitors':monitors()} if action=='snapshot' else change(data) if action=='change' else night(bool(data['enabled']),max(2000,min(6500,int(data['temperature'])))) if action=='night' else None
        if result is None: raise ValueError('Unknown display action')
        print(json.dumps(result),flush=True)
    except Exception as e: print(json.dumps({'ok':False,'error':str(e)}),flush=True);sys.exit(1)
