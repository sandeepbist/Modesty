#!/usr/bin/env python3
"""Exercise Gio desktop launch, field codes, terminal wrapping and environment isolation."""
import json,os,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from desktop_environment import clean_environment
assert clean_environment({'ELECTRON_RUN_AS_NODE':'1','LD_LIBRARY_PATH':'/opt/t3code-nightly-bin/usr/lib:/keep/lib','WAYLAND_DISPLAY':'wayland-1'})=={'LD_LIBRARY_PATH':'/keep/lib','WAYLAND_DISPLAY':'wayland-1'}
with tempfile.TemporaryDirectory(prefix='modesty-launch-') as temp:
 p=Path(temp);apps=p/'applications';apps.mkdir();work=p/'working directory';work.mkdir();bin=p/'bin';bin.mkdir()
 worker=p/'worker script.py';worker.write_text('import os,sys,json\nfrom pathlib import Path\nPath(os.environ["RESULT"]).write_text(json.dumps({"args":sys.argv[1:],"cwd":os.getcwd(),"electron":os.environ.get("ELECTRON_RUN_AS_NODE"),"libs":os.environ.get("LD_LIBRARY_PATH")}))\n')
 terminal=bin/'foot';terminal.write_text('#!/usr/bin/python3\nimport os,sys\nassert sys.argv[1]=="-e"\nos.execv(sys.argv[2],sys.argv[2:])\n');terminal.chmod(0o755)
 for is_terminal in (False,True):
  result=p/('terminal.json' if is_terminal else 'gui.json')
  (apps/'modesty-launch-test.desktop').write_text('[Desktop Entry]\nType=Application\nName=Launch test\nExec=/usr/bin/python3 "'+str(worker)+'" "two words" %U\nPath='+str(work)+'\nTerminal='+str(is_terminal).lower()+'\n')
  env=dict(os.environ,XDG_DATA_HOME=str(p),RESULT=str(result),PATH=str(bin)+':'+os.environ['PATH'],ELECTRON_RUN_AS_NODE='1',LD_LIBRARY_PATH='/opt/t3code-nightly-bin/usr/lib')
  response=subprocess.check_output(['python3','scripts/launch-app.py','modesty-launch-test','foot'],env=env,text=True)
  assert json.loads(response)['ok'],response
  for _ in range(50):
   if result.exists():break
   time.sleep(.05)
  data=json.loads(result.read_text());assert data=={'args':['two words'],'cwd':str(work),'electron':None,'libs':None},data
  print('PASS desktop launch', 'terminal' if is_terminal else 'GUI', 'quoted args, field codes, working directory, clean environment')
 bad=subprocess.run(['python3','scripts/launch-app.py','modesty-definitely-missing'],capture_output=True,text=True);assert bad.returncode and not json.loads(bad.stdout)['ok']
 print('PASS missing desktop entry reports error')
