#!/usr/bin/env python3
"""Deliver keyboard events to the production launcher in an isolated window."""
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from qml import run

with tempfile.TemporaryDirectory(prefix='modesty-launcher-ui-') as temporary:
    applications = Path(temporary) / 'applications'
    applications.mkdir()
    for name in ('One', 'Two'):
        (applications / ('modesty-keyboard-'+name+'.desktop')).write_text(
            '[Desktop Entry]\nType=Application\nName=Modesty Keyboard Fixture '+name+
            '\nExec=/usr/bin/true\nComment=Keyboard fixture\n')
    with patch.dict(os.environ, XDG_DATA_HOME=temporary):
        run('''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import "modules/settings/SettingsCatalog.js" as Catalog
import qs.services
ShellRoot {
    property int phase:0
    FloatingWindow {
        visible:true;implicitWidth:550;implicitHeight:374
        Island.LauncherMenu {id:launcher;anchors.fill:parent}
        TestCase {id:keyboard;when:false}
    }
    function descriptions(item) {
        let labels=[];
        for(const child of item.children??[]) {
            if(child.text==="Keyboard fixture")labels.push(child);
            labels=labels.concat(descriptions(child));
        }
        return labels;
    }
    Timer {interval:300;running:true;repeat:true;onTriggered:{try {
        if(phase===1) {
            const labels=descriptions(launcher);
            if(labels.length!==2||labels.some(label=>label.visible))throw new Error("Descriptions not hidden by default");
            Preferences.set("launcherDescriptions",true);
            if(labels.some(label=>!label.visible)||!Preferences.snapshot().launcherDescriptions)throw new Error("Description setting did not apply");
            Preferences.set("launcherDescriptions",false);
            if(labels.some(label=>label.visible))throw new Error("Description setting did not hide labels");
            if(!Catalog.search("app descriptions").some(result=>result.key==="launcherDescriptions"))throw new Error("Description setting not discoverable");
            console.log("LAUNCHER UI CHECK PASS: keyboard navigation and description toggle");Qt.quit();return;
        }
        const input=keyboard.findChild(launcher,"appSearch");
        input.text="Modesty Keyboard Fixture";input.forceActiveFocus();
        if(launcher.results.length!==2)throw new Error("Fixture applications missing");
        keyboard.keyClick(Qt.Key_Tab);
        if(launcher.selected!==1)throw new Error("Tab did not advance selection");
        keyboard.keyClick(Qt.Key_Tab,Qt.ShiftModifier);
        if(launcher.selected!==0)throw new Error("Shift+Tab moved forward");
        keyboard.keyClick(Qt.Key_Down);keyboard.keyClick(Qt.Key_Backtab);
        if(launcher.selected!==0)throw new Error("Backtab did not move backwards");
        input.text="zzzzmodestynotfoundzzzz";
        keyboard.keyClick(Qt.Key_Down);
        if(launcher.results.length||launcher.selected!==0)throw new Error("Empty-result selection escaped bounds");
        input.text="Modesty Keyboard Fixture";phase=1;
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''', 'LAUNCHER UI CHECK PASS: keyboard navigation and description toggle')
