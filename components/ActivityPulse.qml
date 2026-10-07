import QtQuick
import qs.theme

Item {
    id: root
    property bool running: true
    implicitWidth: 14
    implicitHeight: 14

    Item {
        anchors.centerIn:parent;width:14;height:14
        RotationAnimator on rotation {from:0;to:360;duration:1800;loops:Animation.Infinite;running:root.visible&&root.running&&!Tokens.reducedMotion}
        Repeater {model:3
            Rectangle {
                required property int index
                readonly property real angle:(index*120-90)*Math.PI/180
                width:4-index*.55;height:width;radius:width/2
                x:7+Math.cos(angle)*4.4-width/2;y:7+Math.sin(angle)*4.4-height/2
                color:Theme.accent;opacity:1-index*.27;antialiasing:true
            }
        }
    }
}
