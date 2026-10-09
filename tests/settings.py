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
elif os.environ.get('MODESTY_TEST_EDITOR_CALLS') and len(sys.argv)>2 and sys.argv[1].endswith(('/command-canvas.py', '/luma-assistant.py')):
    from pathlib import Path
    audit=Path(os.environ['MODESTY_TEST_EDITOR_CALLS'])
    keys=audit.with_suffix('.keys')
    configured=set(json.loads(keys.read_text())) if keys.exists() else {'gemini', 'jev'}
    command=sys.argv[2:]
    payload=sys.stdin.readline().rstrip('\\n') if command[0] in ('key-set', 'memory') else None
    if command[0] in ('key-set', 'key-clear'):
        if command[0]=='key-set': configured.add(command[1])
        else: configured.discard(command[1])
        keys.write_text(json.dumps(sorted(configured)))
    with audit.open('a') as file:
        file.write(json.dumps(dict(command=command, payload=payload))+'\\n')
    print(json.dumps(dict(ok=True, configured=len(command)>1 and command[1] in configured,
                          memory='initial-saved-memory-sentinel' if command[0]=='state' else '')))
else:
    print(json.dumps(dict(ok=True, configured=False, desktopBindings=[], installed=False, items=[])))
''')
    python.chmod(0o755)
    environment.update(PATH=str(commands), MODESTY_PREVIEW='1' if preview else '0',
                       QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                       QS_NO_RELOAD_POPUP='1')
    environment.setdefault('QT_QUICK_CONTROLS_STYLE', 'Basic')
    environment['QT_QPA_PLATFORMTHEME'] = 'generic'
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
    print(marker + output.split(marker, 1)[1].splitlines()[0])


UI = '''import QtQuick
import QtTest
import Quickshell
import "modules/settings" as Settings
import "modules/settings/SettingsCatalog.js" as Catalog
import qs.services
import qs.theme
ShellRoot {
    Settings.SettingsWindow {id:settings;implicitWidth:760;implicitHeight:560}
    TestCase {id:input;when:false}
    property int phase:0
    property var root:null
    property var targets:[]
    property int targetIndex:0
    function check(value,message) {if(!value)throw new Error(message);}
    function child(name) {
        input.tryVerify(()=>!!input.findChild(settings.contentItem,name),3000,"Control did not load "+name);
        return input.findChild(settings.contentItem,name);
    }
    function searchFor(query) {const search=child("settings-search");search.text=query;search.forceActiveFocus();input.keyClick(Qt.Key_Return);}
    function reachable(item) {
        const scroll=child("settings-scroll");
        let ancestor=item.parent;
        while(ancestor&&ancestor!==scroll){if(ancestor.clip&&ancestor.height<item.height)item=ancestor;ancestor=ancestor.parent;}
        const point=item.mapToItem(scroll,0,0);
        check(point.y>=0&&point.y+item.height<=scroll.height+1,"Target outside viewport "+item.objectName+" y="+point.y+" height="+item.height+" viewport="+scroll.height);
    }
    Component.onCompleted:{Theme.setMode("TEST_MODE");IslandState.settingsPage="media";IslandState.settingsOpen=true;Preferences.set("motion","instant");}
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
            const title=child("settings-page-title"),titleX=title.x;
            root.navigate("appearance");child("page-motion").forceActiveFocus();input.keyClick(Qt.Key_Space);check(root.pageId==="motion","Keyboard page tab failed");root.navigate("music");
            input.mouseClick(child("category-personal"));check(root.pageId==="motion","Category did not remember page");
            input.mouseClick(child("category-island"));check(root.pageId==="music","Island did not remember page");
            root.lastPages=Object.assign({},root.lastPages,{system:"missing"});
            const system=child("category-system");system.forceActiveFocus();input.keyClick(Qt.Key_Space);
            check(root.pageId==="connections","Invalid remembered page did not fall back");
            check(title.x===titleX,"History buttons shifted title");
            root.navigate("music");
            check(child("page-music").visible&&!input.findChild(settings.contentItem,"page-motion"),"Tabs include another category");
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
            check(root.pageId==="terminal"&&root.current.group==="apps","Custom navigation did not open destination group");
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
            check(!child("custom-save-notes").enabled&&child("custom-notes").activeFocus,"Preview Save notes reveal lacks notes focus");reachable(child("custom-notes"));
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
            root.navigate("companion","character","companionSide");
        }else if(phase===21){
            const choice=child("control-companionSide"),before=Preferences.companionSide;
            check(choice.activeFocus,"ComboBox reveal lacks focus");reachable(choice);
            input.keyClick(Qt.Key_Space);input.tryVerify(()=>choice.popup.visible,1000,"Space did not open ComboBox");
            input.keyClick(before==="left"?Qt.Key_Down:Qt.Key_Up);input.keyClick(Qt.Key_Return);
            check(!choice.popup.visible&&Preferences.companionSide!==before,"ComboBox selection did not write or close");
            input.keyClick(Qt.Key_Space);input.tryVerify(()=>choice.popup.visible,1000,"ComboBox did not reopen");
            input.keyClick(Qt.Key_Escape);check(!choice.popup.visible&&IslandState.settingsOpen,"Escape closed Settings instead of ComboBox");
            Preferences.set("matugenAutomatic",false);root.navigate("appearance","palette","matugenScheme");
        }else if(phase===22){
            const choice=child("control-matugenScheme");
            input.keyClick(Qt.Key_Space);input.tryVerify(()=>choice.popup.visible,1000,"Long ComboBox did not open");
            const list=choice.popup.contentItem;
            input.tryVerify(()=>list.count===10,1000,"ComboBox options missing");
            const option=input.findChild(list,"option-matugenScheme-0"),bar=input.findChild(list,"settings-scrollbar");
            const popupPosition=list.mapToItem(settings.contentItem,0,0);
            check(popupPosition.x>=0&&popupPosition.y>=0&&popupPosition.x+list.width<=settings.contentItem.width&&popupPosition.y+list.height<=settings.contentItem.height,"Popup outside window");
            check(option.Accessible.selected===(choice.currentIndex===0),"Popup selected state wrong");
            check(option.width<=bar.x-2,"Popup scrollbar overlaps options");
            input.keyClick(Qt.Key_End);input.keyClick(Qt.Key_Return);
            check(Preferences.matugenScheme==="scheme-smart"&&!choice.popup.visible,"End/Return selection failed");
            Luma.memory=Array(100).fill("Long notes must remain readable while editing and selecting text.").join("\\n");
            root.navigate("luma-providers","providers","notes");
        }else if(phase===23){
            const notes=child("custom-notes"),view=child("custom-notes-viewport"),bar=input.findChild(view,"settings-scrollbar")||input.findChild(view.parent,"settings-scrollbar");
            check(notes.activeFocus,"Notes reveal lacks focus");reachable(notes);
            check(view.x+view.width<=bar.x-4,"Notes scrollbar overlaps text editor");
            input.keyClick(Qt.Key_End,Qt.ControlModifier);
            input.tryVerify(()=>view.contentY>0,1000,"Notes did not scroll to keyboard cursor");
            const cursor=notes.mapToItem(view,notes.cursorRectangle.x,notes.cursorRectangle.y);
            check(cursor.y>=0&&cursor.y+notes.cursorRectangle.height<=view.height+1,"Notes cursor outside editor viewport");
            targets=[];Catalog.pages.forEach(p=>p.blocks.forEach(b=>b.items.concat(b.targets.map(t=>({key:t.id,label:t.label}))).forEach(t=>targets.push({page:p.id,block:b.id,key:t.key,label:t.label}))));
            check(targets.length>=176,"Catalog target sweep lost coverage");
            targetIndex=0;steps.interval=30;root.navigate(targets[0].page,targets[0].block,targets[0].key);
        }else{
            const target=targets[targetIndex];
            check(root.pageId===target.page,"Sweep page wrong "+JSON.stringify(target));
            const cards=child("settings-page-content").item.cards;
            let destination=null;
            for(let i=0;i<cards.count;i++){
                const card=cards.itemAt(i);
                if(card.modelData.id!==target.block)continue;
                destination=card.modelData.custom?card.editor.item.reveal(target.key):child("setting-"+target.key).reveal();
            }
            check(destination&&destination.activeFocus&&root.focusedItem===destination,"Sweep exact target lacks focus "+JSON.stringify(target));
            reachable(root.focusedItem);
            check(Catalog.search(target.label).some(r=>r.page===target.page&&r.block===target.block&&r.key===target.key),"Sweep target not searchable "+JSON.stringify(target));
            const scroll=child("settings-scroll"),page=child("settings-page-content"),bar=input.findChild(scroll,"settings-scrollbar");
            check(page.width<=bar.x-4,"Main scrollbar overlaps content on "+target.page);
            const navigation=child("settings-navigation"),nav=child("settings-navigation-content"),navBar=input.findChild(navigation,"settings-scrollbar");
            check(nav.width<=navBar.x-4,"Navigation scrollbar overlaps categories");
            if(++targetIndex===targets.length){
                search.text="a";
                const result=child("settings-result-0"),resultBar=input.findChild(results,"settings-scrollbar");
                check(result.width<=resultBar.x-4,"Search scrollbar overlaps results");
                console.log("SETTINGS UI PASS "+targets.length+" targets");Qt.quit();return;
            }
            root.navigate(targets[targetIndex].page,targets[targetIndex].block,targets[targetIndex].key);
        }
        phase++;steps.restart();
    }catch(error){console.error("Phase "+phase+" "+error+" page="+root?.pageId+" pending="+JSON.stringify(root?.pendingTarget)+" searching="+root?.searching);Qt.exit(1);}}}
}
'''

DRAFTS = '''import QtQuick
import QtTest
import Quickshell
import "modules/settings" as Settings
import "modules/settings/SettingsCatalog.js" as Catalog
import qs.services
ShellRoot {
    id:shell
    Component {id:windowComponent;Settings.SettingsWindow {implicitWidth:760;implicitHeight:560}}
    property var settings:null
    property int phase:0
    property var root:null
    TestCase {id:input;when:false}
    function check(value,message) {if(!value)throw new Error(message);}
    function child(name) {
        input.tryVerify(()=>!!input.findChild(settings.contentItem,name),3000,"Control did not load "+name);
        return input.findChild(settings.contentItem,name);
    }
    function edit(name,value) {
        root.focusTarget(child(name));input.keyClick(Qt.Key_A,Qt.ControlModifier);
        if(!value)input.keyClick(Qt.Key_Backspace);
        for(let i=0;i<value.length;i++)input.keyClick(value[i]);
        check(child(name).text===value,"Native edit failed "+name);
    }
    function keyButton(provider,label) {return child("custom-"+provider).parent.children.find(item=>item.text===label);}
    function clickKey(provider,label) {
        const button=keyButton(provider,label);
        input.tryVerify(()=>button.visible&&button.enabled,3000,"Key action unavailable "+provider+" "+label);
        root.focusTarget(button);input.keyClick(Qt.Key_Space);
        input.tryVerify(()=>keyButton(provider,"Remove").enabled,3000,"Key operation did not finish "+provider);
    }
    function retained(notes,gemini,jev) {
        check(child("custom-notes").text===notes,"Unsaved notes lost");
        check(child("custom-gemini").text===gemini,"Gemini draft lost or reappeared");
        check(child("custom-jev").text===jev,"Jev draft lost or reappeared");
    }
    Component.onCompleted:{
        IslandState.settingsPage="luma-providers";IslandState.settingsOpen=true;
        Preferences.set("motion","instant");settings=windowComponent.createObject(shell);
    }
    Timer {id:steps;interval:180;running:true;repeat:false;onTriggered:{try {
        root=child("settings-root");
        input.tryVerify(()=>!root.pendingTarget,3000,"Pending reveal did not complete");
        if(phase===0){
            input.tryVerify(()=>Luma.loaded,3000,"Initial memory load did not finish");
            check(child("custom-notes").text==="initial-saved-memory-sentinel","Initial async saved notes did not load");
            Luma.memory="saved-note-sentinel";
            check(child("custom-notes").text===Luma.memory,"Untouched notes ignored backend load");
            edit("custom-notes","modesty-unsaved-notes-sentinel");
            edit("custom-gemini","modesty-gemini-draft-sentinel");
            edit("custom-jev","modesty-jev-draft-sentinel");
            for(const value of ["modesty-unsaved-notes-sentinel","modesty-gemini-draft-sentinel","modesty-jev-draft-sentinel"])
                check(Catalog.search(value).length===0,"Editor draft entered search");
            input.mouseClick(child("page-luma-knowledge"));
        }else if(phase===1){
            input.mouseClick(child("page-luma-providers"));
        }else if(phase===2){
            retained("modesty-unsaved-notes-sentinel","modesty-gemini-draft-sentinel","modesty-jev-draft-sentinel");
            input.mouseClick(child("category-personal"));
        }else if(phase===3){
            input.mouseClick(child("category-assistant"));
        }else if(phase===4){
            retained("modesty-unsaved-notes-sentinel","modesty-gemini-draft-sentinel","modesty-jev-draft-sentinel");
            Luma.memory="later-backend-note-sentinel";
            check(child("custom-notes").text==="modesty-unsaved-notes-sentinel","Backend update overwrote note draft");
            edit("custom-notes","");Luma.memory="saved-memory-that-must-not-return";
            check(child("custom-notes").text==="","Backend update replaced intentional empty draft");
            input.mouseClick(child("page-luma-knowledge"));
        }else if(phase===5){
            input.mouseClick(child("category-apps"));
        }else if(phase===6){
            input.mouseClick(child("category-assistant"));input.mouseClick(child("page-luma-providers"));
        }else if(phase===7){
            retained("","modesty-gemini-draft-sentinel","modesty-jev-draft-sentinel");
            const search=child("settings-search");search.text="modesty-gemini-draft-sentinel";search.forceActiveFocus();
            check(root.results.length===0,"Draft appeared in search results");input.keyClick(Qt.Key_Escape);
        }else if(phase===8){
            retained("","modesty-gemini-draft-sentinel","modesty-jev-draft-sentinel");
            clickKey("gemini","Save");
            check(child("custom-gemini").text===""&&child("custom-jev").text==="modesty-jev-draft-sentinel","Save cleared wrong provider draft");
            input.mouseClick(child("page-luma-knowledge"));
        }else if(phase===9){
            input.mouseClick(child("page-luma-providers"));
        }else if(phase===10){
            retained("","","modesty-jev-draft-sentinel");
            edit("custom-gemini","modesty-gemini-remove-sentinel");clickKey("gemini","Remove");
            check(child("custom-gemini").text==="","Remove did not clear Gemini input");
            edit("custom-notes","notes-to-save-sentinel");
            root.focusTarget(child("custom-save-notes"));input.keyClick(Qt.Key_Space);
            check(Luma.memory==="notes-to-save-sentinel","Explicit note Save failed");
            input.mouseClick(child("page-luma-knowledge"));
        }else if(phase===11){
            input.mouseClick(child("page-luma-providers"));
        }else if(phase===12){
            retained("notes-to-save-sentinel","","modesty-jev-draft-sentinel");
            Luma.memory="after-save-backend-note-sentinel";
            check(child("custom-notes").text===Luma.memory,"Saved note draft blocked later backend update");
            clickKey("jev","Save");edit("custom-gemini","modesty-window-gemini-sentinel");
            edit("custom-jev","modesty-jev-remove-sentinel");clickKey("jev","Remove");
            check(child("custom-jev").text===""&&child("custom-gemini").text==="modesty-window-gemini-sentinel","Remove cleared wrong provider draft");
            edit("custom-notes","notes-to-clear-sentinel");
            root.focusTarget(child("custom-clear-notes"));input.keyClick(Qt.Key_Space);
            check(Luma.memory===""&&child("custom-notes").text==="","Explicit note Clear failed");
            input.mouseClick(child("page-luma-knowledge"));
        }else if(phase===13){
            input.mouseClick(child("page-luma-providers"));
        }else if(phase===14){
            retained("","modesty-window-gemini-sentinel","");
            Luma.memory="new-backend-note-sentinel";
            check(child("custom-notes").text===Luma.memory,"Cleared note draft blocked later backend load");
            edit("custom-notes","modesty-window-notes-sentinel");edit("custom-jev","modesty-window-jev-sentinel");
            settings.destroy();settings=null;
            Qt.callLater(()=>{IslandState.settingsOpen=true;settings=windowComponent.createObject(shell);});
        }else if(phase===15){
            retained("new-backend-note-sentinel","","");
            console.log("SETTINGS DRAFT PASS");Qt.quit();return;
        }
        phase++;steps.restart();
    }catch(error){console.error("Draft phase "+phase+" "+error);Qt.exit(1);}}}
}
'''

PREVIEW_DRAFTS = '''import QtQuick
import QtTest
import Quickshell
import "modules/settings" as Settings
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
    function edit(value) {
        root.focusTarget(child("custom-notes"));input.keyClick(Qt.Key_A,Qt.ControlModifier);
        input.keyClick(Qt.Key_Backspace);
        for(let i=0;i<value.length;i++)input.keyClick(value[i]);
        check(child("custom-notes").text===value,"Native preview note edit failed");
    }
    function retained(value) {
        check(child("custom-notes").text===value,"Rejected preview action lost note draft");
        check(Luma.memory==="saved-note-sentinel","Rejected preview action changed saved memory");
    }
    function rejectActions(value) {
        for(const name of ["custom-save-notes","custom-clear-notes"]){
            const action=child(name);
            action.clicked();retained(value);
            check(!action.enabled,"Note action enabled in preview "+name);
        }
    }
    Component.onCompleted:{IslandState.settingsPage="luma-providers";IslandState.settingsOpen=true;Preferences.set("motion","instant");}
    Timer {id:steps;interval:180;running:true;repeat:false;onTriggered:{try {
        root=child("settings-root");
        input.tryVerify(()=>!root.pendingTarget,3000,"Pending reveal did not complete");
        if(phase===0){
            check(Preferences.preview,"Preview regression accidentally writable");
            Luma.memory="saved-note-sentinel";edit("unsaved-note-sentinel");rejectActions("unsaved-note-sentinel");
            root.navigate("luma-knowledge");
        }else if(phase===1){
            root.navigate("luma-providers","providers","save-notes");
        }else if(phase===2){
            retained("unsaved-note-sentinel");check(child("custom-notes").activeFocus,"Preview Save reveal did not focus notes");
            edit("");rejectActions("");root.navigate("luma-knowledge");
        }else if(phase===3){
            root.navigate("luma-providers","providers","clear-notes");
        }else if(phase===4){
            retained("");check(child("custom-notes").activeFocus,"Preview Clear reveal did not focus notes");
            console.log("SETTINGS PREVIEW DRAFT PASS");Qt.quit();return;
        }
        phase++;steps.restart();
    }catch(error){console.error("Preview draft phase "+phase+" "+error);Qt.exit(1);}}}
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


