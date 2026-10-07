pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
Singleton {
    id:root
    property var monitors: []
    property bool nightLight: false
    property int temperature: 4000
    property string error: ""
    property bool pending: false
    property int remaining: 15
    readonly property bool busy: action.running
    readonly property string script: Qt.resolvedUrl("../scripts/display.py").toString().replace("file://","")
    Component.onCompleted:if(!Preferences.preview)refresh()
    function refresh(): void { if(!query.running)query.running=true; }
    function change(name: string,mode: string,scale: real): void { if(Preferences.preview||busy)return;error="";action.command=["python3",script,"change",JSON.stringify({name,mode,scale})];action.running=true; }
    function confirm(keep: bool): void { if(pending){action.write(keep?"keep\n":"revert\n");pending=false;} }
    property bool nightRequest: false
    property bool nightDirty: false
    property bool nightInFlight: false
    readonly property string nightScript: Qt.resolvedUrl("../scripts/night-light.py").toString().replace("file://","")
    function setNightLight(enabled: bool): void {
        if(Preferences.preview)return;
        nightRequest=enabled;nightLight=enabled;nightDirty=true;error="";nightIdle.restart();
        if(!nightWriter.running)nightWriter.running=true;
        else if(!nightTick.running)nightTick.start();
    }
    function flushNight(): void {
        if(!nightWriter.running||nightInFlight||!nightDirty)return;
        nightDirty=false;nightInFlight=true;
        nightWriter.write(JSON.stringify({enabled:nightRequest,temperature})+"\n");
    }
    Timer {id:nightTick;interval:33;onTriggered:root.flushNight()}
    Timer {id:nightIdle;interval:600;onTriggered:{if(root.nightDirty||root.nightInFlight){restart();return;}nightWriter.running=false;}}
    Process {id:nightWriter;command:["python3",root.nightScript];stdinEnabled:true
        onStarted:root.flushNight()
        stdout:SplitParser {onRead:line=>{try{const d=JSON.parse(line);root.nightInFlight=false;if(!d.ok){root.error=d.error;nightQuery.running=true;}if(root.nightDirty&&!nightTick.running)nightTick.start();}catch(e){root.nightInFlight=false;root.error="Could not read Night Light response";}}}
        onExited:code=>{root.nightInFlight=false;if(root.nightDirty&&!Preferences.preview)nightWriter.running=true;}
    }
    Process {id:nightQuery;command:["python3",root.nightScript,"snapshot"];running:!Preferences.preview
        stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);if(!nightWriter.running){root.nightLight=!!d.nightLight;root.nightRequest=root.nightLight;if(d.temperature)root.temperature=d.temperature;}}catch(e){}}}
    }
    Timer { interval:1000;repeat:true;running:root.pending;onTriggered:root.remaining=Math.max(0,root.remaining-1) }
    Process {id:query;command:["python3",root.script,"snapshot"];stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);if(d.monitors)root.monitors=d.monitors;else root.error=d.error||"";}catch(e){root.error="Could not read displays";}}} }
    Process {id:action;stdinEnabled:true;stdout:SplitParser {onRead:line=>{try{const d=JSON.parse(line);if(d.pending){root.pending=true;root.remaining=15;}if(d.error)root.error=d.error;if(d.nightLight!==undefined)root.nightLight=d.nightLight;}catch(e){root.error="Could not read display response";}}}onExited:{root.pending=false;root.refresh();} }
    Connections {target:IslandState;function onStateChanged(){if(IslandState.state==="display"){root.refresh();if(!nightWriter.running)nightQuery.running=true;}else if(root.pending)root.confirm(false);} }
    Connections {target:Hyprland;function onRawEvent(event){if(["monitoradded","monitorremoved","configreloaded"].includes(event.name)&&IslandState.state==="display")root.refresh();} }
}
