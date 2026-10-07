pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Polkit

Singleton {
    id: root
    readonly property bool enabled: Quickshell.env("MODESTY_PREVIEW") !== "1"
    readonly property var flow: agentLoader.item?.flow ?? null
    readonly property bool registered: agentLoader.item?.isRegistered ?? false
    property string returnMenu: "none"
    property var requestInfo:({})
    function describeRequest():void {
        if(!enabled||!flow||metadata.running||metadata.requestCookie===flow.cookie)return;
        metadata.requestCookie=flow.cookie;
        metadata.command=["python3",Qt.resolvedUrl("../scripts/auth-request.py").toString().replace("file://",""),flow.actionId,flow.message];
        metadata.running=true;
    }
    onFlowChanged:{requestInfo={};Qt.callLater(describeRequest);}
    Process {
        id:metadata
        property string requestCookie:""
        stdout:StdioCollector {onStreamFinished:{if(root.flow?.cookie!==metadata.requestCookie)return;try{root.requestInfo=JSON.parse(text);}catch(e){}}}
        onExited:Qt.callLater(root.describeRequest)
    }
    function submit(text: string): void { if (flow?.isResponseRequired) flow.submit(text); }
    function cancel(): void { if (flow && !flow.isCompleted) flow.cancelAuthenticationRequest(); }
    Loader {
        id: agentLoader; active: root.enabled
        sourceComponent: PolkitAgent {
            path: "/org/modesty/PolicyAgent"
            onAuthenticationRequestStarted: {
                if (Session.isLocked()) { root.cancel(); return; }
                if (IslandState.menu !== "authentication") root.returnMenu = IslandState.menu;
                IslandState.openMenu("authentication");
            }
            onIsActiveChanged: {
                if (isActive) { if (Session.isLocked()) { root.cancel(); return; } if(IslandState.menu!=="authentication")root.returnMenu = IslandState.menu; IslandState.openMenu("authentication"); }
                else if (IslandState.menu === "authentication") { if (root.returnMenu !== "none" && root.returnMenu !== "authentication") IslandState.openMenu(root.returnMenu); else IslandState.closeMenu(); }
            }
        }
    }
    Connections {target:Session;function onLockedChanged(){if(Session.isLocked())root.cancel();}}
    Connections { target: IslandState; function onMenuChanged() { if (root.flow && !root.flow.isCompleted && IslandState.menu !== "authentication") root.cancel(); } }
}
