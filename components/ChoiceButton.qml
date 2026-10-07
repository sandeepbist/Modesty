import QtQuick
import QtQuick.Controls
import qs.theme
AbstractButton {
    id:root
    property bool selected:false
    implicitHeight:34;implicitWidth:label.implicitWidth+22
    hoverEnabled:true
    background:Rectangle {radius:10;color:Theme.withAlpha(Theme.text,root.pressed?.09:root.hovered?.045:.018);border.width:1;border.color:root.selected||root.activeFocus?Theme.accent:Theme.withAlpha(Theme.text,.07);Behavior on color {ColorAnimation {duration:Tokens.animFast}}Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}}
    contentItem:PanelText {id:label;text:root.text;font.pixelSize:11;font.weight:Font.Medium;color:root.selected?Theme.accent:Theme.text;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
    HoverHandler {cursorShape:Qt.PointingHandCursor}
}
