pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.theme
import Quickshell.Hyprland
Singleton {
    id:root
    property var assignments:({})
    property var desktopBindings:[]
    property string error:""
    property bool loaded:false
    readonly property bool busy:writer.running
    readonly property var actions:[{id:"reminder",label:"New reminder"},{id:"focus",label:"Focus timer"},{id:"focuspause",label:"Pause / resume focus"},{id:"recorder",label:"Screen recorder"},{id:"recordstop",label:"Stop recording"},{id:"recordpause",label:"Pause / resume recording"},{id:"launcher",label:"Applications"},{id:"canvas",label:"Luma"},{id:"settings",label:"Settings"},{id:"quicksettings",label:"Control center"},{id:"media",label:"Media player"},{id:"calendar",label:"Calendar"},{id:"themes",label:"Themes"},{id:"wallpapers",label:"Wallpapers"},{id:"wifi",label:"Wi-Fi"},{id:"bluetooth",label:"Bluetooth"},{id:"display",label:"Display"},{id:"sound",label:"Sound"},{id:"notifhistory",label:"Notification history"},{id:"power",label:"Power menu"},{id:"appearance",label:"Light / dark"},{id:"awake",label:"Keep Awake"},{id:"peace",label:"Peace"},{id:"nightlight",label:"Night Light"},{id:"lock",label:"Lock"},{id:"playpause",label:"Play / pause"},{id:"next",label:"Next track"},{id:"previous",label:"Previous track"}]
    function set(action:string,chord:string):void {
        if(Preferences.preview||busy)return;
        const next=Object.assign({},assignments,{[action]:chord});error="";
        writer.command=["python3",Qt.resolvedUrl("../scripts/bindings.py").toString().replace("file://",""),JSON.stringify(next)];writer.running=true;
    }
    function refreshDesktop():void {
        if(Preferences.preview||desktopReader.running)return;
        desktopReader.running=true;
    }
    function setDesktop(id:string,chord:string):void {
        if(Preferences.preview||busy)return;
        error="";writer.command=["python3",Qt.resolvedUrl("../scripts/desktop-bindings.py").toString().replace("file://",""),JSON.stringify({id,chord})];writer.running=true;
    }
    function restore():void {
        if(Preferences.preview||busy)return;
        writer.command=["python3",Qt.resolvedUrl("../scripts/bindings.py").toString().replace("file://","")];writer.running=true;
    }
    function trigger(action:string):void {
        if(Preferences.preview||Session.isLocked())return;
        if(action==="reminder")Reminders.compose();
        else if(action==="focuspause")FocusTimer.pause();
        else if(action==="recordstop")Recorder.stop();
        else if(action==="recordpause")Recorder.pause();
        else if(action==="canvas")CanvasState.toggle();
        else if(action==="appearance")Theme.toggleMode();
        else if(action==="awake")KeepAwake.toggle();
        else if(action==="peace")Notifications.dnd=!Notifications.dnd;
        else if(action==="nightlight")Display.setNightLight(!Display.nightLight);
        else if(action==="lock")Session.lock(false);
        else if(action==="playpause")Media.togglePlaying();
        else if(action==="next")Media.next();
        else if(action==="previous")Media.previous();
        else if(actions.some(a=>a.id===action))IslandState.toggle(action);
    }
    Process {id:writer;stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.ok){if(data.bindings!==undefined)root.assignments=data.bindings;if(data.desktopBindings)root.desktopBindings=data.desktopBindings;root.loaded=true;root.refreshDesktop();}else root.error=data.error;}catch(e){root.error="Could not update shortcuts";}}}}
    Process {id:desktopReader;command:["python3",Qt.resolvedUrl("../scripts/desktop-bindings.py").toString().replace("file://","")];stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.ok)root.desktopBindings=data.desktopBindings;else root.error=data.error;}catch(e){root.error="Could not read desktop shortcuts";}}}}
    Timer {id:reload;interval:250;onTriggered:root.restore()}
    Connections {target:Hyprland;function onRawEvent(event){if(event.name==="configreloaded")reload.restart();}}
    Component.onCompleted:restore()
}
