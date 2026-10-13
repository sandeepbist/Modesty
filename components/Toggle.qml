import QtQuick
import QtQuick.Controls
import qs.theme
AbstractButton {
    id:root
    checkable:true
    implicitWidth:34;implicitHeight:22
    hoverEnabled:true
    Accessible.role:Accessible.CheckBox
    Accessible.name:text
    opacity:enabled?1:.4
    HoverHandler {cursorShape:root.enabled?Qt.PointingHandCursor:Qt.ArrowCursor}
    background:Rectangle {
        x:0;y:2;width:root.width;height:18;radius:9
        color:root.checked?Theme.accent:Theme.withAlpha(Theme.text,.16)
        border.width:root.activeFocus?1:0;border.color:Theme.text
        Behavior on color {ColorAnimation {duration:Tokens.animFast}}
        Rectangle {
            id:thumb;x:thumbMotion.value;y:3;width:12;height:12;radius:6
            color:root.checked?Theme.bgSolid:Theme.subtext
            FrameSpring {id:thumbMotion;owner:root;targetValue:root.checked?thumb.parent.width-thumb.width-3:3}
            Behavior on color {ColorAnimation {duration:Tokens.animFast}}
        }
    }
    contentItem:Item {}
}
