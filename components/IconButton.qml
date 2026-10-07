import QtQuick
import QtQuick.Controls
import qs.theme
import qs.services

Item {
    id: root

    property string icon: ""
    property string label: ""
    property real size: 16
    property color color: Theme.text
    property color background: "transparent"

    signal clicked()

    implicitWidth: size + 16
    implicitHeight: size + 16
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: label || icon
    Keys.onSpacePressed: clicked()
    Keys.onReturnPressed: clicked()
    Keys.onEnterPressed: clicked()
    scale: mouse.pressed ? 0.96 : 1
    opacity: enabled ? 1 : 0.35

    Rectangle {
        anchors.fill: parent
        antialiasing: true
        radius: height / 2
        color: root.background
        border.width: root.activeFocus ? 1 : 0
        border.color: Theme.accent

        Rectangle {
            anchors.fill: parent
            antialiasing: true
            radius: parent.radius
            color: Theme.withAlpha(root.color, mouse.pressed ? 0.13 : mouse.containsMouse ? 0.065 : 0)
            Behavior on color { ColorAnimation { duration: Tokens.animFast } }
        }

        Behavior on color {
            ColorAnimation {
                duration: Tokens.animFast
            }

        }

    }

    Icon {
        anchors.centerIn: parent
        icon: root.icon
        size: root.size
        color: root.color
        Behavior on color { ColorAnimation { duration: Tokens.animFast } }
    }

    MouseArea {
        id: mouse

        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onEntered: Hints.show(root, root.label)
        onExited: Hints.hide(root)
        onPressed: Hints.hide(root)
        onClicked: root.clicked()
    }

    Behavior on scale {
        NumberAnimation {
            duration: mouse.pressed ? 90 : Tokens.animFast
            easing.type: Easing.OutCubic
        }

    }

}
