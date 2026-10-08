#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def workspace(directory, preview=True):
    directory = Path(directory)
    for name in ('components', 'modules', 'assets', 'theme', 'services', 'scripts'):
        (directory / name).symlink_to(ROOT / name, target_is_directory=True)
    environment = {key: value for key, value in os.environ.items() if key not in (
        'WAYLAND_DISPLAY', 'DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE', 'DBUS_SESSION_BUS_ADDRESS')}
    for key, name in [('HOME', 'home'), ('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                      ('XDG_STATE_HOME', 'state'), ('XDG_CACHE_HOME', 'cache'), ('XDG_RUNTIME_DIR', 'runtime')]:
        path = directory / name
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    commands = directory / 'bin'
    commands.mkdir()
    stub = commands / 'stub'
    stub.write_text('#!/bin/sh\nexit 0\n')
    stub.chmod(0o755)
    for command in ('bash', 'sh', 'hyprctl', 'systemctl', 'foot', 'kitty', 'notify-send', 'wl-copy',
                    'wl-paste', 'matugen', 'gsettings', 'qs', 'xdg-open', 'fish', 'loginctl', 'brightnessctl'):
        (commands / command).symlink_to(stub)
    python = commands / 'python3'
    python.write_text('#!' + sys.executable + '\n' + '''import json, os, runpy, sys
if len(sys.argv)>1 and sys.argv[1].endswith('/preferences.py'):
    if os.environ.get('MODESTY_TEST_SAVE_FAIL') == '1': sys.exit(1)
    sys.argv=sys.argv[1:]
    runpy.run_path(sys.argv[0], run_name='__main__')
elif len(sys.argv)>1 and sys.argv[1].endswith('/terminal_art.py'):
    print(json.dumps([dict(id='portraits/test', title='Test artwork', collection='portraits', preview='')]))
else:
    print(json.dumps(dict(ok=True, configured=False, desktopBindings=[], installed=False)))
''')
    python.chmod(0o755)
    environment.update(PATH=str(commands), MODESTY_PREVIEW='1' if preview else '0',
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                       QS_NO_RELOAD_POPUP='1')
    return environment


QUICKSHELL = shutil.which('qs')


def run(directory, environment, source, marker):
    (Path(directory) / 'shell.qml').write_text(source)
    result = subprocess.run([QUICKSHELL, '--no-color', '-p', str(directory)], env=environment,
                            capture_output=True, text=True, timeout=25)
    output = result.stdout + result.stderr
    if result.returncode or marker not in output or any(error in output for error in (
            'ReferenceError', 'TypeError', 'Error: ', 'is not a function', 'FAIL!')):
        raise AssertionError(output)
    print(marker)


UI = '''import QtQuick
import QtTest
import Quickshell
import "modules/settings" as Settings
import "modules/settings/SettingsCatalog.js" as Catalog
import qs.services
ShellRoot {
    Settings.SettingsWindow {id:settings;implicitWidth:760;implicitHeight:560}
    TestCase {id:input;when:false}
    property int phase:0
    property var root:null
    function check(value,message) {if(!value)throw new Error(message);}
    function child(name) {
        input.tryVerify(()=>!!input.findChild(settings.contentItem,name),3000,"Control did not load "+name);
        return input.findChild(settings.contentItem,name);
    }
    function searchFor(query) {const search=child("settings-search");search.text=query;search.forceActiveFocus();input.keyClick(Qt.Key_Return);}
    function reachable(item) {
        const scroll=child("settings-scroll"),point=item.mapToItem(scroll,0,0);
        check(point.y>=0&&point.y+item.height<=scroll.height+1,"Target outside viewport "+item.objectName+" y="+point.y+" height="+item.height+" viewport="+scroll.height);
    }
    Component.onCompleted:{IslandState.settingsPage="media";IslandState.settingsOpen=true;Preferences.set("motion","instant");}
    Timer {id:steps;interval:180;running:true;repeat:false;onTriggered:{try {
        root=child("settings-root");check(root,"Settings root missing");
        input.tryVerify(()=>!root.pendingTarget,3000,"Pending reveal did not complete");
        check(!root.pendingTarget,"Pending reveal did not complete");
        const search=child("settings-search"),results=child("settings-results");
        if(phase===0){
            Luma.memory="modesty-private-value-sentinel";
            Preferences.set("terminalArtPinned","portraits/modesty-private-value-sentinel");
            Preferences.set("lumaKnowledgeRoots",[Quickshell.env("HOME")+"/modesty-private-value-sentinel"]);
            check(Catalog.search("modesty-private-value-sentinel").length===0,"Private editor values entered search");
            Preferences.set("terminalArtPinned","");
            Catalog.pages.forEach(p=>p.blocks.forEach(b=>b.items.forEach(s=>check(s.kind==="action"||s.service||s.key in Preferences.defaults,"Unclassified control "+s.key))));
            const owners=Catalog.owners(Preferences.defaults);
            for(const key of Object.keys(Preferences.defaults))check(owners[key]?.length===1,"Preference ownership "+key+" "+JSON.stringify(owners[key]));
            check(Catalog.resolve("media","pill","mediaLyrics").page==="music","Media alias failed");
            check(Catalog.resolve("music","capsule","musicMode").key==="liveMedia","Music adapter alias failed");
            check(root.pageId==="music","Initial media page alias failed");
            check(Catalog.resolve("launcher","search","terminal").page==="terminal","Launcher terminal reveal alias failed");
            check(Catalog.resolve("missing")===null,"Unknown page accepted");
            check(Catalog.legacy.join(",")==="layout,clock,appearance,motion,launcher,notifications,controls,lock,connections,shortcuts","Legacy sections changed");
            root.navigate("appearance");check(root.expandedGroups.island&&root.expandedGroups.personal,"First cross-group navigation reset expansion");
            root.navigate("music");root.expandGroup("personal",false);
            const page=root.pageId,back=root.back.length,personal=child("category-personal");
            input.mouseClick(personal);check(root.expandedGroups.personal,"Category click did not expand");
            check(root.expandedGroups.island&&root.pageId===page&&root.back.length===back,"Category click navigated or collapsed sibling");
            personal.forceActiveFocus();input.keyClick(Qt.Key_Left);check(!root.expandedGroups.personal&&root.pageId===page,"Left did not collapse independently");
            input.keyClick(Qt.Key_Right);check(root.expandedGroups.personal&&root.expandedGroups.island,"Right did not expand independently");
            input.keyClick(Qt.Key_Return);check(!root.expandedGroups.personal&&root.pageId===page,"Keyboard category click navigated");
            input.findChild(settings,"settings-ipc").reveal("media","pill","mediaLyrics");
        }else if(phase===1){
            check(root.pageId==="music"&&child("control-mediaLyrics").activeFocus,"Alias target lacks focus");
            reachable(child("control-mediaLyrics"));
            input.keyClick(Qt.Key_F,Qt.ControlModifier);check(search.activeFocus,"Ctrl+F did not focus search");
            search.text="privacy";check(root.results.length>=3,"Multiple search matches missing");
            input.keyClick(Qt.Key_Down);check(results.currentIndex===1,"Search Down failed");
            input.keyClick(Qt.Key_Up);check(results.currentIndex===0,"Search Up failed");
            search.text="no-settings-match-zzzz";input.keyClick(Qt.Key_Down);input.keyClick(Qt.Key_Up);
            check(root.results.length===0&&results.currentIndex===0,"Empty search escaped bounds");
            input.keyClick(Qt.Key_Return);check(root.pageId==="music","Empty search navigated");
            input.keyClick(Qt.Key_Escape);check(!search.text&&IslandState.settingsOpen,"Escape did not clear search");
            searchFor("Favorites only");
        }else if(phase===2){
            check(root.pageId==="terminal"&&root.expandedGroups.apps,"Custom navigation did not open destination group");
            const favorite=child("Favorites only");check(favorite&&favorite.activeFocus,"Exact favorites control lacks focus");reachable(favorite);
            searchFor("Minimal greeting");
        }else if(phase===3){
            const minimal=child("Minimal greeting");check(minimal.activeFocus,"Exact minimal control lacks focus");reachable(minimal);
            Preferences.set("terminalGreeting",false);searchFor("Artwork size");
        }else if(phase===4){
            check(child("Show artwork").activeFocus&&!Preferences.terminalGreeting,"Artwork prerequisite did not focus or auto-enabled");reachable(child("Show artwork"));
            Preferences.set("terminalGreeting",true);input.findChild(settings,"settings-ipc").artwork();
        }else if(phase===5){
            check(child("custom-gallery").activeFocus,"Gallery target lacks focus");reachable(child("custom-gallery"));
            searchFor("Save notes");
        }else if(phase===6){
            check(child("custom-save-notes").activeFocus,"Save notes target lacks focus");reachable(child("custom-save-notes"));
            searchFor("Delete all conversations");
        }else if(phase===7){
            check(child("custom-delete-conversations").activeFocus,"Delete conversations target lacks focus");reachable(child("custom-delete-conversations"));
            searchFor("Gemini API key");
        }else if(phase===8){
            check(child("custom-gemini").activeFocus,"Provider input lacks focus");reachable(child("custom-gemini"));
            Preferences.set("lumaAutoAnswer",false);searchFor("Typing pause");
        }else if(phase===9){
            const setting=child("setting-lumaAnswerDelay"),jump=child("prerequisite-lumaAnswerDelay");
            check(setting.visible&&!setting.available&&jump.activeFocus,"Unavailable row or prerequisite missing");
            check(!child("control-lumaAnswerDelay").enabled&&!Preferences.lumaAutoAnswer,"Search enabled dependent feature");reachable(jump);
            input.mouseClick(jump);
        }else if(phase===10){
            check(child("control-lumaAutoAnswer").activeFocus&&!Preferences.lumaAutoAnswer,"Prerequisite jump failed or enabled feature");
            root.navigate("status","privacy","privacyIndicatorGap");
        }else if(phase===11){
            const slider=child("control-privacyIndicatorGap");check(slider.activeFocus,"Privacy gap lacks focus");reachable(slider);
            const before=Preferences.privacyIndicatorGap;input.keyClick(Qt.Key_Right);check(Preferences.privacyIndicatorGap===before+1,"Privacy slider did not write");
            root.navigate("status","privacy","privacyIndicatorRightPadding");
        }else if(phase===12){
            const slider=child("control-privacyIndicatorRightPadding");check(slider.activeFocus,"Privacy padding lacks focus");reachable(slider);
            const before=Preferences.privacyIndicatorRightPadding;input.keyClick(Qt.Key_Left);check(Preferences.privacyIndicatorRightPadding===before-1,"Padding slider did not write");
            Preferences.saveError="Test visible save error";
            root.navigate("shortcuts","shortcuts","search-shortcuts");
        }else if(phase===13){
            check(child("custom-search-shortcuts").activeFocus,"Shortcuts target lacks focus");reachable(child("custom-search-shortcuts"));
            check(child("preferences-save-error").visible&&child("preferences-save-error").text==="Test visible save error","Save error no longer visible");
            check(Catalog.search("rollback").some(t=>t.key==="rollback"),"Rollback not searchable");
            check(Catalog.search("knowledge folder").some(t=>t.key==="folders"),"Knowledge folders not searchable");
            check(Catalog.search("local voice").some(t=>t.key==="setup"),"Voice setup not searchable");
            Preferences.set("terminalArtFormat","image");searchFor("Artwork palette");
        }else if(phase===14){
            check(child("custom-format-ascii").activeFocus&&!child("custom-palette").enabled&&child("custom-palette").visible,"ASCII prerequisite not focused or palette not visible");
            check(Preferences.terminalArtFormat==="image","Palette search changed format");reachable(child("custom-format-ascii"));
            root.navigate("launcher","search","terminal");
        }else if(phase===15){
            check(root.pageId==="terminal"&&root.highlight==="terminal","Legacy terminal selector reveal failed");
            check(Catalog.owners(Preferences.defaults).terminal[0].page==="terminal","Terminal choice owner wrong");
            root.navigate("clock");
        }else if(phase===16){
            input.mouseClick(child("settings-back"));
        }else if(phase===17){
            check(root.pageId==="terminal","Back navigation failed");input.mouseClick(child("settings-forward"));
        }else if(phase===18){
            check(root.pageId==="clock","Forward navigation failed");
            root.navigate("luma-voice","installation","setup");
        }else if(phase===19){
            check(child("custom-setup-prerequisite").activeFocus,"Voice unavailable prerequisite lacks focus");reachable(child("custom-setup-prerequisite"));
            root.navigate("updates","updates","rollback");
        }else if(phase===20){
            check(child("custom-updates-status").activeFocus,"Update unavailable prerequisite lacks focus");reachable(child("custom-updates-status"));
            console.log("SETTINGS UI PASS");Qt.quit();return;
        }
        phase++;steps.restart();
    }catch(error){console.error("Phase "+phase+" "+error+" page="+root?.pageId+" pending="+JSON.stringify(root?.pendingTarget)+" searching="+root?.searching);Qt.exit(1);}}}
}
'''

PERSISTENCE = '''import QtQuick
import QtTest
import Quickshell
import "modules/settings" as Settings
import "modules/settings/SettingsCatalog.js" as Catalog
import qs.services
ShellRoot {
    FloatingWindow {
        visible:true;implicitWidth:500;implicitHeight:200
        Settings.SettingRow {id:row;anchors.fill:parent;setting:Catalog.page("status").blocks.find(b=>b.id==="privacy").items.find(s=>s.key==="privacyIndicatorGap")}
        TestCase {id:input;when:false}
    }
    property int phase:0
    Timer {id:steps;interval:300;running:true;repeat:false;onTriggered:{try {
        if(phase===0){
            if(Preferences.preview)throw new Error("Persistence test accidentally preview");
            ACTION
        }else if(phase===4){
            ASSERTION
            console.log("MARKER");Qt.quit();return;
        }
        phase++;steps.restart();
    }catch(error){console.error("Phase "+phase+" "+error);Qt.exit(1);}}}
}
'''


def main():
    with tempfile.TemporaryDirectory(prefix='modesty-settings-ui-') as directory:
        environment = workspace(directory)
        run(directory, environment, UI, 'SETTINGS UI PASS')
    with tempfile.TemporaryDirectory(prefix='modesty-settings-persistence-') as directory:
        environment = workspace(directory, preview=False)
        source = PERSISTENCE.replace('ACTION', 'row.reveal().forceActiveFocus();input.keyClick(Qt.Key_Right);').replace(
            'ASSERTION', 'if(Preferences.privacyIndicatorGap!==26||Preferences.saveError)throw new Error("Real writer failed");').replace('MARKER', 'SETTINGS WRITE PASS')
        run(directory, environment, source, 'SETTINGS WRITE PASS')
        stored = Path(environment['XDG_STATE_HOME']) / 'modesty/preferences.json'
        assert json.loads(stored.read_text())['privacyIndicatorGap'] == 26
        source = PERSISTENCE.replace('ACTION', '').replace('ASSERTION',
            'if(Preferences.privacyIndicatorGap!==26)throw new Error("Restart did not restore saved value");').replace('MARKER', 'SETTINGS RESTART PASS')
        run(directory, environment, source, 'SETTINGS RESTART PASS')
        environment['MODESTY_TEST_SAVE_FAIL'] = '1'
        source = PERSISTENCE.replace('ACTION', 'row.reveal().forceActiveFocus();input.keyClick(Qt.Key_Right);').replace(
            'ASSERTION', 'if(Preferences.saveError!=="Couldn\\\'t save your preferences")throw new Error("Save failure missing");').replace('MARKER', 'SETTINGS SAVE ERROR PASS')
        run(directory, environment, source, 'SETTINGS SAVE ERROR PASS')
        assert json.loads(stored.read_text())['privacyIndicatorGap'] == 26


if __name__ == '__main__':
    main()
