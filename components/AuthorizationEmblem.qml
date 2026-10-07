import QtQuick
import QtQuick.Shapes
import qs.theme

Item {
    id:root
    implicitWidth:48;implicitHeight:48
    Shape {
        anchors.fill:parent;preferredRendererType:Shape.CurveRenderer
        ShapePath {
            fillColor:Theme.withAlpha(Theme.accent,.055);strokeColor:Theme.withAlpha(Theme.accent,.8);strokeWidth:1.5
            capStyle:ShapePath.RoundCap;joinStyle:ShapePath.RoundJoin
            PathSvg {path:"M24 5 C29 8 33 9 39 10 L39 23 C39 33 33 39 24 43 C15 39 9 33 9 23 L9 10 C15 9 19 8 24 5 Z"}
        }
        ShapePath {
            strokeColor:Theme.text;strokeWidth:1.6;fillColor:"transparent";capStyle:ShapePath.RoundCap;joinStyle:ShapePath.RoundJoin
            PathSvg {path:"M28 22 A4 4 0 1 0 20 22 A4 4 0 1 0 28 22 M24 26 L24 32"}
        }
    }
}
