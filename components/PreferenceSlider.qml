import QtQuick
import QtQuick.Controls
import qs.theme

Rectangle {
    id: root

    property string label: ""
    property string display: ""
    property real value: 0
    property real from: 0
    property real to: 1
    property real stepSize: 1
    property color backgroundColor: Theme.surfaceSolid

    signal moved(real value)

    implicitHeight: 60
    radius: 12
    antialiasing: true
    color: root.backgroundColor
    opacity: enabled ? 1 : 0.4

    PanelText {
        x: 14
        y: 11
        width: Math.max(0, root.width - 36 - readout.implicitWidth)
        text: root.label
        font.pixelSize: 12
        font.weight: Font.Medium
    }

    PanelText {
        id: readout
        anchors.right: parent.right
        anchors.rightMargin: 14
        y: 11
        text: root.display
        font.pixelSize: Tokens.captionSize
        color: Theme.accent
    }

    Slider {
        id: control

        x: 14
        y: 31
        width: Math.max(0, parent.width - 28)
        height: 22
        from: root.from
        to: root.to
        stepSize: root.stepSize
        wheelEnabled: true
        Binding { target: control; property: "value"; value: root.value; when: !control.pressed; restoreMode: Binding.RestoreNone }
        Accessible.name: root.label
        hoverEnabled: true
        HoverHandler { cursorShape: Qt.PointingHandCursor }
        onMoved: root.moved(value)

        background: Rectangle {
            x: control.leftPadding
            y: control.topPadding + control.availableHeight / 2 - height / 2
            width: control.availableWidth
            height: 4
            radius: 2
            color: Theme.withAlpha(Theme.text, 0.1)

            Rectangle {
                width: parent.width * control.visualPosition
                height: parent.height
                radius: 2
                color: Theme.accent
            }

        }

        handle: Rectangle {
            x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
            y: control.topPadding + control.availableHeight / 2 - height / 2
            width: 12
            height: 12
            radius: 6
            color: Theme.accent
            antialiasing: true
            scale: control.pressed ? 1.15 : control.hovered ? 1.08 : 1

            Behavior on scale {
                NumberAnimation {
                    duration: Tokens.animFast
                }

            }

        }

    }

}
