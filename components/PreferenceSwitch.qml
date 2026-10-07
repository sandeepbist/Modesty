import QtQuick
import QtQuick.Controls
import qs.theme

Rectangle {
    id: root

    property string label: ""
    property string description: ""
    property bool checked: false

    signal toggled(bool checked)

    implicitHeight: Math.max(56, labels.implicitHeight + 24)
    radius: 12
    antialiasing: true
    color: Theme.surfaceSolid

    Column {
        id: labels
        x: 14
        width: Math.max(0, parent.width - 84)
        anchors.verticalCenter: parent.verticalCenter
        spacing: 4

        PanelText {
            width: parent.width
            text: root.label
            font.pixelSize: 12
            font.weight: Font.Medium
        }

        PanelText {
            width: parent.width
            visible: !!root.description
            text: root.description
            font.pixelSize: Tokens.captionSize
            color: Theme.subtext
            wrapMode: Text.WordWrap
            elide: Text.ElideNone
        }

    }

    Toggle {
        objectName: root.label
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        text: root.label
        checked: root.checked
        onToggled: root.toggled(checked)
    }
}
