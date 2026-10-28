#!/usr/bin/env python3
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import qml

ROOT = Path(os.environ.get("MODESTY_TEST_SOURCE", Path(__file__).resolve().parents[1]))
STUBS = {
    'Wireless': '''property bool available:true;property bool hardwareEnabled:true;property bool enabled:true
        property var adapters:[];property var device:null;property var networks:[]
        property string connectedName:"Fixture network";property string connectivity:"Full"
        property var passwordNetwork:null;property bool busy:false;property string error:"";property var calls:[]
        function join(network,password) {calls=calls.concat([{name:network.name,password}]);if(network.secure&&!password)passwordNetwork=network;else passwordNetwork=null;}
        function cancel() {busy=false;}function disconnect(network) {}function forget(network) {}function advanced() {}''',
    'Tray': '''property var items:[];property var selected:null;property var calls:[]
        function show(item,footer) {calls=calls.concat([{kind:"menu",id:item.id,footer}]);selected=item;}
        function close() {selected=null;}function enter(owner) {}function exit(owner) {}''',
    'IslandState': '''property string menu:"none";property int closes:0
        function openMenu(value) {menu=value;}function closeMenu() {menu="none";closes++;}''',
    'Hints': 'function show(owner,text) {}function hide(owner) {}',
    'Time': 'property date date:new Date(2026,9,22,12)',
    'Reminders': '''property string focusDate:"";property bool calendarExpanded:false;property bool calendarEditing:false
        property bool loaded:true;property bool drafting:false;property var items:[];property string error:""
        function forDate(day) {return [];}function hasDate(day) {return false;}function read(id) {return {reminder:null};}''',
    'SystemInfo': '''property bool busy:false;property string error:"";property real brightness:.5
        property bool brightnessAvailable:false;function action(name,value) {}function setBrightness(value) {}''',
    'FocusTimer': 'property bool active:false;property string phase:"";property string timeText:"25:00"',
    'Recorder': 'property bool active:false;property string label:"Ready"',
    'KeepAwake': 'property bool active:false;property real until:0;property int remaining:0;function toggle() {active=!active;}',
    'Radio': '''property bool enabled:false;property var devices:[];property bool available:true
        property bool blocked:false;property bool busy:false;property bool scanRequested:false
        property string prompt:"";property string code:"";property string deviceName:"";property string status:""
        property string error:"";property var calls:[]
        function startScan() {}function stopScan() {}function respond(accept,value) {}function cancel() {}
        function act(device,operation) {calls=calls.concat([{name:device.name,operation}]);}''',
    'Notifications': 'property bool dnd:false;property var list:[];property var historyModel:[]',
    'Display': 'property bool nightLight:false;function setNightLight(value) {nightLight=value;}',
    'Media': '''property string title:"";property string artist:"";property string artUrl:"";property var active:null
        property bool playing:false;property bool canRepeat:false;property bool canGoPrevious:false
        property bool canGoNext:false;property real progress:0;property string loopState:"None"
        property string repeatIcon:"repeat";property string repeatLabel:"Repeat"''',
    'Audio': 'property var sink:null;property bool muted:false;property real volume:.5;function setVolume(value) {volume=value;}',
    'Session': 'function lock(value) {}',
}

