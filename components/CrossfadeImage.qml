import QtQuick
import qs.theme
Item {
    id: root
    property string source: ""
    property int decodeWidth: 320
    property int decodeHeight: 320
    property int transitionDuration: 320
    property bool front: false
    property string requestedSource: ""
    property int request: 0
    property int revealedRequest: -1
    property int presentedRequest: -1
    readonly property bool ready: first.status === Image.Ready || second.status === Image.Ready
    readonly property bool transitioning: first.status === Image.Loading || second.status === Image.Loading || firstFade.running || secondFade.running || cleanup.running
    signal failed()
    signal presented()
    function update(): void {
        if(requestedSource===source)return;
        requestedSource=source;request++;
        cleanup.stop();
        if (!source) { first.source = ""; second.source = ""; return; }
        const incoming = front ? second : first;
        const outgoing = front ? first : second;
        if (outgoing.status === Image.Ready && outgoing.source) {
            if (outgoing === first) firstFade.stop(); else secondFade.stop();
            outgoing.opacity = 1;
        }
        if (incoming === first) firstFade.stop(); else secondFade.stop();
        incoming.opacity = 0;
        incoming.source = source;
        if (incoming.status === Image.Ready) reveal(incoming);
    }
    function reveal(incoming): void {
        if (String(incoming.source) !== source || incoming.status !== Image.Ready || revealedRequest === request) return;
        revealedRequest=request;
        const outgoing = front ? first : second;
        const hadPrevious = outgoing !== incoming && outgoing.status === Image.Ready && outgoing.source;
        if (hadPrevious) {
            if (outgoing === first) firstFade.stop(); else secondFade.stop();
            outgoing.opacity = 1;
        }
        first.z = incoming === first ? 1 : 0;
        second.z = incoming === second ? 1 : 0;
        front = incoming === first;
        if (!hadPrevious || Tokens.reducedMotion || transitionDuration === 0) {
            incoming.opacity = 1;
            clearOutgoing(incoming);
            markPresented(incoming);
        } else {
            if (incoming === first) firstFade.restart(); else secondFade.restart();
            cleanup.restart();
        }
    }
    function markPresented(incoming):void {
        if(String(incoming.source)!==source||incoming.status!==Image.Ready||presentedRequest===request)return;
        presentedRequest=request;presented();
    }
    function clearOutgoing(incoming):void {
        const outgoing=incoming===first?second:first;
        outgoing.source="";outgoing.opacity=0;
    }
    function settlePresentation():void {
        firstFade.stop();secondFade.stop();cleanup.stop();
        const incoming=[first,second].find(image=>String(image.source)===source&&image.status===Image.Ready);
        if(incoming) {
            reveal(incoming);incoming.opacity=1;clearOutgoing(incoming);markPresented(incoming);
        } else {
            const outgoing=front?first:second;
            if(outgoing.status===Image.Ready)outgoing.opacity=1;
        }
    }
    function reject(incoming): void {
        if (String(incoming.source) !== source) return;
        cleanup.stop();
        firstFade.stop();
        secondFade.stop();
        first.source = "";
        second.source = "";
        first.opacity = 0;
        second.opacity = 0;
        failed();
    }
    onSourceChanged: update()
    Component.onCompleted: update()
    Connections {target:Tokens;function onReducedMotionChanged(){if(Tokens.reducedMotion)root.settlePresentation();}}
    Timer {
        id: cleanup; interval: Math.max(1, root.transitionDuration + 80)
        onTriggered:root.clearOutgoing(root.front?first:second)
    }
    NumberAnimation { id: firstFade; target: first; property: "opacity"; from: 0; to: 1; duration: root.transitionDuration; easing.type: Easing.OutCubic; onFinished: root.markPresented(first) }
    NumberAnimation { id: secondFade; target: second; property: "opacity"; from: 0; to: 1; duration: root.transitionDuration; easing.type: Easing.OutCubic; onFinished: root.markPresented(second) }
    Image {
        id: first; anchors.fill: parent; opacity: 0
        asynchronous: true; cache: false; fillMode: Image.PreserveAspectCrop
        sourceSize.width: root.decodeWidth; sourceSize.height: root.decodeHeight
        onStatusChanged: { if (status === Image.Ready) root.reveal(first); else if (status === Image.Error) root.reject(first); }
    }
    Image {
        id: second; anchors.fill: parent; opacity: 0
        asynchronous: true; cache: false; fillMode: Image.PreserveAspectCrop
        sourceSize.width: root.decodeWidth; sourceSize.height: root.decodeHeight
        onStatusChanged: { if (status === Image.Ready) root.reveal(second); else if (status === Image.Error) root.reject(second); }
    }
}
