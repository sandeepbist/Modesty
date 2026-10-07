import QtQuick
import Quickshell.Widgets
import qs.theme

ClippingRectangle {
    id: root

    property string source: ""
    property bool compact: false

    radius: 10
    color: compact ? "transparent" : Theme.surfaceSolid

    CrossfadeImage {
        id: img

        anchors.fill: parent
        source: root.source
    }

    Icon {
        anchors.centerIn: parent
        icon: "music_note"
        size: Math.min(24,Math.min(root.width,root.height)*.64)
        color: Theme.subtext
        visible: !img.ready && !root.compact
    }

    CompactGlyph {
        anchors.centerIn: parent
        glyph: "music"
        size: Math.min(root.width, root.height) * .78
        color: Theme.text
        visible: !img.ready && root.compact
    }

}
