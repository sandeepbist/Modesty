import QtQuick
import qs.theme
Item {
    id: root
    property string source: ""
    property int decodeWidth: 320
    property int decodeHeight: 320
    property int transitionDuration: 320
    property bool front: false
    readonly property bool ready: first.status === Image.Ready || second.status === Image.Ready
    signal failed()
    signal presented()
    function update(): void {
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
        if (String(incoming.source) !== source) return;
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
            presented();
        } else if (incoming === first) firstFade.restart(); else secondFade.restart();
        cleanup.restart();
    }
    onSourceChanged: update()
    Component.onCompleted: update()
    Timer {
        id: cleanup; interval: Math.max(1, root.transitionDuration + 80)
        onTriggered: { const outgoing = root.front ? second : first; outgoing.source = ""; outgoing.opacity = 0; }
    }
    NumberAnimation { id: firstFade; target: first; property: "opacity"; from: 0; to: 1; duration: root.transitionDuration; easing.type: Easing.OutCubic; onFinished: root.presented() }
    NumberAnimation { id: secondFade; target: second; property: "opacity"; from: 0; to: 1; duration: root.transitionDuration; easing.type: Easing.OutCubic; onFinished: root.presented() }
    Image {
        id: first; anchors.fill: parent; opacity: 0
        asynchronous: true; cache: false; fillMode: Image.PreserveAspectCrop
        sourceSize.width: root.decodeWidth; sourceSize.height: root.decodeHeight
        onStatusChanged: { if (status === Image.Ready) root.reveal(first); else if (status === Image.Error) root.failed(); }
    }
    Image {
        id: second; anchors.fill: parent; opacity: 0
        asynchronous: true; cache: false; fillMode: Image.PreserveAspectCrop
        sourceSize.width: root.decodeWidth; sourceSize.height: root.decodeHeight
        onStatusChanged: { if (status === Image.Ready) root.reveal(second); else if (status === Image.Error) root.failed(); }
    }
}
