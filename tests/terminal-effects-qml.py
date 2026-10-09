#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
import qml

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('terminal_installer',ROOT/'install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
real_run=subprocess.run
real_kitty=shutil.which('kitty')
with tempfile.TemporaryDirectory(prefix='modesty-terminal-ui-') as temporary:
    home=Path(temporary);config=home/'.config';state=home/'.local/state';binpath=home/'bin';binpath.mkdir()
    log=home/'launches.jsonl'
    python=binpath/'python3'
    python.write_text('#!'+sys.executable+'\nimport os,subprocess,sys\n'
        'if len(sys.argv)>1 and sys.argv[1].endswith("terminal-effects.py"):\n'
        '    sys.exit(subprocess.call(['+repr(sys.executable)+']+sys.argv[1:]))\n'
        'print("[]" if len(sys.argv)>1 and sys.argv[1].endswith("terminal_art.py") else "{}")\n')
    python.chmod(0o755)
    kitty=binpath/'kitty'
    kitty.write_text('#!'+sys.executable+'\nimport json,subprocess,sys\n'
        'if sys.argv[1:2]==["+runpy"]:\n'
        +('    sys.exit(subprocess.call(['+repr(real_kitty)+']+sys.argv[1:]))\n' if real_kitty else '    sys.exit(1)\n')+
        'with open('+repr(str(log))+',"a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\n')
    kitty.chmod(0o755)
    foot=binpath/'foot'
    foot.write_text('#!'+sys.executable+'\nimport json,sys\nwith open('+repr(str(log))+',"a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\n')
    foot.chmod(0o755)
    environment=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(config),XDG_STATE_HOME=str(state),XDG_CACHE_HOME=str(home/'.cache'),XDG_DATA_HOME=str(home/'.local/share'),PATH=str(binpath)+':'+os.environ['PATH'],GSETTINGS_BACKEND='memory')
    for name in ('DISPLAY','WAYLAND_DISPLAY','HYPRLAND_INSTANCE_SIGNATURE','XDG_SESSION_ID','DBUS_SESSION_BUS_ADDRESS','MODESTY_PREVIEW'):
        environment.pop(name,None)
    workspaces=[]
    def isolated_run(command,**kwargs):
        if command[0]=='qs':
            workspace=Path(command[-1]);workspaces.append(workspace)
            (workspace/'install.py').symlink_to(ROOT/'install.py')
            kwargs['env']=dict(kwargs['env'],**{key:value for key,value in environment.items() if key in ('HOME','XDG_CONFIG_HOME','XDG_STATE_HOME','XDG_CACHE_HOME','XDG_DATA_HOME','PATH','GSETTINGS_BACKEND')})
            for name in ('DISPLAY','WAYLAND_DISPLAY','HYPRLAND_INSTANCE_SIGNATURE','XDG_SESSION_ID','DBUS_SESSION_BUS_ADDRESS'):
                kwargs['env'].pop(name,None)
            kwargs['env']['MODESTY_PREVIEW']=mode
        try: return real_run(command,**kwargs)
        except subprocess.TimeoutExpired as error:
            raise AssertionError((error.stdout or b" ").decode()+"\n"+(error.stderr or b" ").decode()) from error
    with patch.dict(os.environ,environment,clear=True),patch.object(qml.subprocess,'run',side_effect=isolated_run):
        mode='1'
        qml.run('''import QtQuick
import QtTest
import Quickshell
import "modules/settings" as Settings
import "modules/settings/SettingsCatalog.js" as Catalog
import qs.services
ShellRoot {
    Settings.SettingsWindow { id: settings }
    TestCase { id: keyboard; when:false }
    Component.onCompleted: { IslandState.settingsPage="terminal"; IslandState.settingsOpen=true; }
    Timer { interval:800; running:true; repeat:true; onTriggered:{try {
        const effects=keyboard.findChild(settings.contentItem,"terminalEffectsSettings");
        if(!effects||effects.busy)return;
        if(effects.availability!=="absent")throw new Error("Missing optional setup status was not shown");
        const trail=keyboard.findChild(effects,"Native cursor trail");
        const setup=keyboard.findChild(effects,"terminalEffectsSetup");
        if(trail.enabled||setup.enabled)throw new Error("Preview actions were enabled");
        if(!effects.message.includes("approved setup"))throw new Error("Setup prerequisite is missing");
        if(!Catalog.search("kitty cursor trail").some(result=>result.page==="terminal"&&result.block==="effects"))throw new Error("Effects search destination is missing");
        if(effects.reveal("trail")!==keyboard.findChild(effects,"terminalEffectsStatus"))throw new Error("Preview trail did not reveal status");
        const root=keyboard.findChild(settings.contentItem,"settings-root");
        root.navigate("terminal","effects","trail");
        if(!Catalog.search("native cursor trail").some(result=>result.key==="trail"))throw new Error("Exact trail search destination is missing");
        keyboard.mouseClick(setup);
        Qt.callLater(()=>{
            const status=keyboard.findChild(effects,"terminalEffectsStatus");
            if(!status.activeFocus||root.pendingTarget!==null){console.error("Preview search did not focus status");Qt.exit(1);return;}
            console.log("TERMINAL QML PREVIEW PASS");Qt.quit();
        });
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''','TERMINAL QML PREVIEW PASS',timeout=25)
        assert not log.exists() and not (config/'kitty').exists()
        if real_kitty:
            with patch.object(installer,'HOME',home),patch.object(installer,'CONFIG',config),patch.object(installer,'STATE',state):
                installer.install_files(['terminal-effects'],False)
            mode='0'
            qml.run('''import QtQuick
import QtTest
import Quickshell
import "modules/settings" as Settings
ShellRoot {
    property int phase:0
    FloatingWindow {
        visible:true;implicitWidth:600;implicitHeight:300
        Settings.TerminalEffectsSettings { id: effects; anchors.fill:parent }
        TestCase { id:keyboard; when:false }
    }
    Timer { interval:350; running:true; repeat:true; onTriggered:{try {
        if(effects.busy||effects.availability==="checking")return;
        if(effects.availability!=="ready")throw new Error(effects.message);
        const trail=keyboard.findChild(effects,"Native cursor trail");
        const open=keyboard.findChild(effects,"terminalEffectsOpen");
        const setup=keyboard.findChild(effects,"terminalEffectsSetup");
        if(phase===0){
            if(!trail.checked||!trail.enabled)throw new Error("Installed trail was not enabled");
            trail.forceActiveFocus();keyboard.keyClick(Qt.Key_Space);phase=1;return;
        }
        if(phase===1){
            if(effects.trailEnabled||trail.checked)throw new Error("Trail did not disable through actual control");
            trail.forceActiveFocus();keyboard.keyClick(Qt.Key_Space);phase=2;return;
        }
        if(phase===2){
            if(!effects.trailEnabled||!trail.checked)throw new Error("Trail did not enable through actual control");
            keyboard.mouseClick(open);phase=3;return;
        }
        if(phase===3){keyboard.mouseClick(setup);phase=4;return;}
        if(phase===4){
            if(effects.error)throw new Error(effects.error);
            if(effects.reveal("open")!==open)throw new Error("Open reveal target is wrong");
            console.log("TERMINAL QML CONTROLS PASS");Qt.quit();
        }
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''','TERMINAL QML CONTROLS PASS',timeout=30)
            launches=[json.loads(line) for line in log.read_text().splitlines()]
            assert launches==[['--config',str(config/'kitty/modesty.conf')],['--title=Modesty terminal setup','python3',str(workspaces[-1]/'install.py'),'--install-terminal-effects']],launches
            assert (config/'kitty/modesty-effects.conf').read_text().startswith('cursor_trail 1\n')
            qml.run('''import QtQuick
import Quickshell
import "modules/settings" as Settings
ShellRoot {
    Settings.TerminalEffectsSettings { id:effects }
    Timer { interval:300; running:true; repeat:true; onTriggered:{
        if(effects.busy||effects.availability==="checking")return;
        if(effects.availability!=="ready"||!effects.trailEnabled){console.error("Native trail did not persist");Qt.exit(1);return;}
        console.log("TERMINAL QML RESTART PASS");Qt.quit();
    }}
}
''','TERMINAL QML RESTART PASS',timeout=20)
        if not (state/'modesty-install/receipt.json').exists():
            with patch.object(installer,'HOME',home),patch.object(installer,'CONFIG',config),patch.object(installer,'STATE',state):
                installer.install_files(['terminal-effects'],False)
        (binpath/'qs').symlink_to(shutil.which('qs'))
        kitty.unlink()
        environment['PATH']=str(binpath)
        mode='1'
        qml.run('''import QtQuick
import QtTest
import Quickshell
import "modules/settings" as Settings
ShellRoot {
    Settings.TerminalEffectsSettings { id:effects }
    TestCase { id:keyboard; when:false }
    Timer { interval:300; running:true; repeat:true; onTriggered:{
        if(effects.busy||effects.availability==="checking")return;
        if(effects.availability!=="missing-kitty"||!effects.message.includes("Kitty is missing")){console.error("Missing Kitty prerequisite is wrong");Qt.exit(1);return;}
        if(keyboard.findChild(effects,"Native cursor trail").enabled){console.error("Missing Kitty toggle is enabled");Qt.exit(1);return;}
        console.log("TERMINAL QML MISSING KITTY PASS");Qt.quit();
    }}
}
''','TERMINAL QML MISSING KITTY PASS',timeout=20)
print('PASS isolated terminal Settings navigation/search, prerequisite, preview guards, keyboard toggle, native persistence and stubbed launch/setup argv')
