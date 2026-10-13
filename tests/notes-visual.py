#!/usr/bin/env python3
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
from qml import ROOT

output = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/modesty-notes-visual').resolve()
output.mkdir(parents=True, exist_ok=True)
scenes = [
    dict(name='capture-light', width=1100, height=700, mode='light', library=False, scale=1),
    dict(name='capture-dark', width=1100, height=700, mode='dark', library=False, scale=1),
    dict(name='library-dark', width=1100, height=700, mode='dark', library=True, scale=1),
    dict(name='library-light', width=1100, height=700, mode='light', library=True, scale=1),
    dict(name='narrow-light', width=540, height=620, mode='light', library=True, scale=1),
    dict(name='narrow-editor-light', width=540, height=620, mode='light', library=True, scale=1, editing=True),
    dict(name='small-large-scale', width=620, height=470, mode='dark', library=True, scale=1.25),
    dict(name='short-error-library', width=620, height=470, mode='dark', library=True, scale=1.25, failure=True),
    dict(name='empty-library-light', width=540, height=620, mode='light', library=True, scale=1, category='trash'),
    dict(name='empty-capture-light', width=1100, height=700, mode='light', library=False, scale=1, empty=True),
    dict(name='failure-dark', width=1100, height=700, mode='dark', library=False, scale=1, failure=True),
    dict(name='overflow-dark', width=1100, height=700, mode='dark', library=False, scale=1, menu=True),
]
source = '''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    id: test
    property var scenes: SCENES
    property int index: 0
    property bool pending: false
    FloatingWindow {
        id: window; visible: true; title: "Modesty Notes isolated visual check"
        implicitWidth: 1100; implicitHeight: 700
        Item {id: scene; width: 1100; height: 700
            Rectangle {anchors.fill: parent; color: Theme.light ? "#e5eceb" : "#243839"}
            Island.IslandSurface {id: surface; anchors.horizontalCenter: parent.horizontalCenter; y: 45
                availableWidth: scene.width; availableHeight: scene.height - y - 20; scale: Preferences.uiScale; transformOrigin: Item.Top
            }
        }
    }
    TestCase {id: driver; when: false}
    function apply() {
        const settings = scenes[index];
        scene.width = settings.width; scene.height = settings.height;
        Preferences.set("uiScale", settings.scale); Theme.setMode(settings.mode);
        Notes.libraryOpen = settings.library;
        const pane = surface.clockStage.diagnostics().entries.find(entry => entry.name === "notes");
        if (pane?.loaded) {
            const panel = driver.findChild(surface, "notesPanel");
            const menu = driver.findChild(panel, "notesOverflow");
            menu.close(); panel.category = settings.category || "active"; panel.showEditor = !!settings.editing;
            if (settings.empty) panel.newNote();
            else if (Notes.activeId !== "thought") panel.selectNote("thought");
            Notes.error = settings.failure ? "Could not save your note. Your draft is still here." : "";
            const body = driver.findChild(surface, "notesBody");
            body.cursorPosition = 0;
            if (settings.menu) {
                menu.open();
                Qt.callLater(() => {if (scene.Overlay.overlay) scene.Overlay.overlay.parent = scene;});
            }
        }
    }
    Component.onCompleted: {
        Preferences.set("motion", "instant"); Preferences.set("welcomeAtLogin", false);
        Notes.items = [
            {id:"thought",title:"A little breathing room",body:"Keep the useful things close.\\n\\nA place for the thought before it disappears. Plain text, a few words, then back to the day.\\n\\n- Pick up coffee beans\\n- Send the sketch to Maya\\n- Take a walk before sunset",createdAt:"2026-10-12T10:00:00Z",updatedAt:"2026-10-12T10:00:00Z",status:"active",pinned:true,revision:1},
            {id:"weekend",title:"Weekend ideas",body:"Browse the bookshop by the station. Try the new trail. Make room for a slow morning.",createdAt:"2026-10-11T10:00:00Z",updatedAt:"2026-10-11T10:00:00Z",status:"active",pinned:false,revision:1},
            {id:"recipe",title:"",body:"Lemon pasta\\nZest, butter, a splash of cooking water. Finish with parsley.",createdAt:"2026-10-10T10:00:00Z",updatedAt:"2026-10-10T10:00:00Z",status:"active",pinned:false,revision:1}
        ];
        Notes.select("thought"); IslandState.openMenu("notes"); apply();
    }
    Timer {id: capture; interval: 650; running: true; repeat: true; onTriggered: {
        if (pending) return;
        const stage = surface.clockStage;
        const pane = stage.diagnostics().entries.find(entry => entry.name === "notes");
        if (!pane?.loaded || pane.opacity < .99) return;
        if (scenes[index].menu && !driver.findChild(driver.findChild(surface, "notesPanel"), "notesOverflow").opened) {apply();return;}
        if (stage.width > stage.maximumWidth || stage.height > stage.maximumHeight) {console.error("Notes escaped screen bounds");Qt.exit(1);return;}
        pending = true;
        scene.grabToImage(result => {
            const name = scenes[index].name;
            if (!result.saveToFile(OUTPUT + "/" + name + ".png")) {console.error("Capture failed " + name);Qt.exit(1);return;}
            console.log("CAPTURE " + name + " " + JSON.stringify({width:stage.width,height:stage.height,input:pane.input}));
            index++; pending = false;
            if (index === scenes.length) {console.log("PASS production Notes visual captures");Qt.quit();return;}
            apply();
        });
    }}
}
'''.replace('SCENES', json.dumps(scenes)).replace('OUTPUT', json.dumps(str(output)))
with tempfile.TemporaryDirectory(prefix='modesty-notes-visual-shell-') as directory:
    workspace = Path(directory)
    for name in ('components', 'modules', 'assets', 'theme', 'services', 'scripts'):
        (workspace / name).symlink_to(ROOT / name, target_is_directory=True)
    (workspace / 'shell.qml').write_text(source)
    environment = dict(os.environ, MODESTY_PREVIEW='1', QT_QPA_PLATFORM='wayland',
                       QT_QPA_PLATFORMTHEME='generic', QS_NO_RELOAD_POPUP='1',
                       XDG_STATE_HOME=str(workspace / 'state'), XDG_CACHE_HOME=str(workspace / 'cache'))
    environment.pop('QSG_RHI_BACKEND', None)
    try:
        result = subprocess.run(['qs', '--no-color', '-p', str(workspace)], env=environment,
                                capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired as error:
        (output / 'capture.log').write_bytes((error.stdout or b'') + (error.stderr or b''))
        raise
    log = result.stdout + result.stderr
    (output / 'capture.log').write_text(log)
    assert result.returncode == 0 and 'PASS production Notes visual captures' in log, log
    assert 'ReferenceError' not in log and 'TypeError' not in log, log
    print('PASS production Notes visual captures')
for scene in scenes:
    path = output / (scene['name'] + '.png')
    assert path.is_file() and path.stat().st_size > 1000, path
    print(path)
