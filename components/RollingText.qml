import QtQuick
import qs.theme

// Two persistent labels: new updates wait for the current roll and coalesce.
// Neither label changes opacity, so rapid updates never flash through black.
Item {
    id: root
    property string text: ""
    property color color: Theme.text
    property font font: Qt.font({family: Tokens.font, pixelSize: 14, weight: Font.Medium})
    property int horizontalAlignment: Text.AlignHCenter
    property int verticalAlignment: Text.AlignVCenter
    property bool marquee: false
    property bool slideDigits: false
    property bool countsDown: false
    property bool currentUsesDigits: false
    property bool outgoingUsesDigits: false
    property real readingTime: 8
    property string currentText: ""
    property string outgoingText: ""
    property real travel: 1
    property real scrollOffset: 0
    property real outgoingOffset: 0
    property bool initialized: false
    property int readingDuration: 4000
    readonly property real overflow: Math.max(0, currentLabel.implicitWidth - width)
    clip: true

    function delayScroll(): void {
        scrollDelay.stop();
        if(visible&&marquee&&!Tokens.reducedMotion&&overflow>1&&!roll.running)scrollDelay.start();
    }
    function settle(): void {
        roll.stop();scroll.stop();scrollDelay.stop();
        currentText=text;currentUsesDigits=slideDigits;outgoingText="";
        travel=1;scrollOffset=0;outgoingOffset=0;
    }
    function reconcile(): void {
        if (!initialized || (text === currentText && slideDigits === currentUsesDigits)) return;
        if(Tokens.reducedMotion){settle();return;}
        // Keep the existing travel when rapid updates replace the incoming label.
        // Waiting for the old roll to finish makes workspace/status text lag behind.
        if(roll.running){if(slideDigits===currentUsesDigits){currentText=text;scrollOffset=0;}return;}
        if (slideDigits && currentUsesDigits) { currentText = text; return; }
        scroll.stop(); scrollDelay.stop();
        outgoingUsesDigits = currentUsesDigits; currentUsesDigits = slideDigits;
        outgoingText = currentText; outgoingOffset = scrollOffset;
        currentText = text; scrollOffset = 0;
        if (Tokens.reducedMotion || !visible || !outgoingText || !text) {
            travel = 1; outgoingText = ""; delayScroll(); return;
        }
        travel = 0;
        roll.start();
    }
    onTextChanged: Qt.callLater(reconcile)
    onSlideDigitsChanged: Qt.callLater(reconcile)
    onOverflowChanged: { scroll.stop(); scrollOffset = 0; delayScroll(); }
    onMarqueeChanged: {scroll.stop();scrollOffset=0;outgoingOffset=0;delayScroll();}
    Connections {target:Tokens;function onReducedMotionChanged(){if(Tokens.reducedMotion)root.settle();else root.delayScroll();}}
    onVisibleChanged: {
        if (visible) { reconcile(); delayScroll(); }
        else settle();
    }
    Component.onCompleted: { currentUsesDigits = slideDigits; currentText = text; initialized = true; delayScroll(); }
    NumberAnimation {
        id: roll; target: root; property: "travel"; to: 1
        duration: Tokens.reducedMotion ? 0 : Tokens.animMedium
        easing.type: Easing.InOutCubic
        onFinished: { root.outgoingText = ""; Qt.callLater(root.reconcile); root.delayScroll(); }
    }
    Timer {
        id: scrollDelay; interval: 700
        onTriggered: if (!Tokens.reducedMotion && root.visible && root.marquee && !roll.running && root.overflow > 1) { root.readingDuration = Math.max(900, Math.min(root.overflow / 30 * 1000, (root.readingTime - .4) * 1000)); scroll.restart(); }
    }
    SequentialAnimation {
        id: scroll
        NumberAnimation {
            target: root; property: "scrollOffset"; to: root.overflow
            duration: root.readingDuration
            easing.type: Easing.Linear
        }
        PauseAnimation { duration: 1300 }
        NumberAnimation { target: root; property: "scrollOffset"; to: 0; duration: Tokens.reducedMotion ? 0 : 380; easing.type: Easing.InOutCubic }
        onFinished: root.delayScroll()
    }
    SlidingDigits {
        width: root.width; height: root.height; y: -root.height * root.travel
        visible: !!root.outgoingText && root.outgoingUsesDigits
        countsDown:root.countsDown
        text: root.outgoingUsesDigits ? root.outgoingText : ""; font: root.font; color: root.color; animated: false
    }
    SlidingDigits {
        width: root.width; height: root.height; y: root.height * (1 - root.travel)
        visible: root.currentUsesDigits
        countsDown:root.countsDown
        text: root.currentUsesDigits ? root.currentText : ""; font: root.font; color: root.color
    }
    PanelText {
        visible: !!root.outgoingText && !root.outgoingUsesDigits
        x: root.marquee ? -root.outgoingOffset : 0
        y: -root.height * root.travel
        width: root.marquee ? Math.max(root.width, implicitWidth) : root.width; height: root.height
        text: root.outgoingText; font: root.font; color: root.color
        elide: root.marquee ? Text.ElideNone : Text.ElideRight
        horizontalAlignment: root.horizontalAlignment; verticalAlignment: root.verticalAlignment
    }
    PanelText {
        id: currentLabel
        visible: !root.currentUsesDigits
        x: root.marquee ? -root.scrollOffset : 0
        y: root.height * (1 - root.travel)
        width: root.marquee ? Math.max(root.width, implicitWidth) : root.width; height: root.height
        text: root.currentText; font: root.font; color: root.color
        elide: root.marquee ? Text.ElideNone : Text.ElideRight
        horizontalAlignment: root.horizontalAlignment; verticalAlignment: root.verticalAlignment
    }
}
