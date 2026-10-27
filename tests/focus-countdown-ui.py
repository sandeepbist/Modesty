#!/usr/bin/env python3
"""Observe production countdown labels under a bounded native event-loop stall."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from unittest.mock import patch

import qml

COUNTDOWN = r'''import QtQuick
import Quickshell
import qs.services
import qs.components
import "modules/island" as Island
ShellRoot {
    id:probe
    property double started:0
    property var changes:[]
    property var frames:[]
    property var stallBounds:({})
    FloatingWindow {visible:true;implicitWidth:420;implicitHeight:100
        Island.FocusStatus {id:status;x:20;y:15;width:138;height:35}
        PanelText {id:direct;x:210;y:15;width:138;height:35;text:FocusTimer.timeText}
    }
    function walk(item) {let all=[item];for(const child of item.children||[])all=all.concat(walk(child));return all;}
    Component.onCompleted: {
        Preferences.motion="MOTION";started=Date.now();
        FocusTimer.phase="paused";FocusTimer.duration=60;FocusTimer.remaining=15;
        FocusTimer.deadline=started+14500;FocusTimer.phase="running";
        changes.push({at:Date.now(),elapsed:0,remaining:FocusTimer.remaining,text:FocusTimer.timeText});
    }
    Connections {target:FocusTimer;function onRemainingChanged(){if(probe.started>0)
        probe.changes.push({at:Date.now(),elapsed:Date.now()-probe.started,remaining:FocusTimer.remaining,text:FocusTimer.timeText});}}
    Timer {interval:850;running:true;onTriggered:{
        const begin=Date.now();while(Date.now()-begin<800){}
        probe.stallBounds={begin,end:Date.now(),elapsed:begin-probe.started,actualMs:Date.now()-begin,requestedMs:800};
    }}
    Timer {interval:25;running:true;repeat:true;onTriggered:{
        const digits=probe.walk(status).find(item=>item instanceof SlidingDigits&&item.visible);
        const drawn=digits?probe.walk(digits).filter(item=>item.shown!==undefined).sort((a,b)=>a.index-b.index).map(item=>({
            index:item.index,shown:item.shown,target:item.value,progress:item.progress,outgoing:item.outgoing,
            labels:(item.children||[]).filter(child=>child instanceof PanelText&&child.visible).map(child=>({text:child.text,y:child.y}))
        })):[];
        probe.frames.push({at:Date.now(),elapsed:Date.now()-probe.started,remaining:FocusTimer.remaining,direct:direct.text,drawn});
        if(Date.now()-probe.started>=3200) {
            FocusTimer.phase="paused";
            console.log("FOCUS_OBSERVATIONS "+JSON.stringify({changes:probe.changes,frames:probe.frames,stall:probe.stallBounds}));
            console.log("COUNTDOWN STALL COMPLETE");Qt.quit();
        }
    }}
}
'''

BOUNDS = r'''import QtQuick
import QtTest
import Quickshell
import qs.services
ShellRoot {
    TestCase {id:input;when:false}
    function check(ok,message) {if(!ok)throw new Error(message);}
    Timer {interval:100;running:true;onTriggered:{try {
        check(Preferences.preview,"Expected preview guards");Preferences.motion="instant";
        const observations=[];
        for(const phase of ["paused","idle"]) {
            FocusTimer.phase=phase;FocusTimer.remaining=7;FocusTimer.deadline=0;
            const begin=Date.now();input.wait(1150);
            check(FocusTimer.remaining===7&&FocusTimer.timeText==="00:07","Inactive countdown changed value");
            observations.push({phase,begin,end:Date.now(),remaining:FocusTimer.remaining,text:FocusTimer.timeText});
        }
        FocusTimer.phase="paused";FocusTimer.duration=60;FocusTimer.remaining=5;
        const begin=Date.now();FocusTimer.deadline=begin+4500;FocusTimer.phase="running";
        while(Date.now()-begin<2200){}
        const stallEnd=Date.now();input.wait(250);
        check(FocusTimer.remaining===3,"Late update failed deadline catch-up");
        observations.push({phase:"catch-up",begin,stallEnd,at:Date.now(),deadline:FocusTimer.deadline,remaining:FocusTimer.remaining,text:FocusTimer.timeText});
        FocusTimer.phase="paused";FocusTimer.remaining=1;FocusTimer.deadline=Date.now()+150;FocusTimer.phase="running";
        input.wait(500);
        check(FocusTimer.remaining===0&&FocusTimer.phase==="finished"&&FocusTimer.deadline===0,"Countdown failed zero completion");
        check(!Notifications.dnd&&!FocusTimer.quietOwned&&Notifications.list.length===0,"Preview changed quiet or notifications");
        observations.push({phase:FocusTimer.phase,at:Date.now(),remaining:FocusTimer.remaining,deadline:FocusTimer.deadline,text:FocusTimer.timeText});
        console.log("FOCUS_OBSERVATIONS "+JSON.stringify(observations));
        console.log("COUNTDOWN BOUNDS PASS");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=qml.ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    qml.ROOT = args.source.resolve()
    native_subprocess = subprocess.run
    with tempfile.TemporaryDirectory(prefix='modesty-focus-isolated-') as temporary:
        isolated = Path(temporary)
        output = args.output.resolve() if args.output else isolated / 'evidence'
        output.mkdir(parents=True, exist_ok=True)
        paths = ['services/FocusTimer.qml', 'modules/island/FocusStatus.qml',
                 'components/RollingText.qml', 'components/SlidingDigits.qml', 'tests/qml.py',
                 'services/Preferences.qml', 'theme/Tokens.qml']
        (output / 'manifest.json').write_text(json.dumps({
            'started_utc': datetime.now(timezone.utc).isoformat(), 'source': str(qml.ROOT),
            'test_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'source_sha256': {name: hashlib.sha256((qml.ROOT / name).read_bytes()).hexdigest() for name in paths},
            'scope': 'Seeded preview fixture; production native Timer and labels; no real UI timer actions.',
            'backend': 'offscreen, software', 'bus': 'dbus-run-session',
        }, indent=2) + '\n')

        def observe(source, marker, name):
            evidence = output / name
            evidence.mkdir()
            (evidence / 'shell.qml').write_text(source)

            def native_run(command, **kwargs):
                environment = kwargs['env']
                for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE',
                            'DBUS_SESSION_BUS_ADDRESS', 'DBUS_SYSTEM_BUS_ADDRESS', 'XDG_SESSION_ID'):
                    environment.pop(key, None)
                for key in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_RUNTIME_DIR'):
                    folder = isolated / name / key.lower()
                    folder.mkdir(parents=True, mode=0o700)
                    environment[key] = str(folder)
                environment.update(QT_QPA_PLATFORMTHEME='generic', QT_NO_XDG_DESKTOP_PORTAL='1',
                                   DBUS_SYSTEM_BUS_ADDRESS='unix:path=' + str(isolated / 'no-system-bus'),
                                   PIPEWIRE_REMOTE='modesty-no-live-pipewire')
                result = native_subprocess(['dbus-run-session', '--', *command], **kwargs)
                log = result.stdout + result.stderr
                (evidence / 'run.log').write_text(log)
                assert not re.search(r'Binding loop|Unable to assign|SyntaxError', log), log[-2000:]
                state = Path(environment['XDG_STATE_HOME'])
                files = [str(path.relative_to(state)) for path in state.rglob('*') if path.is_file()]
                (evidence / 'state-files.json').write_text(json.dumps(files) + '\n')
                assert not files, 'Preview wrote state files: ' + repr(files)
                return result

            with patch('qml.subprocess.run', side_effect=native_run):
                qml.run(source, marker, timeout=15)
            match = re.search(r'FOCUS_OBSERVATIONS (.+)', (evidence / 'run.log').read_text())
            assert match, 'Missing native observations'
            observed = json.loads(match[1])
            (evidence / 'observations.json').write_text(json.dumps(observed, indent=2) + '\n')
            return observed

        for motion in ('gentle', 'instant'):
            trial = observe(COUNTDOWN.replace('MOTION', motion), 'COUNTDOWN STALL COMPLETE', motion)
            stall = trial['stall']
            assert 750 <= stall['elapsed'] <= 950 and 800 <= stall['actualMs'] <= 900, stall
            values = [item['remaining'] for item in trial['changes']]
            assert 14 in values, f'Missing 14 after bounded 800ms native stall ({motion}): {values}'
            assert all(value in values for value in (15, 13, 12)), values
            stable = set()
            for frame in trial['frames']:
                if len(frame['drawn']) == 5 and all(digit['progress'] == 1 and not digit['outgoing'] and
                        any(label['text'] == digit['shown'] and abs(label['y']) < .01 for label in digit['labels'])
                        for digit in frame['drawn']):
                    stable.add(''.join(digit['shown'] for digit in frame['drawn']))
            assert {'00:15', '00:14', '00:13', '00:12'} <= stable, stable
            print(f'PASS {motion} source={values}, stable labels={sorted(stable)}')
        observe(BOUNDS, 'COUNTDOWN BOUNDS PASS', 'bounds')
        print('PASS late deadline catch-up, zero, paused/idle value stability')


if __name__ == '__main__':
    main()
