import QtQuick
import QtQuick.Controls
import qs.services
import qs.components
import qs.theme
Item {
    id:root
    readonly property var incoming:Notifications.popups[0]??null
    property var shown:null
    property real presence:0
    onIncomingChanged: {retreat.stop();swap.restart();}
    Component.onCompleted: {shown=incoming;presence=1;}
    Connections {target:root.shown;function onPopupClosingChanged(){if(root.shown?.popupClosing){swap.stop();retreat.restart();}}}
    SequentialAnimation {
        id:swap
        NumberAnimation {target:root;property:"presence";to:0;duration:root.shown?Tokens.animFast:0;easing.type:Easing.InCubic}
        ScriptAction {script:{if(root.shown)root.shown.popupHovered=false;root.shown=root.incoming;}}
        NumberAnimation {target:root;property:"presence";to:1;duration:Tokens.animMedium;easing.type:Easing.OutCubic}
    }
    NumberAnimation {id:retreat;target:root;property:"presence";to:0;duration:Tokens.animMedium;easing.type:Easing.InCubic}
    Flickable {
        anchors.fill:parent;contentHeight:card.implicitHeight;clip:true;boundsBehavior:Flickable.StopAtBounds
        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
        NotificationCard {
            id:card;width:parent.width;height:implicitHeight
            notification:root.shown;popup:true;interactive:!!root.shown&&!root.shown.popupClosing
            onImplicitHeightChanged:if(root.shown===root.incoming)Notifications.popupHeight=implicitHeight
            Component.onCompleted:Notifications.popupHeight=implicitHeight
            opacity:root.presence;transform:Translate {y:-8*(1-root.presence)}
            onDismissed:Notifications.dismiss(root.shown)
            HoverHandler {onHoveredChanged:if(root.shown)root.shown.popupHovered=hovered}
            Component.onDestruction:if(root.shown)root.shown.popupHovered=false
        }
    }
}