def test_drafts():
    with tempfile.TemporaryDirectory(prefix='modesty-settings-drafts-') as directory:
        environment = workspace(directory, preview=False)
        audit = Path(directory) / 'editor-calls.jsonl'
        environment['MODESTY_TEST_EDITOR_CALLS'] = str(audit)
        run(directory, environment, DRAFTS, 'SETTINGS DRAFT PASS')
        calls = [json.loads(line) for line in audit.read_text().splitlines()]
        key_writes = [call for call in calls if call['command'][0] in ('key-set', 'key-clear')]
        expected_key_writes = [
            dict(command=['key-set', 'gemini'], payload='modesty-gemini-draft-sentinel'),
            dict(command=['key-clear', 'gemini'], payload=None),
            dict(command=['key-set', 'jev'], payload='modesty-jev-draft-sentinel'),
            dict(command=['key-clear', 'jev'], payload=None),
        ]
        assert key_writes == expected_key_writes, (
            f'Navigation or editing caused unintended key writes: actual={key_writes!r}, expected={expected_key_writes!r}')
        note_writes = [json.loads(call['payload']) for call in calls if call['command'][0] == 'memory']
        expected_note_writes = ['notes-to-save-sentinel', '']
        assert note_writes == expected_note_writes, (
            f'Notes wrote without explicit Save or Clear: actual={note_writes!r}, expected={expected_note_writes!r}')
        assert all(call['command'][0] in ('state', 'usage', 'key-status', 'key-set', 'key-clear', 'memory')
                   for call in calls), 'Editor caused an unexpected backend operation'


def test_preview_drafts():
    with tempfile.TemporaryDirectory(prefix='modesty-settings-preview-drafts-') as directory:
        environment = workspace(directory)
        audit = Path(directory) / 'editor-calls.jsonl'
        environment['MODESTY_TEST_EDITOR_CALLS'] = str(audit)
        run(directory, environment, PREVIEW_DRAFTS, 'SETTINGS PREVIEW DRAFT PASS')
        calls = [json.loads(line) for line in audit.read_text().splitlines()] if audit.exists() else []
        assert not any(call['command'][0] == 'memory' for call in calls), 'Preview note action wrote to backend'


def main():
    test_drafts()
    test_preview_drafts()
    for width, height, mode in ((760, 560, 'dark'), (960, 720, 'light')):
        with tempfile.TemporaryDirectory(prefix='modesty-settings-ui-') as directory:
            environment = workspace(directory)
            source = UI.replace('implicitWidth:760;implicitHeight:560', f'implicitWidth:{width};implicitHeight:{height}').replace('TEST_MODE', mode)
            run(directory, environment, source, 'SETTINGS UI PASS')
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
