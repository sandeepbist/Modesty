#!/usr/bin/env python3
"""Capture native numeric transitions and check countdown and reduced-motion behavior."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = args.source.resolve()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
source = r'''import QtQuick
import Quickshell
import qs.services
import qs.components
import qs.theme
ShellRoot {
 id:probe
 property int phase:0
 property bool grabbing:false
 property int shot:0
 property var samples:[]
 FloatingWindow {visible:true;implicitWidth:360;implicitHeight:120
  Rectangle {id:canvas;anchors.fill:parent;color:"#121214"
   RollingText {id:up;x:40;y:12;width:120;height:35;slideDigits:true;text:"00:15";font.family:"Inter Variable";font.pixelSize:14;font.features:({tnum:1})}
   RollingText {id:down;x:200;y:12;width:120;height:35;slideDigits:true;text:"00:15";font:up.font}
   PanelText {x:40;y:75;text:"Increasing";font.pixelSize:12}
   PanelText {x:200;y:75;text:"Countdown";font.pixelSize:12}
  }
 }
 function walk(item){let a=[item];for(const c of item.children||[])a=a.concat(walk(c));return a;}
 function read(item){return walk(item).filter(c=>c.shown!==undefined).map(c=>({index:c.index,value:c.value,shown:c.shown,outgoing:c.outgoing,progress:c.progress,layer:c.layer.enabled,labels:walk(c).filter(d=>d instanceof PanelText&&d.visible).map(d=>({text:d.text,y:d.y}))}));}
 Component.onCompleted:{Quickshell.watchFiles=false;Preferences.motion="gentle";Preferences.motionSpeed=1;Preferences.fontFamily="Inter Variable";Theme.setPalette("midnight");if(down.countsDown!==undefined)down.countsDown=true;}
 Timer {interval:700;repeat:true;running:phase<5;onTriggered:{
  phase++;
  if(phase===1){up.text="00:16";down.text="00:14";}
  if(phase===2){up.text="00:19";down.text="00:10";}
  if(phase===3){up.text="00:20";down.text="00:09";}
  if(phase===4){Preferences.motion="instant";up.text="00:21";down.text="00:08";}
 }}
 Timer {interval:17;running:true;repeat:true;onTriggered:{
  if(grabbing)return;grabbing=true;
  const row={file:String(shot++).padStart(3,"0")+".png",phase,ms:Date.now(),up:read(up),down:read(down)};
  canvas.grabToImage(r=>{r.saveToFile("OUTPUT/"+row.file);probe.samples.push(row);grabbing=false;if(phase===5){console.log("NUMERIC_RESULT "+JSON.stringify(probe.samples));Qt.quit();}});
 }}
}'''.replace('OUTPUT', str(out))
with tempfile.TemporaryDirectory(prefix='modesty-numeric-') as temporary:
    w = Path(temporary)
    for name in ('components', 'modules', 'theme', 'assets', 'scripts'):
        (w/name).symlink_to(root/name, target_is_directory=True)
    shutil.copytree(root/'services', w/'services')
    (w/'shell.qml').write_text(source)
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='rhi',
               QSG_RHI_BACKEND='opengl', QSG_INFO='1', MODESTY_PREVIEW='1',
               QS_NO_RELOAD_POPUP='1', QT_NO_XDG_DESKTOP_PORTAL='1',
               XDG_CONFIG_HOME=str(w/'config'), XDG_STATE_HOME=str(w/'state'),
               XDG_CACHE_HOME=str(w/'cache'), XDG_RUNTIME_DIR=str(w/'runtime'),
               PIPEWIRE_REMOTE='modesty-numeric-isolated')
    (w/'runtime').mkdir(mode=0o700)
    result = subprocess.run(['dbus-run-session', '--', 'qs', '--no-color', '-p', str(w)], env=env,
                            capture_output=True, text=True, timeout=20)
log = result.stdout+result.stderr
(out/'run.log').write_text(log)
match = re.search(r'NUMERIC_RESULT (\[[^\n]+\])', log)
assert result.returncode == 0 and match and 'OpenGL' in log, log[-4000:]
assert not re.search(r'\bERROR\b|ReferenceError|TypeError|Binding loop|Unable to assign|Failed to', log), log[-4000:]
rows = json.loads(match[1])
(out/'manifest.json').write_text(json.dumps(rows, indent=2))
moving = [row for row in rows if row['phase'] in (1, 3) and any(0<d['progress']<1 for d in row['down'])]
assert len(moving)>4, 'No captured countdown movement'
for row in moving:
    for digit in row['down']:
        if digit['outgoing'] and 0<digit['progress']<1:
            assert digit['labels'][0]['y']>0 and digit['labels'][1]['y']<0, f'Countdown rolls upward: {digit}'
    for digit in row['up']:
        if digit['outgoing'] and 0<digit['progress']<1:
            assert digit['labels'][0]['y']<0 and digit['labels'][1]['y']>0, f'Increasing number rolls downward: {digit}'
assert all(len(d['labels'])==1 and d['labels'][0]['text']==d['value'] and abs(d['labels'][0]['y'])<.01 for r in rows if r['phase']==5 for d in r['up']+r['down']), 'Reduced Motion left displaced or outgoing text'
assert ''.join(d['shown'] for d in rows[-1]['down'])=='00:08', 'Final countdown differs from source'
summary = dict(captures=len(rows), countdownMovingFrames=len(moving), reducedMotionSettled=True,
               finalCountdown='00:08', backend='OpenGL')
(out/'summary.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary))
print('NUMERIC MOTION PASS')
