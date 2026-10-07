import QtQuick
import QtQuick.Shapes
import qs.theme
import "ControlGlyphs.js" as Glyphs

Item {
    id: root
    property string icon: ""
    property real size: 16
    property color color: Theme.text
    readonly property string outline: Glyphs.paths[icon] || ""
    implicitWidth: size; implicitHeight: size
    width: size; height: size
    // Vector geometry avoids font baseline drift at small control sizes.
    Shape {
        width: 24; height: 24; visible: !!root.outline
        scale: root.size / 24; transformOrigin: Item.TopLeft
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: root.color; strokeWidth: 1.8; fillColor: "transparent"
            capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
            PathSvg {path: root.outline}
        }
    }
    Text {
        anchors.fill: parent; visible: !root.outline
        text: root.icon; color: root.color
        renderType: Text.QtRendering
        font.family: Tokens.iconFont; font.pixelSize: root.size
        font.variableAxes: ({"FILL": 0, "wght": 400, "opsz": 20})
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
}
