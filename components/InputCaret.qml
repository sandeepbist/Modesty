import QtQuick
import qs.services
import qs.theme

Item {
    id: root
    objectName: "inputCaret"
    required property Item editor
    property Flickable viewport: null
    property color color: Theme.accent
    property real caretWidth: 1.5
    property real caretRadius: caretWidth / 2
    property bool reveal: true
    property int visibilityDuration: 0
    width: caretWidth

    readonly property bool displayable: editor.activeFocus && editor.cursorVisible && editor.enabled && editor.visible && !editor.readOnly && reveal
                                       && (!editor.Window.window || editor.Window.window.visible)
    property real visualX: x
    property real visualY: y
    property bool ready: false
    property bool forceSnap: true
    property int previousPosition: 0
    property real anchorX: 0
    property real anchorY: 0
    property bool blinkOn: true
    readonly property bool moving: horizontal.running || vertical.running
    readonly property bool blinking: blink.running

    function resetBlink(): void {
        blinkOn = true;
        if (displayable && !editor.inputMethodComposing && editor.selectionStart === editor.selectionEnd && Qt.styleHints.cursorFlashTime > 0) blink.restart();
        else blink.stop();
    }
    function sync(): void {
        const anchor = editor.positionToRectangle(Math.min(previousPosition, editor.length));
        const layoutMoved = ready && (Math.abs(anchor.x - anchorX) > 1 || Math.abs(anchor.y - anchorY) > 1);
        const animate = ready && !forceSnap && !layoutMoved && displayable && !Tokens.reducedMotion
                        && !editor.inputMethodComposing && editor.selectionStart === editor.selectionEnd;
        if (animate) {
            horizontal.to = x;
            vertical.to = y;
            if (visualX !== x) horizontal.restart();
            if (visualY !== y) vertical.restart();
        } else {
            horizontal.stop(); vertical.stop();
            visualX = x; visualY = y;
        }
        previousPosition = editor.cursorPosition;
        const cursor = editor.positionToRectangle(previousPosition);
        anchorX = cursor.x;
        anchorY = cursor.y;
        ready = true;
        forceSnap = false;
        resetBlink();
    }
    function snap(): void { forceSnap = true; Qt.callLater(sync); }
    onXChanged: Qt.callLater(sync)
    onYChanged: Qt.callLater(sync)
    onHeightChanged: snap()
    onDisplayableChanged: snap()
    onRevealChanged: snap()
    Component.onCompleted: snap()

    NumberAnimation {id:horizontal;target:root;property:"visualX";duration:Math.round(60/Preferences.motionSpeed);easing.type:Easing.OutCubic}
    NumberAnimation {id:vertical;target:root;property:"visualY";duration:Math.round(60/Preferences.motionSpeed);easing.type:Easing.OutCubic}
    Rectangle {
        x: root.visualX - root.x
        y: root.visualY - root.y
        width: root.caretWidth
        height: root.height
        radius: root.caretRadius
        color: root.color
        opacity: root.displayable && root.editor.selectionStart === root.editor.selectionEnd
                 && (root.editor.inputMethodComposing || Qt.styleHints.cursorFlashTime <= 0 || root.blinkOn) ? 1 : 0
        Behavior on opacity {NumberAnimation {duration:Tokens.reducedMotion?0:Math.round(root.visibilityDuration/Preferences.motionSpeed)}}
    }
    Timer {
        id: blink
        interval: Math.max(1, Qt.styleHints.cursorFlashTime / 2)
        repeat: true
        running: root.displayable && !root.editor.inputMethodComposing && root.editor.selectionStart === root.editor.selectionEnd && Qt.styleHints.cursorFlashTime > 0
        onTriggered: root.blinkOn = !root.blinkOn
    }
    Connections {
        target: root.editor
        function onWidthChanged(): void { root.snap(); }
        function onHeightChanged(): void { root.snap(); }
        function onFontChanged(): void { root.snap(); }
        function onRenderTypeChanged(): void { root.snap(); }
        function onInputMethodComposingChanged(): void { root.snap(); }
        function onSelectionStartChanged(): void { Qt.callLater(root.sync); }
        function onSelectionEndChanged(): void { Qt.callLater(root.sync); }
        function onTextEdited(): void { root.resetBlink(); }
    }
    Connections {
        target: root.viewport
        function onContentXChanged(): void { root.snap(); }
        function onContentYChanged(): void { root.snap(); }
        function onWidthChanged(): void { root.snap(); }
        function onHeightChanged(): void { root.snap(); }
    }
    Connections {target:Tokens;function onReducedMotionChanged(): void { root.forceSnap=true;root.sync(); }}
}
