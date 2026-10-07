import QtQuick
import qs.services
import qs.theme

Item {
    id: root
    property string kind: ""
    property string label: ""
    readonly property int dotSize: 6
    property color lampColor: "#ff9f0a"
    property real reveal: kind ? 1 : 0
    signal clicked()
    implicitWidth: 22
    implicitHeight: Preferences.barHeight
    enabled: !!kind
    visible: reveal > 0
    activeFocusOnTab: enabled
    Accessible.role: Accessible.Button
    Accessible.name: label || "Privacy controls"
    onKindChanged: if (kind) lampColor = kind === "camera" ? "#30d158" : kind === "microphone" ? "#ff9f0a" : "#64b5ff"
    onLabelChanged: if (hover.hovered && kind) Hints.show(root, label)
    onVisibleChanged: if (!visible) Hints.hide(root)
    Component.onDestruction: Hints.hide(root)
    Keys.onReturnPressed: clicked()
    Keys.onEnterPressed: clicked()
    Keys.onSpacePressed: clicked()
    Behavior on reveal { NumberAnimation { duration: Tokens.animMedium; easing.type: Easing.OutCubic } }
    Behavior on lampColor { ColorAnimation { duration: Tokens.animFast } }
    Rectangle {
        anchors.centerIn: parent
        width: root.dotSize; height: root.dotSize; radius: width / 2; antialiasing: true
        color: root.lampColor; opacity: root.reveal
        scale: .7 + .3 * root.reveal
    }
    Rectangle {
        anchors.centerIn: parent; width: 20; height: 20; radius: 10
        color: "transparent"; border.width: root.activeFocus ? 1 : 0
        border.color: Theme.withAlpha(root.lampColor, .65)
    }
    HoverHandler {
        id: hover
        blocking: false
        cursorShape: Qt.PointingHandCursor
        onHoveredChanged: hovered ? Hints.show(root, root.label) : Hints.hide(root)
    }
    MouseArea {
        anchors.fill: parent
        onPressed: Hints.hide(root)
        onClicked: root.clicked()
    }
}
