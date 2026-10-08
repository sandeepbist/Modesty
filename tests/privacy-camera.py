#!/usr/bin/env python3
"""Exercise direct camera ownership and observer recovery without camera capture."""
import importlib.util
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
from qml import run

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('camera', ROOT / 'scripts/privacy-camera.py')
camera = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera)
with tempfile.TemporaryDirectory(prefix='modesty-camera-check-') as temporary:
    folder = Path(temporary)
    device = folder / 'video0'
    device.touch()
    observer = subprocess.Popen([sys.executable, '-c',
        'import importlib.util, pathlib; s=importlib.util.spec_from_file_location("camera",'+repr(str(ROOT/'scripts/privacy-camera.py'))+'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.watch(pathlib.Path('+repr(str(folder))+'))'],
        stdout=subprocess.PIPE, text=True)
    def wait(check):
        for _ in range(20):
            if select.select([observer.stdout], [], [], .2)[0]:
                value = json.loads(observer.stdout.readline())
                if check(value): return value
        raise AssertionError('Camera ownership event missing')
    try:
        wait(lambda rows: rows == [])
        with device.open('rb'):
            rows = wait(lambda rows: any(row['pid'] == os.getpid() for row in rows))
            assert all(row['directCamera'] for row in rows)
        wait(lambda rows: rows == [])
    finally:
        observer.terminate()
        observer.wait(timeout=3)

    helper = folder / 'observer.py'
    counter = folder / 'starts'
    helper.write_text('''import json, pathlib, time
counter=pathlib.Path('''+repr(str(counter))+''')
count=int(counter.read_text())+1 if counter.exists() else 1
counter.write_text(str(count))
print(json.dumps([{"pid":count,"label":"Fixture","directCamera":True}]),flush=True)
time.sleep(.25 if count in (1,3) else 30)
''')
    source = (ROOT / 'services/Audio.qml').read_text().replace('pragma Singleton\n', '', 1).replace('Singleton {', 'Scope {', 1)
    # Keep production Process/parser/retry; replace only command and preview input.
    source = source.replace('id: root', 'id: root\n    property bool preview: true', 1).replace('Quickshell.env("MODESTY_PREVIEW") !== "1"', '!root.preview')
    source = source.replace('["python3", Qt.resolvedUrl("../scripts/privacy-camera.py").toString().replace("file://", "")]', json.dumps([sys.executable, str(helper)]))
    source = source.replace('import Quickshell.Services.Pipewire', 'import Quickshell.Services.Pipewire\nimport qs.services')
    (folder / 'AudioProbe.qml').write_text(source)
    run('''import QtQuick
import Quickshell
import qs.services
import "MODULE" as Fixture
ShellRoot {
    Fixture.AudioProbe { id: audio }
    property int phase: 0
    property double since: Date.now()
    property double deadline: Date.now()+19000
    function next() { phase++; since=Date.now(); }
    function check(ok,label) { if(!ok)throw new Error(label+" phase="+phase); }
    Timer { interval:50;running:true;repeat:true;onTriggered:{try {
        check(Date.now()<deadline,"Observer test timed out");
        if(phase===0&&Date.now()-since>200){check(!audio.directCameras.length,"Preview started observer");audio.preview=false;next();}
        else if(phase===1&&audio.directCameras[0]?.pid===1){next();}
        else if(phase===2&&audio.directCameras[0]?.pid===2){Preferences.privacyRadar=false;next();}
        else if(phase===3&&Date.now()-since>250){check(!audio.directCameras.length,"Disabled observer retained camera");Preferences.privacyRadar=true;next();}
        else if(phase===4&&audio.directCameras[0]?.pid===3){next();}
        else if(phase===5&&!audio.directCameras.length){Preferences.privacyRadar=false;next();}
        else if(phase===6&&Date.now()-since>5400){check(!audio.directCameras.length,"Disabled retry started observer");Preferences.privacyRadar=true;next();}
        else if(phase===7&&audio.directCameras[0]?.pid===4){audio.preview=true;next();}
        else if(phase===8&&Date.now()-since>250){check(!audio.directCameras.length,"Preview retained camera");console.log("CAMERA CHECK PASS: ownership events, unexpected exit recovery, disable and preview");Qt.quit();}
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''.replace('MODULE', folder.as_uri()), 'CAMERA CHECK PASS: ownership events, unexpected exit recovery, disable and preview', timeout=23)
    assert counter.read_text() == '4', counter.read_text()
