import QtQuick
import QtQuick.Shapes
import qs.theme

Item {
    id: root
    property string glyph: "wifi"
    property real size: 16
    property color color: Theme.text
    implicitWidth: size; implicitHeight: size
    width: size; height: size
    Shape {
        width: 24; height: 24
        scale: root.size / 24; transformOrigin: Item.TopLeft
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: root.glyph === "wifi" ? root.color : "transparent"
            strokeWidth: 2; capStyle: ShapePath.RoundCap
            fillColor: root.glyph === "wifi" ? "transparent" : root.color
            PathSvg {
                path: root.glyph === "wifi"
                    ? "M3.5 9.5 Q12 2.5 20.5 9.5 M7.3 13.2 Q12 9.3 16.7 13.2"
                    : "M9 5.5 Q9 4.7 9.8 4.5 L19 2.5 Q20 2.3 20 3.4 L20 15.9 C20 18.5 14 19.9 14 17 C14 15.4 16.2 14.4 18 14.6 L18 7.5 L11 9 L11 18 C11 20.7 5 22.1 5 19.1 C5 17.5 7.2 16.5 9 16.7 Z"
            }
        }
        ShapePath {
            strokeColor: "transparent"
            fillColor: root.glyph === "wifi" ? root.color : "transparent"
            PathSvg {path: "M13.5 17.4 A1.5 1.5 0 1 1 10.5 17.4 A1.5 1.5 0 1 1 13.5 17.4 Z"}
        }
    }
}