SOURCE = '''import QtQuick
import QtTest
import Quickshell
import Quickshell.Networking
import "modules/island" as Island
import qs.components
import qs.services
import qs.theme
ShellRoot {
    id:test
    property var events:[]
    property int iconClicks:0
    property int tileClicks:0
    FloatingWindow {
        id:window;visible:true;implicitWidth:900;implicitHeight:1100
        TextInput {id:guard;x:10;y:10;width:120;height:30;text:"Start Tab here"}
        Island.WifiMenu {id:wifi;x:10;y:60;width:340;height:500;visible:false}
        Island.ControlEditor {id:editor;x:10;y:60;width:360;height:950;visible:false}
        Item {id:trayHost;x:10;y:60;width:400;height:80;visible:false;Island.TrayIcons {id:tray}}
        Island.CalendarMenu {id:calendar;x:10;y:60;width:320;height:500;visible:false}
        Island.ControlTile {id:tile;x:10;y:60;width:200;height:72;kind:"wifi";visible:false}
        IconButton {id:icon;x:250;y:60;icon:"close";label:"Fixture icon";visible:false;onClicked:test.iconClicks++}
    }
    TestCase {id:input;when:false}
    function check(ok,message) {if(!ok)throw new Error(message);}
    function walk(item) {let result=[item];for(const child of item.children||[])result=result.concat(walk(child));return result;}
    function find(item,predicate) {const result=walk(item).find(predicate);check(!!result,"Missing control");return result;}
    function settle() {input.wait(35);}
    function tabTo(item) {
        check(!!item,"Missing keyboard target");
        guard.forceActiveFocus();
        for(let i=0;i<180&&!item.activeFocus;i++)input.keyClick(Qt.Key_Tab);
        check(item.activeFocus&&item.activeFocusOnTab,"Tab cannot reach control "+item);
    }
    function network(name,connected=false,secure=false) {return {name,connected,secure,known:false,stateChanging:false,signalStrength:.8,security:secure?WifiSecurityType.Wpa2Psk:WifiSecurityType.Open};}
    function wifiRows() {return walk(wifi).filter(c=>"modelData" in c&&c.modelData?.name);}
    function exerciseWifi() {
        wifi.visible=true;
        Wireless.networks=[network("Open fixture"),network("Connected fixture",true),network("Secure fixture",false,true)];settle();
        const open=wifiRows().find(c=>c.modelData.name==="Open fixture");tabTo(open);
        check(open.background.border.width===1,"Wi-Fi has no focus border");
        for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space]) {
            const before=Wireless.calls.length;input.keyClick(key);
            check(wifi.selected.name==="Open fixture"&&Wireless.calls.length===before+1,"Wi-Fi key must select and join once "+key);
        }
        input.mouseClick(open,20,20);check(Wireless.calls.length===4,"Wi-Fi pointer join lost or duplicated");
        Wireless.busy=true;open.forceActiveFocus();input.keyClick(Qt.Key_Return);
        check(Wireless.calls.length===4,"Busy Wi-Fi row starts another join");Wireless.busy=false;
        const connected=wifiRows().find(c=>c.modelData.connected);tabTo(connected);input.keyClick(Qt.Key_Space);
        check(wifi.selected.connected&&Wireless.calls.length===4,"Connected Wi-Fi row starts another join");
        const secure=wifiRows().find(c=>c.modelData.secure);tabTo(secure);input.keyClick(Qt.Key_Enter);settle();
        const password=input.findChild(wifi,"wifiPassword");
        check(password.visible&&password.activeFocus&&wifi.selected.name==="Secure fixture","Secure Wi-Fi does not focus password");
        password.text="fixture password";input.keyClick(Qt.Key_Return);
        check(Wireless.calls.length===6&&Wireless.calls[5].password==="fixture password"&&password.text==="","Password acceptance lost");
        wifi.select(null);Wireless.networks=Array.from({length:14},(_,i)=>network("Network "+i));settle();
        const list=find(wifi,c=>"positionViewAtIndex" in c);tabTo(wifiRows().find(c=>c.modelData.name==="Network 0"));
        let reached=false;
        for(let i=0;i<60;i++) {
            const focused=wifiRows().find(c=>c.activeFocus);
            if(focused) {
                const y=focused.mapToItem(list,0,0).y;
                check(y>=-.1&&y+focused.height<=list.height+.1,"Wi-Fi keyboard focus leaves viewport "+focused.modelData.name+" y="+y+" height="+list.height);
                if(focused.modelData.name==="Network 13"){reached=true;break;}
            }
            input.keyClick(Qt.Key_Tab);settle();
        }
        check(reached,"Wi-Fi keyboard cannot reach last network");
        Wireless.enabled=false;settle();check(wifiRows().length===0,"Wi-Fi off retains network rows");
        wifi.visible=false;Wireless.enabled=true;
        console.log("ISLAND WIFI KEYS PASS");
    }
    function trayRecord(id,onlyMenu=false) {
        return {id,title:id,tooltipTitle:id,icon:"",onlyMenu,hasMenu:true,
            activate:()=>test.events.push(id+":primary"),secondaryActivate:()=>test.events.push(id+":secondary"),
            scroll:(delta,horizontal)=>test.events.push(id+":scroll:"+delta+":"+horizontal)};
    }
    function exerciseTray() {
        Preferences.preview=false;trayHost.visible=true;Tray.items=[trayRecord("Fixture"),trayRecord("Menu fixture",true)];settle();
        const icon=find(tray,c=>c.modelData?.id==="Fixture");tabTo(icon);
        check(icon.background.border.width===1,"Tray has no focus border");
        for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space]) {
            const before=events.length;input.keyClick(key);
            check(events.length===before+1&&events[before]==="Fixture:primary","Tray key must activate exactly once "+key);
        }
        const closed=IslandState.closes;check(closed===3,"Tray primary does not close island menu");
        input.keyClick(Qt.Key_Menu);input.keyClick(Qt.Key_F10,Qt.ShiftModifier);
        check(Tray.calls.length===2&&Tray.calls.every(c=>c.id==="Fixture"&&!c.footer),"Tray context keyboard lost");
        input.keyClick(Qt.Key_F10);check(Tray.calls.length===2,"Unmodified F10 opens tray menu");
        input.mouseClick(icon,10,10,Qt.RightButton);input.mouseClick(icon,10,10,Qt.MiddleButton);input.mouseClick(icon,10,10,Qt.LeftButton);
        check(Tray.calls.length===3&&events.slice(-2).join()==="Fixture:secondary,Fixture:primary","Tray pointer buttons lost or duplicated");
        input.mouseWheel(icon,10,10,0,-120);input.mouseWheel(icon,10,10,120,0);
        check(events.slice(-2).join()==="Fixture:scroll:-120:false,Fixture:scroll:120:true","Tray wheel axes lost");
        input.mouseMove(window.contentItem,800,1000);
        const menu=find(tray,c=>c.modelData?.id==="Menu fixture");tabTo(menu);const before=events.length;
        input.keyClick(Qt.Key_Space);check(events.length===before&&Tray.calls.length===4,"Menu-only tray icon invokes primary");
        tray.inFooter=true;icon.forceActiveFocus();input.keyClick(Qt.Key_Menu);
        check(Tray.calls[4].footer,"Tray footer context location lost");
        Preferences.preview=true;const menus=Tray.calls.length,actions=events.length;
        for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space,Qt.Key_Menu])input.keyClick(key);
        input.keyClick(Qt.Key_F10,Qt.ShiftModifier);
        for(const button of [Qt.LeftButton,Qt.RightButton,Qt.MiddleButton])input.mouseClick(icon,10,10,button);
        input.mouseWheel(icon,10,10,0,120);input.mouseMove(window.contentItem,800,1000);
        check(events.length===actions&&Tray.calls.length===menus,"Tray preview guard lost");
        Preferences.preview=false;trayHost.enabled=false;input.mouseClick(icon,10,10);input.mouseWheel(icon,10,10,0,120);
        check(events.length===actions&&Tray.calls.length===menus,"Disabled tray accepts pointer action");
        trayHost.enabled=true;Preferences.preview=true;
        Tray.items=Array.from({length:12},(_,i)=>trayRecord("Overflow "+i));tray.maximumWidth=90;settle();
        const view=find(tray,c=>"flickableDirection" in c),first=find(tray,c=>c.modelData?.id==="Overflow 0");tabTo(first);
        let reached=false;
        for(let i=0;i<20;i++) {
            const focused=walk(tray).find(c=>c.modelData?.id&&c.activeFocus);
            if(focused) {
                const x=focused.mapToItem(view,0,0).x;
                check(x>=-.1&&x+focused.width<=view.width+.1,"Tray keyboard focus leaves viewport "+focused.modelData.id);
                if(focused.modelData.id==="Overflow 11"){reached=true;break;}
            }
            input.keyClick(Qt.Key_Tab);settle();
        }
        check(reached,"Tray keyboard cannot reach last icon");
        trayHost.visible=false;console.log("ISLAND TRAY KEYS AND SECONDARY PASS");
    }
    function editorTiles() {return walk(editor).filter(c=>"entry" in c&&"modelData" in c);}
    function entry(id) {return ControlLayout.items.find(c=>c.id===id);}
    function exerciseEditor() {
        ControlLayout.items=[{id:"wifi",x:0,y:0,w:2,h:1},{id:"bluetooth",x:2,y:0,w:2,h:1}];ControlLayout.history=[];
        editor.visible=true;settle();const wifiTile=editorTiles().find(c=>c.modelData==="wifi");tabTo(wifiTile);
        check(editor.selected==="wifi","Tab does not select editor tile");
        for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space]) {
            editor.selected="";input.keyClick(key);check(editor.selected==="wifi","Editor key does not select tile "+key);
        }
        input.keyClick(Qt.Key_Right);input.keyClick(Qt.Key_Down);
        check(entry("wifi").x===1&&entry("wifi").y===1,"Editor keyboard move lost");
        input.keyClick(Qt.Key_Right,Qt.ShiftModifier);input.keyClick(Qt.Key_Down,Qt.ShiftModifier);
        check(entry("wifi").w===3&&entry("wifi").h===2,"Editor keyboard resize lost");
        input.keyClick(Qt.Key_Delete);settle();check(!entry("wifi")&&editor.selected==="","Editor Delete does not remove selection");
        const bluetooth=editorTiles().find(c=>c.modelData==="bluetooth");tabTo(bluetooth);
        check(editor.selected==="bluetooth","Editor skips remaining tile");
        const initial={x:entry("bluetooth").x,y:entry("bluetooth").y};
        input.mousePress(bluetooth,20,15);input.mouseMove(bluetooth,20,70,30);input.mouseRelease(bluetooth,20,70);settle();
        check(entry("bluetooth").y===initial.y+1&&!editor.gesture&&!editor.dragging,"Editor pointer drag no longer commits");
        input.mouseClick(bluetooth,20,15,Qt.RightButton);settle();
        const sizes=bluetooth.data.find(c=>"popup" in c&&"close" in c);
        check(sizes?.visible,"Editor right-click size menu lost");sizes.close();
        input.mousePress(bluetooth,bluetooth.width-8,bluetooth.height-8);
        input.mouseMove(bluetooth,bluetooth.width+47,bluetooth.height+47,30);
        input.mouseRelease(bluetooth,bluetooth.width+47,bluetooth.height+47);settle();
        check(entry("bluetooth").w===3&&entry("bluetooth").h===2&&!editor.gesture,"Editor pointer resize no longer commits");
        input.mousePress(bluetooth,20,15);input.mouseMove(bluetooth,20,70,30);input.keyClick(Qt.Key_Escape);input.mouseRelease(bluetooth,20,70);settle();
        check(entry("bluetooth").y===initial.y+1&&!editor.gesture,"Editor Escape does not cancel drag");
        editor.visible=false;console.log("ISLAND EDITOR KEYS AND DRAG PASS");
    }
    function exerciseCalendar() {
        calendar.visible=true;calendar.selectedDate="2026-10-22";calendar.year=2026;calendar.month=9;calendar.mode="days";settle();
        const chooser=find(calendar,c=>c.text===Qt.formatDateTime(calendar.viewDate,"MMMM yyyy"));tabTo(chooser);
        check(chooser.background.border.width===1,"Calendar chooser has no focus border");
        for(const [key,mode] of [[Qt.Key_Return,"months"],[Qt.Key_Enter,"years"],[Qt.Key_Space,"days"]]) {
            Reminders.calendarExpanded=true;input.keyClick(key);settle();
            check(calendar.mode===mode&&!Reminders.calendarExpanded&&!calendar.editing,"Calendar chooser keyboard lost or bubbles "+key);
        }
        input.mouseClick(chooser,30,10);settle();check(calendar.mode==="months","Calendar chooser pointer lost");
        calendar.year=2030;calendar.month=3;Reminders.calendarExpanded=true;
        input.mouseClick(chooser,30,10,Qt.RightButton);settle();
        check(calendar.year===2026&&calendar.month===9&&calendar.mode==="days"&&!Reminders.calendarExpanded,"Calendar right-click today lost");
        chooser.forceActiveFocus();input.keyClick(Qt.Key_PageDown);settle();check(calendar.month===10,"Calendar PageDown lost");
        input.keyClick(Qt.Key_Home);settle();check(calendar.month===9,"Calendar Home lost");
        calendar.visible=false;console.log("ISLAND CALENDAR KEYS PASS");
    }
    function luminance(color) {return [color.r,color.g,color.b].map(v=>v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);}
    function contrast(a,b) {const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
    function exerciseContrast() {
        tile.visible=true;Wireless.enabled=true;let minimum=Infinity;
        tabTo(tile);
        for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space]) {
            IslandState.menu="none";input.keyClick(key);check(IslandState.menu==="wifi","Control tile key does not open Wi-Fi "+key);
        }
        for(const state of ["interactive","editing","enabled"]) {
            guard.forceActiveFocus();
            tile.interactive=true;tile.editing=false;tile.enabled=true;
            tile[state]=state==="editing";IslandState.menu="none";
            tile.forceActiveFocus();
            for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space])input.keyClick(key);
            input.mouseClick(tile,20,20);
            check(IslandState.menu==="none"&&!tile.usable,"Inactive control tile accepts activation "+state);
        }
        tile.interactive=true;tile.editing=false;tile.enabled=true;
        for(const name of Object.keys(Theme.palettes))for(const mode of ["dark","light"]) {
            Theme.setPalette(name);Theme.setMode(mode);settle();
            const subtitle=find(tile,c=>"text" in c&&c.text==="Fixture network");
            const alpha=subtitle.color.a,ink=Qt.rgba(subtitle.color.r*alpha+tile.color.r*(1-alpha),subtitle.color.g*alpha+tile.color.g*(1-alpha),subtitle.color.b*alpha+tile.color.b*(1-alpha),1);
            const ratio=contrast(ink,tile.color);minimum=Math.min(minimum,ratio);
            check(ratio>=4.5,"Selected subtitle contrast below 4.5 "+name+" "+mode+" "+ratio);
        }
        console.log("ISLAND SELECTED SUBTITLE CONTRAST PASS minimum="+minimum.toFixed(2));
    }
    function exercisePressFeedback() {
        icon.visible=true;tile.visible=true;tile.kind="peace";
        Notifications.dndChanged.connect(()=>test.tileClicks++);
        function count(control) {return control===icon?iconClicks:tileClicks;}
        function tint(control) {return control===icon?walk(icon).some(c=>c.color?.a>.12&&c.color.a<.14):tile.children.some(c=>Math.abs(c.opacity-.085)<.001);}
        for(const control of [icon,tile]) {
            for(const key of [Qt.Key_Space,Qt.Key_Return,Qt.Key_Enter]) {
                control.forceActiveFocus();const before=count(control);
                input.keyPress(key);settle();
                check(control.pressed&&control.scale<.99&&tint(control),"Keyboard lacks pointer-like press feedback "+key);
                check(count(control)===before+(key===Qt.Key_Space?0:1),"Initial key timing changed "+key);
                input.keyPress(key);control.pressKey({key,isAutoRepeat:true,accepted:false});
                control.releaseKey({key,isAutoRepeat:true,accepted:false});
                check(control.pressed&&count(control)===before+(key===Qt.Key_Space?0:1),"Autorepeat changes press or activation "+key);
                input.keyRelease(key);settle();
                check(!control.pressed&&control.scale===1&&count(control)===before+1,"Release must finish feedback and activate once "+key);
            }
            for(const cancel of ["escape","focus","disable","mismatch",...(control===tile?["editing","interactive"]:[])]) {
                control.forceActiveFocus();const before=count(control);input.keyPress(Qt.Key_Space);
                if(cancel==="escape")input.keyClick(Qt.Key_Escape);
                else if(cancel==="focus")guard.forceActiveFocus();
                else if(cancel==="disable")control.enabled=false;
                else if(cancel==="mismatch")input.keyRelease(Qt.Key_Return);
                else if(cancel==="editing")tile.editing=true;
                else tile.interactive=false;
                input.keyRelease(Qt.Key_Space);
                check(!control.pressed&&count(control)===before,"Cancelled Space activates "+cancel);
                control.enabled=true;tile.editing=false;tile.interactive=true;
            }
            const before=count(control);input.mousePress(control,10,10);settle();
            check(control.pressed&&control.scale<.99&&tint(control),"Pointer feedback changed");
            input.mouseRelease(control,10,10);check(count(control)===before+1,"Pointer activates more than once");
        }
        tile.kind="sound";Audio.sink={};settle();
        const slider=find(tile,c=>c.orientation!==undefined&&c.position!==undefined);slider.forceActiveFocus();
        IslandState.menu="none";
        for(const key of [Qt.Key_Space,Qt.Key_Return,Qt.Key_Enter,Qt.Key_Right])input.keyClick(key);
        check(IslandState.menu==="none"&&!tile.pressed&&slider.activeFocus,"Parent tile steals nested slider keys");
        console.log("ISLAND PRESS TIMING FEEDBACK AND CANCELLATION PASS");
    }
    Component.onCompleted:Preferences.motion="instant"
    Timer {interval:120;running:true;onTriggered:{try {
        exerciseWifi();exerciseTray();exerciseEditor();exerciseCalendar();exerciseContrast();exercisePressFeedback();
        console.log("ISLAND CONTROLS PASS");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

PANELS = '''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import "modules/island" as Island
import qs.components
import qs.services
import qs.theme
ShellRoot {
    id:test
    property int selections:0
    property int rowClicks:0
    property var sliderMoves:[]
    FloatingWindow {
        id:window;visible:true;implicitWidth:760;implicitHeight:580
        Rectangle {anchors.fill:parent;color:Theme.bgSolid}
        TextInput {id:guard;x:10;y:10;width:120;height:30;text:"Start Tab here"}
        Island.BluetoothMenu {id:bluetooth;x:16;y:52;width:340;height:500;visible:false;onSelectedChanged:test.selections++}
        PreferenceSlider {id:preference;x:384;y:52;width:340;label:"Brightness";display:Math.round(value*100)+"%";from:0;to:1;stepSize:.01;value:.5;visible:false;onMoved:value=>{test.sliderMoves=test.sliderMoves.concat([value]);preference.value=value;}}
        Island.MediaCard {id:media;x:384;y:138;width:340;height:166;visible:false}
    }
    TestCase {id:input;when:false}
    function check(ok,message) {if(!ok)throw new Error(message);}
    function near(a,b,message) {check(Math.abs(a-b)<.00001,message+" expected="+b+" actual="+a);}
    function walk(item) {let result=[item];for(const child of item.children||[])result=result.concat(walk(child));return result;}
    function find(item,predicate) {const result=walk(item).find(predicate);check(!!result,"Missing control");return result;}
    function settle() {input.wait(35);}
    function tabTo(item) {
        guard.forceActiveFocus();
        for(let i=0;i<180&&!item.activeFocus;i++)input.keyClick(Qt.Key_Tab);
        check(item.activeFocus&&item.activeFocusOnTab,"Tab cannot reach control "+item);settle();
    }
    Component {id:deviceFixture;QtObject {
        property string name:"";property bool paired:false;property bool connected:false;property bool pairing:false
        property string icon:"bluetooth";property bool batteryAvailable:connected;property real battery:.8
    }}
    function device(name,paired=false,connected=false) {return deviceFixture.createObject(test,{name,paired,connected});}
    function rows() {return walk(bluetooth).filter(c=>c.device?.name);}
    function action(row) {return find(row,c=>["Pair","Connect","Disconnect"].includes(c.text)&&"clicked" in c);}
    function contained(item,list,message) {
        const p=item.mapToItem(list,0,0);
        check(p.y>=-.1&&p.y+item.height<=list.height+.1&&p.x>=-.1&&p.x+item.width<=list.width+.1,message+" y="+p.y+" height="+list.height);
    }
    function selectOnce(row,activate) {
        bluetooth.selected=null;bluetooth.confirmForget=true;Radio.error="Selection sentinel";settle();
        const before=selections,calls=Radio.calls.length,clicks=rowClicks;
        activate();settle();
        check(bluetooth.selected===row.device&&selections===before+1,"Bluetooth selection must change exactly once device="+row.device.name+" selected="+bluetooth.selected?.name+" changes="+(selections-before)+" focus="+row.activeFocus+" busy="+Radio.busy+" calls="+Radio.calls.length+" accessible="+row.Accessible.selected);
        check(!bluetooth.confirmForget&&Radio.error===""&&Radio.calls.length===calls,"Bluetooth selection dispatches action or misses reset");
        check(rowClicks===clicks+1,"Bluetooth selection click must emit once");
        check(row.Accessible.selected,"Bluetooth selected state missing");
    }
    function exerciseBluetooth() {
        Radio.enabled=true;Radio.devices=[device("Connected fixture",true,true),device("Saved fixture",true),device("Nearby fixture")];
        guard.forceActiveFocus();bluetooth.visible=true;settle();
        check(guard.activeFocus&&Radio.calls.length===0,"Bluetooth steals initial focus or auto pairs");
        const list=find(bluetooth,c=>"positionViewAtIndex" in c);
        for(const row of rows()) {
            tabTo(row);
            row.clicked.connect(()=>test.rowClicks++);
            check(row.Accessible.name===row.device.name&&row.Accessible.description.length>0,"Bluetooth accessible label missing");
            check(!row.Accessible.selected&&row.background.border.width===1&&String(row.background.border.color)===String(Theme.accent),"Bluetooth selection focus border missing");
            for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space])selectOnce(row,()=>input.keyClick(key));
            selectOnce(row,()=>input.mouseClick(row,20,20));
            const button=action(row);tabTo(button);
            input.keyClick(Qt.Key_Backtab,Qt.ShiftModifier);settle();check(row.activeFocus,"Bluetooth ShiftTab skips selection row");
            input.keyClick(Qt.Key_Tab);check(button.activeFocus,"Bluetooth Tab skips nested action");
            for(const activate of [()=>input.keyClick(Qt.Key_Return),()=>input.keyClick(Qt.Key_Enter),()=>input.keyClick(Qt.Key_Space),()=>input.mouseClick(button,15,10)]) {
                bluetooth.selected=null;bluetooth.confirmForget=true;Radio.error="Action sentinel";
                const before=Radio.calls.length,count=selections,clicks=rowClicks;activate();settle();
                check(Radio.calls.length===before+1&&selections===count+1&&bluetooth.selected===row.device,"Bluetooth nested action must dispatch exactly once");
                check(Radio.calls[before].operation===(row.device.connected?"disconnect":row.device.paired?"connect":"pair"),"Bluetooth action operation changed");
                check(bluetooth.confirmForget&&Radio.error==="Action sentinel","Bluetooth nested action bubbles to row selection");
                check(rowClicks===clicks,"Bluetooth nested action emits parent click");
            }
            Radio.busy=true;settle();tabTo(row);
            for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space])selectOnce(row,()=>input.keyClick(key));
            selectOnce(row,()=>input.mouseClick(row,20,20));
            check(!button.enabled,"Busy Bluetooth action remains enabled");
            const before=Radio.calls.length;button.forceActiveFocus();
            for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space])input.keyClick(key);
            input.mouseClick(button,15,10);check(Radio.calls.length===before,"Busy Bluetooth dispatches action");
            Radio.busy=false;bluetooth.selected=null;settle();
        }
        Radio.enabled=false;bluetooth.selected=null;settle();
        check(rows().length===2,"Bluetooth off loses saved rows or keeps nearby row");
        for(const row of rows()) {
            const button=action(row),calls=Radio.calls.length,count=selections;
            check(!row.enabled&&!button.enabled,"Bluetooth off leaves retained row enabled");row.forceActiveFocus();
            for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space])input.keyClick(key);
            input.mouseClick(row,20,20);button.forceActiveFocus();
            for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space])input.keyClick(key);
            input.mouseClick(button,15,10);
            check(selections===count&&Radio.calls.length===calls,"Bluetooth off accepts selection or action");
        }
        Radio.enabled=true;Radio.error="";Radio.devices=Array.from({length:14},(_,i)=>device("Device "+i,true));bluetooth.width=220;bluetooth.height=290;settle();
        tabTo(rows().find(c=>c.device.name==="Device 0"));
        let reached=false;const visited=[];
        for(let i=0;i<100;i++) {
            const focused=bluetooth.Window.window.activeFocusItem,row=rows().find(c=>c===focused||action(c)===focused);
            if(row) {
                visited.push(row.device.name+(focused===row?" row":" action"));
                contained(focused,list,"Bluetooth Tab leaves focused control clipped");
                if(row.device.name==="Device 13"&&focused===action(row)){reached=true;break;}
            }
            input.keyClick(Qt.Key_Tab);settle();
        }
        check(reached,"Bluetooth Tab cannot reach final nested action visited="+visited.join(","));
        check(visited.length===28,"Bluetooth Tab skips row or nested action "+visited.join(","));
        for(let i=0;i<28;i++) {
            const focused=bluetooth.Window.window.activeFocusItem,row=rows().find(c=>c===focused||action(c)===focused);
            if(row)contained(focused,list,"Bluetooth ShiftTab leaves focused control clipped");
            input.keyClick(Qt.Key_Backtab,Qt.ShiftModifier);settle();
        }
        for(const nested of [false,true]) {
            bluetooth.selected=null;settle();list.positionViewAtEnd();settle();
            const row=rows().find(c=>c.device.name==="Device 13"),target=nested?action(row):row;
            target.forceActiveFocus();settle();const height=list.height,calls=Radio.calls.length;
            input.keyClick(Qt.Key_Return);settle();
            check(list.height<height,"Bluetooth selection does not exercise viewport shrink");
            contained(target,list,"Bluetooth selection clips focus after viewport shrinks");
            check(target.activeFocus&&Radio.calls.length===calls+(nested?1:0),"Bluetooth selection shrink loses focus or duplicates action");
        }
        bluetooth.visible=false;bluetooth.selected=null;Radio.enabled=false;Radio.devices=[];Radio.calls=[];
        console.log("ISLAND BLUETOOTH SELECTION ACTION TAB SCROLL OFF BUSY PASS");
    }
    function exerciseSliders() {
        preference.visible=true;tabTo(preference.control);
        const control=preference.control;
        check(control.handle.border.width===2&&String(control.handle.border.color)===String(Theme.text),"Preference slider has no focus border");
        for(const key of [Qt.Key_Right,Qt.Key_Left]) {
            const before=sliderMoves.length,value=control.value,delta=key===Qt.Key_Right?.01:-.01;
            input.keyClick(key);check(sliderMoves.length===before+1,"Preference arrow must emit once key="+key+" changes="+(sliderMoves.length-before)+" value="+control.value+" focus="+control.activeFocus);near(control.value,value+delta,"Preference arrow value changed");
        }
        input.mouseClick(control,control.width*.7,control.height/2);check(sliderMoves.length===3,"Preference pointer must emit once");
        const before=sliderMoves.length,value=control.value;preference.enabled=false;control.forceActiveFocus();
        for(const key of [Qt.Key_Right,Qt.Key_Up,Qt.Key_Left,Qt.Key_Down])input.keyClick(key);
        input.mouseClick(control,control.width*.2,control.height/2);input.mouseWheel(control,20,10,0,120);
        check(sliderMoves.length===before&&control.value===value,"Disabled PreferenceSlider accepts input");
        preference.enabled=true;preference.visible=false;
        Media.active={identity:"Fixture player",trackAlbum:"Focus study"};Media.title="Native focus study";Media.artist="Modesty";Media.progress=.5;Media.canSeek=true;media.visible=true;settle();
        const seek=find(media,c=>"visualPosition" in c&&"handle" in c);tabTo(seek);
        check(seek.handle.opacity===1&&seek.handle.border.width===2,"Media seek focus thumb remains hidden or indistinct");
        for(const key of [Qt.Key_Right,Qt.Key_Left]) {
            const before=Media.calls.length,value=seek.value,delta=key===Qt.Key_Right?.1:-.1;
            input.keyClick(key);check(Media.calls.length===before+1,"Media arrow must seek once");near(seek.value,value+delta,"Media arrow value changed");near(Media.calls[before],seek.value*Media.length,"Media seek seconds changed");
        }
        input.mouseClick(seek,seek.width*.7,seek.height/2);check(Media.calls.length===3,"Media pointer must seek once");
        for(const empty of [false,true]) {
            Media.canSeek=false;Media.active=empty?null:{identity:"Unseekable fixture"};settle();
            const before=Media.calls.length,value=seek.value;seek.forceActiveFocus();
            for(const key of [Qt.Key_Right,Qt.Key_Up,Qt.Key_Left,Qt.Key_Down])input.keyClick(key);
            input.mouseClick(seek,seek.width*.2,seek.height/2);input.mouseWheel(seek,20,10,0,120);
            check(Media.calls.length===before&&seek.value===value,"Disabled or empty media accepts seek");
        }
        media.visible=false;console.log("ISLAND SLIDER ARROWS POINTER DISABLED EMPTY PASS");
    }
    Component.onCompleted:{Preferences.motion="instant";Theme.setPalette("midnight");Theme.setMode("dark");}
    Timer {interval:120;running:true;onTriggered:{try {
        exerciseBluetooth();exerciseSliders();console.log("ISLAND PANEL INTERACTIONS PASS");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

ART = '''import QtQuick
import QtTest
import Quickshell
import qs.components
import qs.services
ShellRoot {
    property int failures:0
    FloatingWindow {visible:true;implicitWidth:200;implicitHeight:100
        Art {id:cover;width:80;height:80;source:"GOOD_ART"}
    }
    TestCase {id:input;when:false}
    function check(ok,message) {if(!ok)throw new Error(message);}
    function waitFor(predicate,message) {for(let i=0;i<100&&!predicate();i++)input.wait(10);check(predicate(),message);}
    Component.onCompleted:Preferences.motion="instant"
    Timer {interval:100;running:true;onTriggered:{try {
        const image=cover.children.find(c=>"transitionDuration" in c),fallback=cover.children.find(c=>"icon" in c);
        image.failed.connect(()=>failures++);image.transitionDuration=0;
        waitFor(()=>image.ready,"Initial artwork not ready");check(!fallback.visible,"Ready art shows fallback");
        cover.source="BAD_ART";waitFor(()=>failures===1,"Current artwork error does not emit failed");
        check(!image.ready&&fallback.visible,"Artwork failure retains old art or suppresses fallback");
        check(image.children.filter(c=>"status" in c&&"source" in c).every(c=>!String(c.source)&&c.opacity===0),"Failed artwork leaves decoded slot visible");
        cover.source="GOOD_ART";waitFor(()=>image.ready,"Art does not recover after failure");
        const slots=image.children.filter(c=>"status" in c&&"source" in c),obsolete=slots.find(c=>!String(c.source));
        obsolete.source="OBSOLETE_ART";waitFor(()=>obsolete.status===Image.Error,"Obsolete error setup did not load");
        check(image.ready&&!fallback.visible&&failures===1,"Late obsolete error clears valid current artwork");
        cover.source="";check(!image.ready&&fallback.visible,"Empty artwork retains previous cover");
        console.log("ISLAND ART ERROR AND OBSOLETE PASS");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

with tempfile.TemporaryDirectory(prefix='modesty-island-controls-') as directory:
    workspace = Path(directory)
    for name in ('components', 'modules', 'assets', 'theme', 'scripts'):
        (workspace / name).symlink_to(ROOT / name, target_is_directory=True)
    services = workspace / 'services'
    services.mkdir()
    for source in (ROOT / 'services').iterdir():
        if source.suffix == '.js' or source.name == 'ControlLayout.qml':
            (services / source.name).symlink_to(source)
    preferences = (ROOT / 'services/Preferences.qml').read_text().replace(
        'readonly property bool preview: Quickshell.env("MODESTY_PREVIEW") === "1"',
        'property bool preview:true')
    (services / 'Preferences.qml').write_text(preferences)
    for name, body in STUBS.items():
        if name == 'Media':
            body += ''';property real position:120;property real length:240;property bool canSeek:true;property var calls:[]
                function seekTo(value) {calls=calls.concat([value]);progress=value/length;}
                function togglePlaying() {}function previous() {}function next() {}function cycleRepeat() {}'''
        (services / f'{name}.qml').write_text('pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {' + body + '}\n')
    (services / 'qmldir').write_text(''.join(
        f'singleton {name} 1.0 {name}.qml\n' for name in ('Preferences', 'ControlLayout', *STUBS)))
    with patch.object(qml, 'ROOT', workspace):
        qml.run(SOURCE, 'ISLAND CONTROLS PASS')
        qml.run(PANELS, 'ISLAND PANEL INTERACTIONS PASS')
        qml.run(ART.replace('GOOD_ART', (ROOT / 'assets/icons/lucide/music-2.svg').as_uri())
                .replace('BAD_ART', (workspace / 'missing-current.png').as_uri())
                .replace('OBSOLETE_ART', (workspace / 'missing-obsolete.png').as_uri()),
                'ISLAND ART ERROR AND OBSOLETE PASS')
