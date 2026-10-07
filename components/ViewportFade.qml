import QtQuick
import qs.theme

// Soft viewport edges belong to the viewport, never its scrolling content.
Item {
    id:root
    property Flickable view:null
    property bool horizontal:false
    property real edge:14
    property color background:Theme.bgSolid
    parent:view
    anchors.fill:parent
    enabled:false;z:3
    Rectangle {
        width:root.horizontal?root.edge:root.width;height:root.horizontal?root.height:root.edge
        opacity:root.view&&(root.horizontal?!root.view.atXBeginning:!root.view.atYBeginning)?1:0
        gradient:Gradient {
            orientation:root.horizontal?Gradient.Horizontal:Gradient.Vertical
            GradientStop {position:0;color:root.background}
            GradientStop {position:1;color:Theme.withAlpha(root.background,0)}
        }
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
    }
    Rectangle {
        x:root.horizontal?root.width-root.edge:0;y:root.horizontal?0:root.height-root.edge
        width:root.horizontal?root.edge:root.width;height:root.horizontal?root.height:root.edge
        opacity:root.view&&(root.horizontal?!root.view.atXEnd:!root.view.atYEnd)?1:0
        gradient:Gradient {
            orientation:root.horizontal?Gradient.Horizontal:Gradient.Vertical
            GradientStop {position:0;color:Theme.withAlpha(root.background,0)}
            GradientStop {position:1;color:root.background}
        }
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
    }
}
