#!/usr/bin/env python3
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import qml
from qml import run

BOUNDS = '''import QtQuick
import Quickshell
import "modules/island" as Island
import qs.components
import qs.services
ShellRoot {
    property int profile:0
    property int phase:0
    property var profiles:[{width:800,scale:1},{width:1024,scale:1.25},{width:640,scale:1},{width:640,scale:1.25},{width:800,scale:.9,user:true},{width:1920,scale:.9,user:true}]
    property var panels:["quicksettings","media","wifi","none"]
    FloatingWindow {visible:true;implicitWidth:1200;implicitHeight:700
        Island.IslandSurface {id:surface;availableWidth:profiles[profile].width;availableHeight:600}
    }
    function check(ok,label):void {if(!ok)throw new Error(label+" profile="+profile+" panel="+IslandState.menu);}
    function walk(item) {let items=[item];for(const child of item.children||[])items=items.concat(walk(child));return items;}
    function configure():void {
        const p=profiles[profile];Preferences.uiScale=p.scale;Preferences.barHeight=p.user?35:33;
        Preferences.collapsedWidth=p.user?105:90;Preferences.clusterGap=p.user?8:14;
        IslandState.openMenu("quicksettings");
    }
    Component.onCompleted:{Preferences.motion="instant";Preferences.mediaAutoHide=false;configure();}
    Timer {interval:180;running:true;repeat:true;onTriggered:{try {
        const margin=16/Preferences.uiScale;
        for(const stage of [surface.mediaStage,surface.controlStage]) {
            if(!stage.visible)continue;
            check(stage.x>=margin-.01,"Side stage crosses left margin x="+stage.x);
            check(stage.x+stage.width<=surface.width-margin+.01,"Side stage crosses right margin edge="+(stage.x+stage.width));
            check(stage.targetWidth<=stage.maximumWidth+.01,"Target exceeds side budget");
            for(const pane of stage.diagnostics().entries.filter(p=>p.selected)) {
                check(pane.width<=Math.max(0,stage.maximumWidth-Preferences.innerPadding*2)+.01,"Panel exceeds side budget width="+pane.width);
                check(pane.height<=Math.max(0,surface.maximumHeight-Preferences.innerPadding*2)+.01,"Panel exceeds height budget");
                check(pane.status===1&&pane.opacity>.99&&pane.enabled,"Selected panel stays hidden");
            }
        }
        const label=walk(surface).find(item=>item instanceof RollingText&&item.text===Time.timeStr);
        check(!!label,"Clock text missing");
        const center=label.mapToItem(surface,label.width/2,0).x;
        check(Math.abs(center-surface.width/2)<.01,"Time moved away from screen center "+center);
        check(surface.clockStage.height===Preferences.barHeight,"Side panel changes resting clock height");
        phase++;
        if(phase===panels.length){phase=0;if(profile+1===profiles.length){console.log("ISLAND BOUNDS PASS");Qt.quit();return;}profile++;configure();}
        else if(panels[phase]==="none")IslandState.closeMenu();else IslandState.openMenu(panels[phase]);
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

SCROLL = '''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
ShellRoot {
    property int phase:0
    property int detailIndex:0
    property var details:["wifi","bluetooth","display","sound","notifhistory","recorder","focus","performance"]
    property var chosen
    FloatingWindow {visible:true;implicitWidth:800;implicitHeight:600
        Island.IslandSurface {id:surface;availableWidth:640;availableHeight:300}
    }
    TestCase {id:input;when:false}
    function check(ok,label):void {if(!ok)throw new Error(label+" phase="+phase+" detail="+details[detailIndex]);}
    function walk(item) {let items=item?[item]:[];for(const child of item?.children||[])items=items.concat(walk(child));return items;}
    function child(name) {return input.findChild(surface.controlStage,name);}
    function inside(item,viewport):void {
        const p=item.mapToItem(viewport,0,0);
        check(p.x>=-.1&&p.y>=-.1&&p.x+Math.min(item.width,viewport.width)<=viewport.width+.1&&p.y+Math.min(item.height,viewport.height)<=viewport.height+.1,"Focused control stays outside viewport "+(item.text||item.label||item.kind)+" x="+p.x+" y="+p.y);
    }
    Component.onCompleted:{Preferences.motion="instant";Preferences.footerTray=false;IslandState.openMenu("quicksettings");}
    Timer {id:steps;interval:180;running:true;onTriggered:{try {
        const overview=child("controlOverview");
        if(phase===0) {
            check(!!overview,"Narrow overview has no scroll viewport");
            check(overview.contentWidth>overview.width&&overview.contentHeight>overview.height,"Narrow short overview does not scroll");
            const tiles=walk(overview).filter(item=>item.usable!==undefined&&item.kind!==undefined);
            check(tiles.length===ControlLayout.items.length,"Configured controls missing");
            check(tiles.every(tile=>tile.width>=40&&tile.height>=40),"Control shrinks below usable size");
            input.mouseWheel(overview,overview.width/2,overview.height/2,-120,0);
            input.tryVerify(()=>overview.contentX>0,1000,"Horizontal wheel does not scroll");
            check(overview.contentX>0,"Horizontal scroll leaves controls unreachable");
            chosen=child("footerSettings");chosen.forceActiveFocus();
        } else if(phase===1) {
            inside(chosen,overview);input.keyClick(Qt.Key_Tab);chosen=child("footerPerformance");
            check(chosen.activeFocus,"Tab misses footer Performance");
        } else if(phase===2) {
            inside(chosen,overview);overview.forceActiveFocus();input.keyClick(Qt.Key_End);
            check(Math.abs(overview.contentY-overview.contentHeight+overview.height)<.1,"End misses short overview footer");
            input.keyClick(Qt.Key_Home);check(overview.contentY===0,"Home misses first row");
            IslandState.openMenu(details[detailIndex]);
        } else if(phase===3) {
            const center=overview.parent;
            const state=center.diagnostics(),selected=state.panes.find(p=>p.selected);
            check(state.modal&&!state.backgroundEnabled,"Detail does not block overview");
            check(!!selected&&selected.status===1&&selected.opacity>.99&&selected.enabled,"Short detail never reveals");
            const pane=walk(center).find(item=>item.modelData===details[detailIndex]&&item.selected&&item.item);
            const viewport=child("controlDetailViewport");
            check(!!viewport&&viewport.contentWidth>=280&&viewport.contentWidth>viewport.width,"Narrow detail has no horizontal scroll");
            const controls=walk(pane.item).filter(item=>item.visible&&item.enabled&&((item.focusPolicy??Qt.NoFocus)!==Qt.NoFocus||item.activeFocusOnTab));
            chosen=controls.sort((a,b)=>b.mapToItem(viewport,0,0).x+b.width-a.mapToItem(viewport,0,0).x-a.width)[0];
            check(!!chosen,"Detail has no keyboard control");chosen.forceActiveFocus();
            if(details[detailIndex]==="focus"||details[detailIndex]==="recorder") {
                chosen=controls.find(item=>item.text===(details[detailIndex]==="focus"?"Start focus":"Open recordings folder"));
                check(!!chosen,"Bottom action missing");chosen.forceActiveFocus();
            }
        } else if(phase===4) {
            const viewport=child("controlDetailViewport");inside(chosen,viewport);
            if(details[detailIndex]==="focus"||details[detailIndex]==="recorder")check(viewport.contentHeight>viewport.height&&viewport.contentY>0,"Fixed detail bottom action cannot scroll into view");
            const back=walk(viewport).find(item=>item.label==="Control center"&&item.visible);
            check(!!back,"Detail back action missing");back.forceActiveFocus();chosen=back;
        } else if(phase===5) {
            const viewport=child("controlDetailViewport");inside(chosen,viewport);
            input.keyClick(Qt.Key_Return);check(IslandState.menu==="quicksettings","Visible detail back action blocked");
            detailIndex++;if(detailIndex===details.length){console.log("ISLAND SCROLL PASS");Qt.quit();return;}
        } else if(phase===6) {IslandState.openMenu(details[detailIndex]);phase=2;}
        phase++;steps.restart();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

PRIVACY = '''import QtQuick
import Quickshell
import "modules/island" as Island
import qs.components
import qs.services
ShellRoot {
    property int phase:0
    FloatingWindow {id:window;visible:true;implicitWidth:900;implicitHeight:300
        Island.IslandSurface {id:surface;availableWidth:900;scale:Preferences.uiScale}
    }
    function check(ok,label):void {if(!ok)throw new Error(label);}
    function walk(item) {let items=[item];for(const child of item.children||[])items=items.concat(walk(child));return items;}
    Component.onCompleted:{Preferences.motion="instant";Preferences.uiScale=.9;Preferences.barHeight=35;Preferences.collapsedWidth=105;Preferences.clusterGap=8;Audio.directCameras=[{directCamera:true,label:"Geometry test camera"}];}
    Timer {interval:180;running:true;repeat:true;onTriggered:{try {
        const stage=surface.clockStage;
        if(phase===0) {
            check(stage.privacySpace,"Camera fixture did not request privacy space");
            const indicator=walk(surface).find(item=>item instanceof PrivacyIndicator);
            check(!!indicator,"Privacy indicator missing");
            const p=indicator.mapToItem(surface.parent,indicator.width/2,indicator.height/2);
            const local=stage.mapFromItem(surface.parent,p.x,p.y);
            stage.activated(local.x);
            check(IslandState.menu==="privacy","Forwarded privacy click opened wrong panel");IslandState.closeMenu();
        } else if(phase===1) {
            stage.activated(1);check(IslandState.menu==="clock","Forwarded normal clock click failed");
            console.log("ISLAND PRIVACY FORWARD PASS");Qt.quit();
        }
        phase++;
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

MEDIA = '''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
ShellRoot {
    property int phase:0
    property var previous
    property var repeatButton
    FloatingWindow {visible:true;implicitWidth:400;implicitHeight:300
        Island.MediaCard {id:card;width:160;height:110}
    }
    TestCase {id:input;when:false}
    function check(ok,label):void {if(!ok)throw new Error(label);}
    function walk(item) {let items=[item];for(const child of item.children||[])items=items.concat(walk(child));return items;}
    Component.onCompleted:Preferences.motion="instant"
    Timer {id:steps;interval:100;running:true;onTriggered:{try {
        const viewport=input.findChild(card,"mediaViewport");
        if(phase===0) {
            check(!!viewport&&viewport.contentWidth>=280&&viewport.contentHeight>=166,"Media content shrinks into overlapping controls");
            previous=walk(card).find(item=>item.label==="Previous track");
            repeatButton=walk(card).find(item=>item.label?.startsWith("Repeat unavailable"));
            check(!!previous&&!!repeatButton,"Playback controls missing");
            const playback=previous.parent;playback.visible=true;
            for(const button of playback.children)button.enabled=true;
            repeatButton.visible=true;repeatButton.enabled=true;
            const times=walk(card).filter(item=>item.text!==undefined&&/^\\d+:\\d+$/.test(item.text));
            check(times.length===2,"Playback timestamps missing");
            times.forEach(item=>{item.visible=true;item.text="59:59";});
            input.wait(35);
            check(times[0].x+times[0].width<=playback.x&&repeatButton.x+repeatButton.width<=times[1].x,"Playback timestamps overlap controls");
            check(Math.abs(playback.x+playback.width/2-viewport.contentWidth/2)<.01,"Primary transport group is not centered "+[playback.x,playback.width,playback.parent.width,viewport.contentWidth]);
            const title=walk(card).find(item=>item.font?.pixelSize===15&&item.parent?.x===114);
            check(!!title&&title.width>0,"Media title overlaps artwork");
            repeatButton.forceActiveFocus();
        } else if(phase===1) {
            const p=repeatButton.mapToItem(viewport,0,0);
            check(repeatButton.activeFocus&&p.x>=0&&p.x+repeatButton.width<=viewport.width+.1&&p.y>=0&&p.y+repeatButton.height<=viewport.height+.1,"Narrow media keyboard control stays clipped");
            check(viewport.contentX>0&&viewport.contentY>0,"Media keyboard focus does not scroll");
            console.log("ISLAND MEDIA SCROLL PASS");Qt.quit();return;
        }
        phase++;steps.restart();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

SOUND = '''import QtQuick
import QtTest
import Quickshell
import qs.services
import "modules/island" as Island
ShellRoot {
    id:test
    property var node
    property int phase:0
    property int actions:0
    FloatingWindow {visible:true;implicitWidth:500;implicitHeight:600;Island.SoundMenu {id:sound;width:340;height:500}}
    Component {id:nodeComponent;QtObject {property string description:"Temporary output";property string name:"fixture";property QtObject audio:QtObject {property bool muted:false;property real volume:.5}}}
    TestCase {id:input;when:false}
    function check(ok,label) {if(!ok)throw new Error(label);}
    function walk(item) {let all=[item];for(const child of item.children||[])all=all.concat(walk(child));return all;}
    Timer {interval:100;running:true;repeat:true;onTriggered:{try{
        if(phase===0){Preferences.motion="instant";node=nodeComponent.createObject(test);Audio.outputs=[node];phase++;return;}
        if(phase===1){check(walk(sound).some(c=>c.text==="Temporary output"),"Sound node fixture not loaded");node.destroy();phase++;return;}
        if(phase===2){check(node===null,"Fixture QObject was not removed");Audio.outputs=[node];phase++;return;}
        if(phase===3){
        const unavailable=walk(sound).find(c=>c.text==="Device unavailable");
        check(!!unavailable,"Removed QObject has no safe unavailable presentation");
        let row=unavailable.parent;while(row&&row.modelData!==null)row=row.parent;
        check(!!row&&!row.enabled,"Removed QObject retains enabled controls");
        for(const control of walk(row).filter(c=>c.pressKey!==undefined||c.control!==undefined)) {
            check(!control.enabled,"Removed node retains enabled control");
            if(control.clicked!==undefined){control.clicked.connect(()=>test.actions++);input.mouseClick(control);}
        }
        check(actions===0,"Removed node accepts pointer action");
        Audio.outputs=[];phase++;return;}
        if(phase===4){check(!walk(sound).some(c=>c.text==="Device unavailable"),"Unavailable row survives list reconciliation");node=nodeComponent.createObject(test,{description:"Replacement output"});Audio.outputs=[node];phase++;return;}
        check(walk(sound).some(c=>c.text==="Replacement output"),"Replacement node does not render");
        console.log("ISLAND SOUND NODE REMOVAL PASS");Qt.quit();
    }catch(e){console.error(e);Qt.exit(1);}}}
}
'''

BLUETOOTH = '''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
ShellRoot {
    id:test
    FloatingWindow {visible:true;implicitWidth:900;implicitHeight:720
        TextInput {id:guard;x:10;y:660;width:140;height:28;text:"Focus guard"}
        Island.IslandSurface {id:surface;availableWidth:640;availableHeight:520}
    }
    Component {id:deviceFixture;QtObject {
        property string name:"";property string icon:"bluetooth";property bool paired:true
        property bool connected:false;property bool pairing:false;property bool batteryAvailable:false;property real battery:0
    }}
    TestCase {id:input;when:false}
    function check(ok,message) {if(!ok)throw new Error(message);}
    function walk(item) {let all=[item];for(const child of item.children||[])all=all.concat(walk(child));return all;}
    function find(item,predicate) {const found=walk(item).find(predicate);check(!!found,"Missing Bluetooth integration control");return found;}
    function settle() {input.wait(80);}
    function inside(item,viewport,label,tolerance=.1) {
        const p=item.mapToItem(viewport,0,0);
        check(p.y>=-tolerance&&p.y+item.height<=viewport.height+tolerance,label+" vertically clipped y="+p.y+" h="+item.height+" viewport="+viewport.height);
        check(p.x>=-tolerance&&p.x+Math.min(item.width,viewport.width)<=viewport.width+tolerance,label+" horizontally clipped x="+p.x+" w="+item.width+" viewport="+viewport.width);
    }
    function exercise(profile) {
        Preferences.uiScale=profile.scale;surface.availableHeight=profile.height;
        Radio.enabled=true;Radio.devices=Array.from({length:profile.count},(_,i)=>deviceFixture.createObject(test,{name:"Device "+i}));
        IslandState.openMenu("bluetooth");
        input.tryVerify(()=>!!input.findChild(surface.controlStage,"bluetoothPanel"),2000,"Bluetooth panel unavailable");settle();
        const panel=input.findChild(surface.controlStage,"bluetoothPanel");
        const center=find(surface.controlStage,c=>"scrollKey" in c);
        const list=find(panel,c=>"positionViewAtIndex" in c);
        const outer=input.findChild(surface.controlStage,"controlDetailViewport");
        check(!!outer&&panel.visible&&panel.enabled,"Production detail unavailable");
        guard.forceActiveFocus();settle();
        check(guard.activeFocus&&Radio.calls.length===0,"Bluetooth steals settled focus or dispatches");
        function rows() {return walk(panel).filter(c=>c.device?.name);}
        function action(row) {return find(row,c=>c.text==="Connect"&&"clicked" in c);}
        function focused() {return panel.Window.window.activeFocusItem;}
        function contained(target,label) {inside(target,list,label+" list");inside(target,outer,label+" outer",.5);}
        function trace(target,row,label) {
            console.log("ISLAND BLUETOOTH NESTED "+JSON.stringify({label,device:row.device.name,row:target===row,y:target.mapToItem(list,0,0).y,height:target.height,listHeight:list.height,originY:list.originY,contentY:list.contentY,contentHeight:list.contentHeight,outerHeight:outer.height,scale:profile.scale}));
        }
        const visited=[];
        for(let n=0;n<180;n++) {
            input.keyClick(Qt.Key_Tab);settle();
            const target=focused(),row=rows().find(c=>c===target||action(c)===target);
            if(!row)continue;
            visited.push(row.device.name+(target===row?" row":" action"));
            if(row.device.name==="Device "+(profile.count-1))trace(target,row,"Tab");
            contained(target,"Tab");
            if(row.index===profile.count-1&&target===action(row))break;
        }
        const expected=[];
        for(let i=0;i<profile.count;i++)expected.push("Device "+i+" row","Device "+i+" action");
        check(JSON.stringify(visited)===JSON.stringify(expected),"Nested Tab misses targets "+JSON.stringify(visited));
        check(list.originY!==0,"Sectioned native list does not exercise arbitrary origin");
        for(let n=expected.length-1;n>=0;n--) {
            const target=focused(),row=rows().find(c=>c===target||action(c)===target);
            if(n>=expected.length-2)check(!!row&&row.device.name+(target===row?" row":" action")===expected[n],"Nested ShiftTab misses final target "+expected[n]);
            if(row)contained(target,"ShiftTab");
            input.keyClick(Qt.Key_Backtab,Qt.ShiftModifier);settle();
        }
        check(Radio.calls.length===0&&panel.selected===null,"Focus traversal selects or dispatches");
        const cacheBuffer=list.cacheBuffer;
        list.cacheBuffer=list.contentHeight*2;settle();
        center.forceActiveFocus();settle();list.positionViewAtEnd();settle();
        for(const key of [Qt.Key_PageDown,Qt.Key_Home,Qt.Key_PageUp,Qt.Key_PageDown,Qt.Key_End,Qt.Key_PageDown,Qt.Key_PageUp,Qt.Key_Home]) {
            const minimum=list.originY,maximum=minimum+Math.max(0,list.contentHeight-list.height);
            const expectedY=key===Qt.Key_Home?minimum:key===Qt.Key_End?maximum:Math.max(minimum,Math.min(maximum,list.contentY+(key===Qt.Key_PageUp?-1:1)*list.height*.8));
            const oldY=list.contentY;
            input.keyClick(key);settle();
            console.log("ISLAND BLUETOOTH SCROLL KEY "+JSON.stringify({key,originY:list.originY,contentY:list.contentY,expectedY}));
            if(key===Qt.Key_Home)check(list.atYBeginning,"Home does not reach native beginning");
            if(key===Qt.Key_End)check(list.atYEnd,"End does not reach native end");
            if(key===Qt.Key_PageUp||key===Qt.Key_PageDown)check(Math.abs(list.contentY-expectedY)<.5,"ControlCenter page key ignores native origin key="+key+" old="+oldY+" expected="+expectedY+" actual="+list.contentY);
        }
        list.cacheBuffer=cacheBuffer;settle();
        for(const nested of [false,true]) {
            panel.selected=null;settle();list.positionViewAtEnd();settle();
            const row=rows().find(c=>c.index===profile.count-1),target=nested?action(row):row;
            let selections=0,clicks=0;
            panel.selectedChanged.connect(()=>selections++);row.clicked.connect(()=>clicks++);
            target.forceActiveFocus();settle();const before=Radio.calls.length,oldHeight=list.height;
            panel.confirmForget=true;input.keyClick(Qt.Key_Return);settle();
            check(target.activeFocus&&panel.selected===row.device&&selections===1,"Nested activation loses selection, focus, or single dispatch");
            check(clicks===(nested?0:1)&&panel.confirmForget===nested,"Nested action bubbles to selection");
            check(Radio.calls.length===before+(nested?1:0),"Nested activation operation count changed");
            if(nested)check(Radio.calls[before].operation==="connect"&&Radio.calls[before].name===row.device.name,"Nested action dispatches wrong operation");
            check(list.height<oldHeight,"Selection does not exercise viewport shrink");
            contained(target,"Selection shrink");trace(target,row,"Selection shrink");
            const selectedHeight=list.height;surface.availableHeight=profile.height-60;settle();
            check(list.height<selectedHeight&&target.activeFocus,"Surface resize not exercised or steals focus");
            contained(target,"Surface resize");trace(target,row,"Surface resize");
            input.keyClick(nested?Qt.Key_Backtab:Qt.Key_Tab,nested?Qt.ShiftModifier:Qt.NoModifier);settle();
            check((nested?row:action(row)).activeFocus,"Resized native Tab or ShiftTab misses final target");
            contained(nested?row:action(row),"Resized native traversal");inside(row,list,"Resized full row");
            input.keyClick(nested?Qt.Key_Tab:Qt.Key_Backtab,nested?Qt.NoModifier:Qt.ShiftModifier);settle();
            check(target.activeFocus,"Resized native return traversal loses focus");
            surface.availableHeight=profile.height;settle();contained(target,"Surface restore");
        }
        const before=Radio.calls.length;
        Radio.busy=true;settle();list.positionViewAtEnd();settle();
        const last=rows().find(c=>c.index===profile.count-1);
        check(last.enabled&&!action(last).enabled,"Busy state disables selection or enables operation");
        last.forceActiveFocus();settle();input.keyClick(Qt.Key_Return);settle();contained(last,"Busy selection");
        check(Radio.calls.length===before,"Busy selection dispatches");
        Radio.busy=false;Radio.enabled=false;panel.selected=null;settle();
        check(list.count===profile.count&&rows().every(c=>!c.enabled&&!action(c).enabled),"Off state loses saved devices or enables controls");
        guard.forceActiveFocus();for(let n=0;n<12;n++){input.keyClick(Qt.Key_Tab);settle();}
        check(Radio.calls.length===before&&panel.selected===null,"Off state accepts selection or action");
        Radio.enabled=true;Radio.devices=[];settle();
        const empty=find(panel,c=>c.text==="Put your device in pairing mode to find it here.");
        check(list.count===0&&empty.visible,"Empty enabled status missing");
        Radio.enabled=false;settle();check(empty.visible&&empty.text==="Turn on Bluetooth to connect your devices.","Empty off status missing");
        check(Radio.calls.length===before&&Radio.calls.every(c=>c.operation==="connect")&&Radio.prompt==="","Unexpected Bluetooth side effect");
        console.log("ISLAND BLUETOOTH NESTED PROFILE PASS "+JSON.stringify(profile));
        IslandState.closeMenu();Radio.calls=[];settle();
    }
    Component.onCompleted:{Quickshell.watchFiles=false;Preferences.motion="instant";Preferences.footerTray=false;}
    Timer {interval:200;running:true;onTriggered:{try {
        for(const profile of [{count:20,height:520,scale:1},{count:14,height:420,scale:.9}])exercise(profile);
        console.log("ISLAND BLUETOOTH NESTED PASS");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

RADIO = '''pragma Singleton
import QtQuick
import Quickshell
Singleton {
    property bool enabled:false;property var devices:[];property bool available:true
    property bool blocked:false;property bool busy:false;property bool scanRequested:false
    property string prompt:"";property string code:"";property string deviceName:"";property string status:""
    property string error:"";property var calls:[]
    function startScan() {}function stopScan() {}function respond(accept,value) {}function cancel() {}
    function act(device,operation) {calls=calls.concat([{name:device.name,operation}]);}
}
'''

if __name__ == '__main__':
    root = Path(os.environ.get('MODESTY_TEST_SOURCE', Path(__file__).resolve().parents[1]))
    with tempfile.TemporaryDirectory(prefix='modesty-island-geometry-') as directory:
        workspace = Path(directory)
        for name in ('components', 'modules', 'assets', 'theme', 'scripts'):
            (workspace / name).symlink_to(root / name, target_is_directory=True)
        services = workspace / 'services'
        services.mkdir()
        for source in (root / 'services').iterdir():
            if source.name != 'Audio.qml':
                (services / source.name).symlink_to(source)
        audio = (root / 'services/Audio.qml').read_text()
        for selection in ('n.audio&&!n.isStream&&n.isSink',
                          'n.audio&&!n.isStream&&!n.isSink', 'n.audio&&n.isStream'):
            audio = audio.replace(f'Pipewire.nodes.values.filter(n=>{selection})', '[]')
        audio = audio.replace('readonly property var outputs: []', 'property var outputs: []')
        (services / 'Audio.qml').write_text(audio)
        with patch.object(qml, 'ROOT', workspace):
            run(BOUNDS, 'ISLAND BOUNDS PASS')
            run(SCROLL, 'ISLAND SCROLL PASS')
            run(PRIVACY, 'ISLAND PRIVACY FORWARD PASS')
            run(MEDIA, 'ISLAND MEDIA SCROLL PASS')
            run(SOUND, 'ISLAND SOUND NODE REMOVAL PASS')
            (services / 'Radio.qml').unlink()
            (services / 'Radio.qml').write_text(RADIO)
            run(BLUETOOTH, 'ISLAND BLUETOOTH NESTED PASS', timeout=45)
