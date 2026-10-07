#!/usr/bin/env python3
"""Live visual regression; hover coordinates follow current geometry.
Capture regions assume a 1920×1080 desktop.
Explicitly opt in: python3 tests/live-review.py --live
Moves the desktop pointer and opens panels; never authenticates or changes hardware.
Evidence is saved under /tmp/modesty-review. Requires grim and wf-recorder.
"""
import sys
if "--live" not in sys.argv:
    raise SystemExit("Pass --live to run on the current desktop; see this file's docstring.")
import json,subprocess,time,signal
from pathlib import Path
out=Path('/tmp/modesty-review'); out.mkdir(exist_ok=True)
base=['quickshell','ipc','-p',str(Path(__file__).resolve().parents[1]/'shell.qml'),'call','island']
def call(*args):return subprocess.check_output(base+list(args),text=True)
def geo():return json.loads(call('geometry'))
def move(x,y):subprocess.run(['hyprctl','eval',f'hl.dispatch(hl.dsp.cursor.move({{x={int(x)},y={int(y)}}}))'],capture_output=True)
orig=subprocess.check_output(['hyprctl','cursorpos'],text=True).strip().split(', ')
assert not json.loads(call('health'))['locked'], 'Unlock before running the live review'
records={}
try:
 call('close');move(700,600);time.sleep(.6)
 for i,name in enumerate(['media','clock','controls']):
  g=geo();s=g['stages'][i]
  if not s['visible']:continue
  monitor=json.loads(subprocess.check_output(['hyprctl','-j','monitors'],text=True))[0]
  scale=g['uiScale'];x=monitor['x']+monitor['width']/2+(s['x']+s['width']/2-g['width']/2)*scale
  move(x,monitor['y']+g['topMargin']+5*scale);time.sleep(.5)
  frames=[]
  for _ in range(15):
   g=geo();frames.append(g);assert g['panel']=='idle';assert g['stages'][i]['restingHovered'],(name,subprocess.check_output(['hyprctl','cursorpos'],text=True));time.sleep(.035)
  records['hover-'+name]=frames
  subprocess.run(['grim','-g','830,0 340x80',str(out/('hover-'+name+'.png'))])
  move(700,600);time.sleep(.3)
  print('PASS stable top-edge hover',name,flush=True)
 rec=subprocess.Popen(['wf-recorder','-g','500,0 1050x570','-f',str(out/'transitions.mp4'),'-y'],stdout=open(out/'recorder.log','w'),stderr=subprocess.STDOUT)
 time.sleep(.3)
 try:
  for name in ['media','clock','quicksettings','wifi','bluetooth','display','sound','calendar','wallpapers','themes','launcher','power']:
   call('open',name);time.sleep(.6)
   g=geo();assert g['panel']==name,(name,g['panel'])
   panes=[p for s in g['stages'] for p in s['entries'] if p['selected']];assert len(panes)==1 and panes[0]['loaded'] and panes[0]['opacity']>.99,(name,panes)
   call('close');samples=[];end=time.monotonic()+.55
   while time.monotonic()<end:
    g=geo();samples.append(g)
    for s in g['stages']:
     assert s['restHeight']==33 and s['restWidth'] in [33,90],s
     assert s['height']>=32.99,s
     for p in s['entries']:
      if p['opacity']>.01 and p['name'] not in ['context','toast']:assert p['width']>150 and p['height']>60,(name,p)
    if name=='clock':assert g['clockOpacity']>.99,g['clockOpacity']
    time.sleep(.012)
   records[name]=samples;print('PASS close geometry',name,flush=True)
 finally:
  rec.send_signal(signal.SIGINT);rec.wait(timeout=6)
 for name in ['media','wifi','clock','quicksettings','calendar','media']:
  call('open',name);time.sleep(.055)
 call('close');time.sleep(.7);g=geo();assert all(abs(s['width']-s['targetWidth'])<.05 and abs(s['height']-s['targetHeight'])<.05 for s in g['stages'])
 print('PASS interrupted transitions settle',flush=True)
finally:
 call('close');move(float(orig[0]),float(orig[1]));(out/'native-motion.json').write_text(json.dumps(records))
