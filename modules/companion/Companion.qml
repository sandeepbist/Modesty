import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import Quickshell.Io
import qs.services
import qs.theme
import qs.components
PanelWindow {
    id:root
    property var initialClient:null
    property bool focusObserved:false
    property var client:Hyprland.toplevels.values.find(t=>t.address.replace(/^0x/,"")===focusedAddress.replace(/^0x/,""))?.lastIpcObject??initialClient
    // The cached active toplevel can outlive focus on an empty workspace.
    // Socket focus/workspace events are authoritative until the cache catches up.
    property string focusedAddress:Hyprland.activeToplevel?.address??""
    property string workspaceName:Hyprland.focusedWorkspace?.name??""
    readonly property bool currentWindow:!!client&&!!focusedAddress
        && String(client.address).replace(/^0x/,"")===focusedAddress.replace(/^0x/,"")
        && (client.pinned||String(client.workspace?.name??"")===workspaceName)
    readonly property string appClass:String(client?.class??"").toLowerCase()
    readonly property bool terminal:Preferences.companionTerminal&&/^(foot|footclient|kitty|alacritty|org\.wezfurlong\.wezterm|com\.mitchellh\.ghostty)$/.test(appClass)
    readonly property bool browser:Preferences.companionZen&&/^(zen|zen-browser|app\.zen_browser\.zen)$/.test(appClass)
    readonly property bool matching:currentWindow&&(terminal||browser)&&client.mapped!==false&&client.visible!==false&&!client.hidden&&(client.fullscreen??0)!==2
    readonly property bool capture:Recorder.selecting||Hyprland.toplevels.values.some(t=>/flameshot/i.test(t.lastIpcObject.class??"")&&/^flameshot$/i.test(t.lastIpcObject.title??""))
    readonly property bool showing:Preferences.companionEnabled&&matching&&!Session.isLocked()&&!capture&&!IslandState.menuOpen&&!IslandState.settingsOpen&&!CanvasState.opened
    property bool retiring:false
    property bool typing:false
    readonly property bool watching:browser&&Media.players.some(p=>p.isPlaying&&!Media.isSpotify(p)&&/zen|firefox/i.test(String(p.desktopEntry||"")+String(p.identity||"")+String(p.dbusName||"")))
    readonly property string mood:typing?"typing":watching?"watching":sleep.isIdle?"sleeping":AgentWork.active&&terminal?"working":"idle"
    screen:Quickshell.screens.find(s=>s.name===Hyprland.focusedMonitor?.name)??Quickshell.screens[0]
    anchors {left:true;top:true}
    implicitWidth:Math.ceil(fitSize)
    implicitHeight:Math.ceil(fitSize)
    margins.left:Math.round(Math.max(4,Math.min((screen?.width??1920)-width-4,edgeX)))
    margins.top:Math.round(Math.max(2,edgeY-height*.7))
    color:"transparent"
    exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"modesty-companion"
    WlrLayershell.layer:WlrLayer.Top
    WlrLayershell.keyboardFocus:WlrKeyboardFocus.None
    visible:root.showing||root.retiring&&root.matching&&!Session.isLocked()&&!root.capture
    mask:Region {width:root.width;height:root.height*.7}
    IpcHandler {
        target:"companion"
        function status():string {return JSON.stringify({showing:root.showing,mood:root.mood,gesture:pet.gesture,frame:pet.frame,app:root.appClass,workspace:root.workspaceName,windowWorkspace:root.client?.workspace?.name??"",focused:root.focusedAddress,width:root.width,height:root.height,x:root.margins.left,y:root.margins.top});}
    }
    // Align the illustrated hip line with the actual window edge.
    readonly property real edgeY:Math.max(4,(client?.at?.[1]??0)-(screen?.y??0))
    readonly property real fitSize:Math.max(22,Math.min(Preferences.companionSize,(edgeY-3)/.7))
    readonly property real edgeX:(client?.at?.[0]??0)-(screen?.x??0)
        +(Preferences.companionSide==="left"?Preferences.companionInset:(client?.size?.[0]??300)-fitSize-Preferences.companionInset)
    LumaMark {
        id:pet
        portrait:false;size:root.fitSize;interactive:true
        shown:root.showing&&ready;animate:root.visible
        typing:root.typing;activity:AgentWork.active&&root.terminal?"composing":"idle"
        moodOverride:root.watching?"watching":sleep.isIdle?"sleeping":""
        onDeparted:root.retiring=false
        Accessible.role:Accessible.Button;Accessible.name:"Window companion"
    }
    IdleMonitor {id:sleep;timeout:45;enabled:root.showing;respectInhibitors:false}
    Timer {id:typingEnd;interval:1600;onTriggered:root.typing=false}
    // Some compositor builds do not populate activeToplevel until the first
    // focus event after a shell restart. One snapshot covers that startup gap;
    // a newer socket event always wins over the asynchronous snapshot.
    Process {
        command:["hyprctl","activewindow","-j"];running:true
        stdout:StdioCollector {onStreamFinished:{
            if(root.focusObserved)return;
            try {
                const window=JSON.parse(text);
                if(!window.address)return;
                root.initialClient=window;
                root.focusedAddress=String(window.address);
                root.workspaceName=String(window.workspace?.name??root.workspaceName);
            } catch (_) {}
        }}
    }
    // Existing Hyprland metadata cache is refreshed only while a supported
    // window is visible. 250ms covers resize/move, which lack socket events.
    Timer {interval:250;running:root.showing;repeat:true;onTriggered:Hyprland.refreshToplevels()}
    Connections {
        target:Hyprland
        function onRawEvent(event){
            if(["activewindowv2","workspace","focusedmon","closewindow"].includes(event.name)){
                root.focusObserved=true;root.initialClient=null;
            }
            if(event.name==="activewindowv2")root.focusedAddress=event.data.trim();
            if(event.name==="workspace")root.workspaceName=event.data;
            if(event.name==="focusedmon")root.workspaceName=event.data.split(",").slice(1).join(",");
            if(["activewindowv2","workspace","focusedmon","closewindow"].includes(event.name))Hyprland.refreshToplevels();
            if(event.name==="custom"&&event.data==="modesty-input"&&root.showing){root.typing=true;typingEnd.restart();}
        }
    }
    Connections {target:AgentWork;function onFeedback(outcome){if(root.showing)pet.react(outcome==="completed"?"success":"uncertain");}}
    onShowingChanged:{
        if(showing)retiring=false;
        else {retiring=matching&&!Session.isLocked()&&!capture&&pet.visible;typing=false;typingEnd.stop();}
    }
    onMatchingChanged:if(!matching)retiring=false
    Component.onCompleted:Hyprland.refreshToplevels()
}
