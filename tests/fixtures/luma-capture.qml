import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

ShellRoot {
    id: root
    property int phase: 0
    property bool opened: true
    property bool popup: false
    property bool publicContent: false
    property bool publicHoles: false

    PanelWindow {
        anchors { left: true; right: true; top: true; bottom: true }
        exclusionMode: ExclusionMode.Ignore
        color: root.phase === 0 ? "#2468ac" : "#38ac64"
        WlrLayershell.namespace: "modesty-capture-fixture-background"
        WlrLayershell.layer: WlrLayer.Background
        Repeater {
            model: root.publicHoles ? 1200 : 0
            Rectangle {
                required property int index
                x: (index % 40) * 20; y: Math.floor(index / 40) * 20
                width: 20; height: 20
                color: (index + Math.floor(index / 40)) % 2 ? "#eeeeee" : "#111111"
            }
        }
        Rectangle { x: 20; y: 20; width: 60; height: 60; color: "#ffff00" }
    }
    PanelWindow {
        anchors { left: true; right: true; top: true; bottom: true }
        visible: root.publicHoles
        exclusionMode: ExclusionMode.Ignore
        color: "transparent"
        WlrLayershell.namespace: "modesty-capture-public-alpha"
        WlrLayershell.layer: WlrLayer.Top
        Rectangle { x: 120; y: 160; width: 150; height: 240; color: "#80606060" }
        Rectangle { x: 370; y: 160; width: 150; height: 240; color: "#80606060" }
    }
    PanelWindow {
        id: overlay
        anchors { left: true; right: true; top: true; bottom: true }
        color: "transparent"
        visible: root.opened
        WlrLayershell.namespace: "modesty-command-canvas"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
        Rectangle {
            id: card
            x: 120; y: 160; width: 400; height: 240; color: "#ff2244"
            Text { x: 25; y: 25; text: "PRIVATE LUMA FIXTURE"; font.pixelSize: 24; color: "white" }
            TextInput { id: input; x: 25; y: 90; width: 350; height: 60; focus: true; color: "white"; font.pixelSize: 25 }
        }
        mask: Region { item: card }
    }
    PanelWindow {
        anchors { left: true; right: true; top: true; bottom: true }
        color: "transparent"
        visible: root.opened
        WlrLayershell.namespace: "modesty-island"
        WlrLayershell.layer: WlrLayer.Overlay
        Rectangle { x: 580; y: 30; width: 100; height: 60; color: "#ee22ff" }
    }
    PopupWindow {
        anchor.window: overlay
        anchor.rect: Qt.rect(550, 160, 1, 1)
        visible: root.popup && root.opened
        implicitWidth: 160
        implicitHeight: 130
        color: "#ee22ff"
    }
    FloatingWindow {
        visible: root.publicContent
        title: "Public capture fixture"
        implicitWidth: 700
        implicitHeight: 500
        color: "#80606060"
        Text { anchors.centerIn: parent; text: "PUBLIC CONTENT"; color: "white"; font.pixelSize: 24 }
    }
    IpcHandler {
        target: "capture-fixture"
        function state(): string { return JSON.stringify({phase: root.phase, opened: root.opened, text: input.text, width: overlay.width, height: overlay.height}); }
        function phase(value: int): void { root.phase = value; }
        function open(value: bool): void { root.opened = value; }
        function popup(value: bool): void { root.popup = value; }
        function publicContent(value: bool): void { root.publicContent = value; }
        function publicHoles(value: bool): void { root.publicHoles = value; }
    }
}
