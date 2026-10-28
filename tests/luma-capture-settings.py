#!/usr/bin/env python3
"""Exercise the production privacy toggle with an isolated helper process."""
import json
from pathlib import Path
import tempfile

from settings import run, workspace

BACKEND = '''if len(sys.argv)>2 and sys.argv[1].endswith('/luma-capture.py'):
    from pathlib import Path
    import time
    path=Path(os.environ['MODESTY_CAPTURE_FIXTURE'])
    state=json.loads(path.read_text())
    command=sys.argv[2]
    with path.with_suffix('.calls').open('a') as audit: audit.write(command+'\\n')
    if command=='fixture-fail': state['fail']=True
    elif command=='fixture-unsupported': state.update(enabled=True,loaded=False,supported=False,fail=False)
    elif command=='fixture-unloaded': state.update(enabled=True,loaded=False,supported=True)
    elif command=='fixture-malformed': state['malformed']=True
    elif command in ('enable','disable'):
        time.sleep(.2)
        if command=='enable' and state.get('fail'):
            print('Stop screen capture before enabling privacy',file=sys.stderr)
            sys.exit(1)
        state.update(enabled=command=='enable',loaded=command=='enable')
    path.write_text(json.dumps(state))
    if command=='status' and state.get('malformed'): print('invalid status')
    else: print(json.dumps(state))
    sys.exit(0)
'''

UI = '''import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import "modules/settings" as Settings
import "modules/settings/SettingsCatalog.js" as Catalog
import qs.services
ShellRoot {
    Settings.SettingsWindow {id:settings;implicitWidth:760;implicitHeight:560}
    TestCase {id:input;when:false}
    Process {id:controller}
    function check(ok,message) {if(!ok)throw new Error(message);}
    function child(name) {
        input.tryVerify(()=>!!input.findChild(settings.contentItem,name),3000,"Missing "+name);
        return input.findChild(settings.contentItem,name);
    }
    function settle() {input.tryVerify(()=>!LumaCapture.busy&&LumaCapture.state!==null,3000,"Status did not settle");}
    function fixture(command) {
        controller.command=["python3",LumaCapture.backend,command];controller.running=true;
        input.tryVerify(()=>!controller.running,3000,"Fixture command did not finish");
    }
    function refresh() {LumaCapture.refresh();settle();}
    Component.onCompleted:{IslandState.settingsPage="search";IslandState.settingsOpen=true;Preferences.set("motion","instant");}
    Timer {interval:200;running:true;onTriggered:{try {
        const root=child("settings-root");root.navigate("search","capture","private-capture");
        const toggle=child("custom-private-capture");settle();
        input.tryVerify(()=>!root.pendingTarget,3000,"Toggle reveal did not finish");input.wait(50);
        check(toggle.checked&&toggle.enabled,"Saved active state not shown");
        check(Catalog.search("Discord").some(r=>r.key==="private-capture"),"Privacy setting is not searchable");
        input.mouseClick(toggle);check(LumaCapture.busy&&!toggle.enabled&&toggle.checked,"Pending toggle state "+JSON.stringify({busy:LumaCapture.busy,enabled:toggle.enabled,checked:toggle.checked}));
        LumaCapture.setEnabled(false);settle();check(!toggle.checked,"Disable did not update toggle");
        toggle.forceActiveFocus();input.keyClick(Qt.Key_Space);check(LumaCapture.busy,"Space did not enable");
        LumaCapture.setEnabled(false);settle();check(toggle.checked,"Enable did not update toggle");
        input.mouseClick(toggle);settle();fixture("fixture-fail");
        input.mouseClick(toggle);settle();
        check(!toggle.checked&&child("custom-private-capture-error").text.includes("Stop screen capture"),"Failed enable was not rolled back with error");
        fixture("fixture-unsupported");refresh();
        check(toggle.checked&&toggle.enabled&&!child("custom-private-capture-status").text.startsWith("Active"),"Unsupported saved-on state is misleading or cannot disable");
        input.mouseClick(toggle);settle();check(!toggle.checked&&!toggle.enabled,"Unsupported off state permits enable");
        fixture("fixture-unloaded");refresh();
        check(toggle.checked&&child("custom-private-capture-status").text.includes("inactive"),"Saved state was mistaken for active protection");
        input.mouseClick(toggle);root.navigate("clock");
        input.tryVerify(()=>!input.findChild(settings.contentItem,"custom-private-capture"),3000,"Editor not destroyed");
        settle();check(!LumaCapture.state.enabled,"Operation did not survive editor destruction");
        root.navigate("search","capture","private-capture");settle();
        fixture("fixture-malformed");LumaCapture.refresh();
        input.tryVerify(()=>!LumaCapture.busy,3000,"Malformed status left service busy");
        check(LumaCapture.state===null&&!child("custom-private-capture").enabled&&!!LumaCapture.error,"Unknown status was treated as protected");
        console.log("CAPTURE SETTINGS PASS");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}'''

PREVIEW = '''import QtQuick
import QtTest
import Quickshell
import "modules/settings" as Settings
import qs.services
ShellRoot {
    FloatingWindow {visible:true;implicitWidth:600;implicitHeight:340;Settings.CaptureSettings {id:editor;width:550}}
    TestCase {id:input;when:false}
    Timer {interval:200;running:true;onTriggered:{try {
        LumaCapture.refresh();LumaCapture.setEnabled(true);input.wait(100);
        const toggle=input.findChild(editor,"custom-private-capture");
        if(toggle.enabled||LumaCapture.busy||!LumaCapture.status.includes("preview"))throw new Error("Preview enabled side effects");
        console.log("CAPTURE PREVIEW PASS");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}'''

for preview in (False, True):
    with tempfile.TemporaryDirectory(prefix='modesty-capture-settings-') as directory:
        environment = workspace(directory, preview=preview)
        fixture = Path(directory)/'capture.json'
        fixture.write_text(json.dumps(dict(enabled=True, loaded=True, supported=True)))
        environment['MODESTY_CAPTURE_FIXTURE'] = str(fixture)
        python = Path(directory)/'bin/python3'
        python.write_text(python.read_text().replace('if len(sys.argv)>1', BACKEND+'elif len(sys.argv)>1', 1))
        run(directory, environment, PREVIEW if preview else UI, 'CAPTURE PREVIEW PASS' if preview else 'CAPTURE SETTINGS PASS')
        calls = fixture.with_suffix('.calls').read_text().splitlines() if fixture.with_suffix('.calls').exists() else []
        if preview:
            assert calls == [], calls
        else:
            assert calls.count('enable') == 2 and calls.count('disable') == 4, calls
