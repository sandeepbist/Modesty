#!/usr/bin/env python3
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='modesty-dock-bindings-') as d:
    root=Path(d);state=root/'state/modesty/bindings.json';log=root/'calls'
    stub=root/'hyprctl';stub.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
if sys.argv[1:]==['-j','binds']: print(os.environ['DOCK_BINDS'])
else:
 with Path(os.environ['DOCK_LOG']).open('a') as f:f.write(sys.argv[-1]+'\\n')
 print('ok')
''');stub.chmod(0o700)
    env=dict(os.environ,PATH=str(root)+os.pathsep+os.environ['PATH'],XDG_STATE_HOME=str(root/'state'),MODESTY_PREVIEW='0',DOCK_LOG=str(log))
    def restore(saved,binds=(),explicit=None):
        state.parent.mkdir(parents=True,exist_ok=True);state.write_text(json.dumps(saved));env['DOCK_BINDS']=json.dumps(binds)
        r=subprocess.run([sys.executable,str(ROOT/'scripts/bindings.py')]+([] if explicit is None else [json.dumps(explicit)]),env=env,capture_output=True,text=True)
        data=json.loads(r.stdout);assert r.returncode==0 and data['ok'],data
        assert json.loads(state.read_text())==data['bindings'];return data
    defaults={'notes':'SUPER + ALT + N','dock':'SUPER + ALT + D'}
    assert restore({})['bindings']==defaults
    assert restore(defaults)['bindings']==defaults, 'Reload changed saved assignments'
    for chord in ('','SUPER + SHIFT + D'):
        r=restore({'dock':chord});assert r['bindings']==dict(defaults,dock=chord)
    for action,key,other in [('dock','D','notes'),('notes','N','dock')]:
        collision=[{'modmask':72,'key':key,'description':'User desktop shortcut'}]
        r=restore({},collision);assert r['bindings']=={other:defaults[other]} and 'already used' in r['defaultError']
        assert action not in json.loads(state.read_text()),'Collision persisted an opt-out'
        assert restore(r['bindings'])['bindings']==defaults,'Missing default did not retry'
    r=restore({'reminder':'SUPER + ALT + D'});assert r['bindings']=={'notes':defaults['notes'],'reminder':'SUPER + ALT + D'} and 'assigned more than once' in r['defaultError']
    assert restore({},explicit={'dock':''})['bindings']=={'dock':''},'Explicit write installed missing defaults'
    assert 'call island action dock' in log.read_text()
print('DOCK BINDINGS PASS')
