#!/usr/bin/env python3
"""Check the real companion typing binding through visibility and local resets."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='modesty-companion-') as directory:
    workspace = Path(directory)
    for name in ['components', 'modules', 'assets', 'theme', 'services']:
        (workspace / name).symlink_to(root / name, target_is_directory=True)
    (workspace / 'shell.qml').write_text('''import QtQuick
import Quickshell
import "components" as Components
ShellRoot {
    id:root
    property bool pressed:false
    property bool showPet:false
    property bool animation:true
    property int stage:0
    property double since:Date.now()
    property double deadline:Date.now()+18000
    property int firstFrame:0
    FloatingWindow {
        visible:true;implicitWidth:120;implicitHeight:120
        Components.LumaMark {
            id:pet;portrait:false;size:90
            typing:root.pressed;shown:root.showPet&&ready;animate:root.animation
        }
    }
    function check(ok,label):void {if(!ok)throw new Error(label+" stage="+stage+" gesture="+pet.gesture+" frame="+pet.frame+" typing="+pet.typing+" arriving="+pet.arriving);}
    function next():void {stage++;since=Date.now();}
    Timer {interval:50;running:true;repeat:true;onTriggered:{
        try {
            check(Date.now()<deadline,"Timed out");
            if(stage===0&&pet.ready){root.showPet=true;next();}
            else if(stage===1&&Date.now()-since>1800&&!pet.arriving){root.pressed=true;next();}
            else if(stage===2&&Date.now()-since>300){
                check(pet.typing&&pet.gesture==="writing","External typing binding was lost");
                firstFrame=pet.frame;next();
            } else if(stage===3&&pet.frame!==firstFrame){
                root.pressed=false;next();
            } else if(stage===4&&Date.now()-since>100){
                check(pet.gesture==="idle","Typing did not settle to idle");
                pet.respond();root.pressed=true;next();
            } else if(stage===5&&Date.now()-since>850){
                check(pet.typing&&pet.gesture==="writing","Local response timer reset keyboard typing");
                root.showPet=false;next();
            } else if(stage===6&&Date.now()-since>500){
                check(pet.typing,"Hiding the companion reset its external binding");
                root.showPet=true;next();
            } else if(stage===7&&Date.now()-since>1800&&!pet.arriving){
                check(pet.gesture==="writing","Typing did not resume after arrival");
                root.animation=false;next();
            } else if(stage===8&&Date.now()-since>100){
                check(pet.typing,"Stopping animation reset keyboard typing");
                root.animation=true;root.pressed=false;next();
            } else if(stage===9&&Date.now()-since>100){
                root.pressed=true;next();
            } else if(stage===10&&Date.now()-since>300){
                check(pet.gesture==="writing","Typing did not resume after animation reset");
                console.log("COMPANION CHECK PASS: external typing, frame movement, idle, local response, visibility and animation reset");
                Qt.quit();
            }
        } catch(error) {console.error("COMPANION CHECK FAIL: "+error);Qt.exit(1);}
    }}
}
''')
    environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', MODESTY_PREVIEW='1',
                       QSG_RHI_BACKEND='software', QS_NO_RELOAD_POPUP='1')
    result = subprocess.run(['qs', '--no-color', '-p', str(workspace)],
                            env=environment, capture_output=True, text=True, timeout=25)
    output = result.stdout + result.stderr
    print(output.strip())
    if result.returncode or 'COMPANION CHECK PASS' not in output:
        raise SystemExit(1)
