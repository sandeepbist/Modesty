#!/usr/bin/env python3
"""Live pointer/drag acceptance for this 1920×1080 desktop. Changes are restored.
Run only with explicit live-test authorization: python3 tests/native-input.py --live
Requires wayland-scanner, a C compiler, Wayland development files, wtype, grim.
"""
import sys
if '--live' not in sys.argv: raise SystemExit('Pass --live to click and drag on the current desktop.')
import subprocess,time,json
from pathlib import Path
binary=subprocess.check_output(['bash','tests/native-input/build.sh'],text=True).strip()
Path('/tmp/modesty-input-review').mkdir(exist_ok=True)
p=subprocess.Popen([binary],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
def send(s):p.stdin.write(s+'\n');p.stdin.flush();assert p.stdout.readline().strip()=='ok'
def click(x,y):send(f'move {x} {y}');time.sleep(.08);send('down');send('up');time.sleep(.65)
base=['quickshell','ipc','-p',str(Path(__file__).resolve().parents[1]/'shell.qml'),'call','island']
def g():return json.loads(subprocess.check_output(base+['geometry']))
assert not json.loads(subprocess.check_output(base+['health']))['locked'], 'Unlock before live input testing'
backlight=Path('/sys/class/backlight/amdgpu_bl1/brightness');old=int(backlight.read_text()); maximum=65535
volume=float(subprocess.check_output(['wpctl','get-volume','@DEFAULT_AUDIO_SINK@'],text=True).split()[1])
try:
 for x,panel in [(884,'media'),(960,'clock'),(1035,'quicksettings')]:
  click(x,24);assert g()['menu']==panel,(panel,g()['menu'])
  click(700,760);assert g()['menu']=='none',g()['menu'];print('PASS pointer open/outside close',panel,flush=True)
 click(1035,24);click(1100,40);assert g()['menu']=='wifi',g()['menu'];click(1063,88);assert g()['menu']=='quicksettings',g()['menu']
 click(1288,337)
 w=json.loads(subprocess.check_output(['hyprctl','-j','activewindow']));assert w.get('title')=='Modesty Settings',(g()['menu'],w.get('title'));assert g()['menu']=='none'
 click(590,260);subprocess.run(['wtype','Motion']);time.sleep(.3)
 subprocess.run(['grim','-g','505,215 910x695','/tmp/modesty-input-review/settings-input.png'])
 subprocess.run(['wtype','-k','Escape']);time.sleep(.4);print('PASS Wi-Fi back → Settings → typed into Settings',flush=True)
 click(1035,24)
 for kind,y,start,end,read in [('brightness',148,.80,.94,lambda:int(backlight.read_text())),('volume',201,volume,min(.68,volume+.1),lambda:float(subprocess.check_output(['wpctl','get-volume','@DEFAULT_AUDIO_SINK@'],text=True).split()[1]))]:
  values=[];send(f'move {int(1037+336*start)} {y}');send('down')
  for i in range(31):
   send(f'move {int(1037+336*(start+(end-start)*i/30))} {y}');time.sleep(.045);values.append(read())
  # All samples above are taken before releasing the pointer.
  send('up');time.sleep(.4);print(kind,'distinct values during drag',len(set(values)),values,flush=True);assert len(set(values))>=5,(kind,values)
  Path('/tmp/modesty-input-review/'+kind+'.json').write_text(json.dumps(values))
 click(700,760);assert g()['menu']=='none'
finally:
 subprocess.run(base+['close']);send('up');p.stdin.close();p.wait()
 subprocess.run(['python3','scripts/brightness-stream.py','amdgpu_bl1'],input=json.dumps({'sequence':1,'value':old})+'\n',text=True,check=True)
 subprocess.run(['wpctl','set-volume','@DEFAULT_AUDIO_SINK@',str(volume)],check=True)
