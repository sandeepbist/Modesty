import QtQuick
import QtQuick.Controls
import qs.theme

AbstractButton {
    id: root

    property bool primary: false

    implicitHeight: 34
    implicitWidth: Math.max(72, label.implicitWidth + 24)
    padding: 10
    topPadding: Math.min(padding, Math.max(2, (height - label.implicitHeight) / 2))
    bottomPadding: topPadding
    hoverEnabled: true
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    opacity: enabled ? 1 : 0.4
    scale: pressed ? 0.97 : 1

    background: Rectangle {
        radius: 12
        color: root.primary ? Theme.accent : Theme.surfaceSolid
        border.width: root.activeFocus ? 1 : 0
        border.color: Theme.accent
        // Theme already animates its semantic colors. Animate interaction tint
        // separately so light/dark switching cannot lag behind the label.
        Rectangle { anchors.fill: parent; radius: parent.radius; color: Theme.withAlpha(root.primary ? Theme.accentText : Theme.text, root.pressed ? 0.12 : root.hovered ? (root.primary ? 0.05 : 0.14) : 0); Behavior on color { ColorAnimation { duration: Tokens.animFast } } }

    }

    contentItem: PanelText {
        id: label

        text: root.text
        font.pixelSize: 12
        font.weight: Font.Medium
        color: root.primary ? Theme.accentText : Theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    Behavior on scale { enabled:!Tokens.reducedMotion; SpringMotion { epsilon:.002 } }

}
