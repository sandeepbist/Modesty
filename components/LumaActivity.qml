import QtQuick
import QtQuick.Shapes
import qs.theme

// A continuous line responds to real work; it rests flat when motion is reduced.
Item {
    id:root
    property bool active:true
    property real phase:0
    implicitWidth:34;implicitHeight:24
    Shape {
        anchors.fill:parent;preferredRendererType:Shape.CurveRenderer
        ShapePath {
            strokeColor:Theme.accent;strokeWidth:1.7;fillColor:"transparent"
            capStyle:ShapePath.RoundCap
            startX:2;startY:root.height/2
            PathCubic {
                x:root.width-2;y:root.height/2
                control1X:root.width*.28;control1Y:root.height/2+Math.sin(root.phase)*root.height*.28
                control2X:root.width*.72;control2Y:root.height/2-Math.sin(root.phase)*root.height*.28
            }
        }
    }
    NumberAnimation on phase {
        running:root.active&&root.visible&&!Tokens.reducedMotion
        from:0;to:Math.PI*2;duration:1600;loops:Animation.Infinite
    }
}
