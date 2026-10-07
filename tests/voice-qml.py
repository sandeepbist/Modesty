#!/usr/bin/env python3
"""Exercise the real Voice.qml lifecycle in an isolated shell using recorded audio.

Pass a 16 kHz WAV. Singletons are test doubles; transcripts never reach Luma.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('audio', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='modesty-voice-qml-') as directory:
    workspace = Path(directory)
    services = workspace / 'services'; services.mkdir()
    source = (root / 'services/Voice.qml').read_text()
    source = source.replace('Qt.resolvedUrl("../scripts/luma-voice.py").toString().replace("file://", "")',
                            '"' + str(root / 'scripts/luma-voice.py') + '"')
    source = source.replace('command:["python3",root.backend]',
                            'command:["python3",root.backend,"--audio",' + '"' + str(args.audio.resolve()) + '"]')
    source = source.replace('interval:180000', 'interval:300')
    (services / 'Voice.qml').write_text(source)
    stubs = {
        'Preferences': 'property bool preview:false; property bool lumaVoice:true; property bool lumaVoiceWarm:false',
        'Session': 'property bool locked:false; function isLocked():bool {return locked;}',
        'CanvasState': 'property bool opened:false; function show():void {opened=true;}',
        'Luma': 'property bool busy:false',
        'Recorder': 'property bool selecting:false',
    }
    for name, body in stubs.items():
        (services / (name + '.qml')).write_text('pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {' + body + '}\n')
    (services / 'qmldir').write_text('\n'.join('singleton ' + name + ' 1.0 ' + name + '.qml'
                                               for name in ['Voice', *stubs]) + '\n')
    (workspace / 'audit.qml').write_text('''import QtQuick
import Quickshell
import "services" as Audit
ShellRoot {
    id:root
    property int stage:0
    property int submitted:0
    property int partials:0
    property int cancelled:0
    property double since:Date.now()
    property double deadline:Date.now()+25000
    property string oldId:""
    property string finalText:""
    Connections {target:Audit.Voice
        function onSubmitted(text){root.submitted++;root.finalText=text;}
        function onTranscriptChanged(){if(Audit.Voice.transcript)root.partials++;}
        function onCancelled(){root.cancelled++;}
    }
    function check(ok,label):void {if(!ok)throw new Error(label+" stage="+stage);}
    function next():void {stage++;since=Date.now();}
    Timer {interval:40;repeat:true;running:true;onTriggered:{
        try {
            const v=Audit.Voice;
            check(Date.now()<deadline,"Timed out");
            if(stage===0){
                check(!v.workerStarted&&!v.ready,"Cold idle started a worker");
                Audit.Luma.busy=true;v.begin();check(!v.active,"Started while assistant busy");Audit.Luma.busy=false;
                Audit.Recorder.selecting=true;v.begin();check(!v.active,"Started during screen selection");Audit.Recorder.selecting=false;
                v.begin();v.release();check(v.phase==="finishing","Quick release lost");next();
            } else if(stage===1&&v.ready&&!v.active){
                check(submitted===0,"Quick empty hold submitted");
                v.begin();oldId=v.identity;
                v.receive({event:"final",id:"stale",text:"Do not submit"});
                check(v.active&&submitted===0,"Stale final accepted");
                v.receive({event:"listening",id:v.identity});check(v.phase==="listening","Listening phase failed");next();
            } else if(stage===2&&Date.now()-since>4100){v.release();check(v.phase==="finishing","Release failed");next();
            } else if(stage===3&&!v.active){
                check(submitted===1&&finalText.length>0&&partials>0,"Native hold did not submit exactly once");
                v.receive({event:"final",id:oldId,text:"duplicate"});check(submitted===1,"Duplicate final accepted");
                v.begin();oldId=v.identity;v.cancel();
                v.receive({event:"final",id:oldId,text:"cancelled"});check(!v.active&&submitted===1,"Cancel submitted");next();
            } else if(stage===4){
                v.begin();oldId=v.identity;Audit.CanvasState.opened=false;
                check(!v.active&&!v.identity,"Closing canvas did not cancel");
                v.receive({event:"final",id:oldId,text:"closed"});check(submitted===1,"Closed hold submitted");
                Audit.Preferences.lumaVoiceWarm=true;next();
            } else if(stage===5&&v.ready){
                v.begin();oldId=v.identity;Audit.Session.locked=true;
                check(!v.active&&!v.identity,"Lock did not cancel");
                v.begin();check(!v.active,"Started while locked");
                v.receive({event:"final",id:oldId,text:"locked"});check(submitted===1,"Locked hold submitted");next();
            } else if(stage===6&&Date.now()-since>400){
                check(v.ready&&v.workerStarted,"Warm worker unloaded while locked");
                Audit.Session.locked=false;Audit.Preferences.lumaVoice=false;next();
            } else if(stage===7&&!v.workerStarted){
                check(!v.ready,"Disabled worker still ready");
                v.begin();check(!v.active,"Disabled voice started");
                Audit.Preferences.lumaVoice=true;next();
            } else if(stage===8&&v.ready){next();
            } else if(stage===9&&Date.now()-since>400){
                check(v.ready&&v.workerStarted,"Warm idle worker unloaded");
                Audit.Preferences.lumaVoiceWarm=false;next();
            } else if(stage===10&&!v.workerStarted){
                check(!v.ready,"Idle worker did not unload");
                Audit.Session.locked=true;v.prepare();check(!v.workerStarted,"Prepared while locked");Audit.Session.locked=false;
                v.begin();v.cancel();Audit.Preferences.lumaVoice=false;next();
            } else if(stage===11&&!v.workerStarted){
                check(submitted===1&&cancelled>=4,"Lifecycle emitted extra submissions");
                console.log("VOICE QML AUDIT PASS: startup, native final, stale/duplicate events, cancel, dismissal, lock, disable, retention and idle unload");
                Qt.quit();
            }
        } catch(e) {console.error("VOICE QML AUDIT FAIL: "+e);Qt.exit(1);}
    }}
}
''')
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_CONTROLS_STYLE='Basic')
    result = subprocess.run(['quickshell', '-p', str(workspace / 'audit.qml')], env=env,
                            text=True, capture_output=True, timeout=35)
    log = result.stdout + result.stderr
    assert result.returncode == 0 and 'VOICE QML AUDIT PASS' in log, log[-3500:]
    assert 'VOICE QML AUDIT FAIL' not in log
    print(next(line for line in log.splitlines() if 'VOICE QML AUDIT PASS' in line))
