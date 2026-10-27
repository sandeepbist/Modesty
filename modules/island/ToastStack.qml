import QtQuick
import QtQuick.Controls
import qs.services
import qs.components
import qs.theme
Item {
    id:root
    readonly property real viewportHeight:Math.min(height,parent?.viewportHeight??height)
    readonly property var incoming:Notifications.popups[0]??null
    property var shown:null
    property real presence:0
    onShownChanged: {
        if(shown)shown.popupHovered=hover.hovered;
        viewport.contentY=0;
        Notifications.popupHeight=card.implicitHeight;
    }
    function showIncoming():void {
        if(shown!==incoming){if(shown)shown.popupHovered=false;shown=incoming;}
        if(shown)shown.popupHovered=hover.hovered;
    }
    function settlePresentation():void {
        swap.stop();retreat.stop();showIncoming();presence=shown&&!shown.popupClosing?1:0;
    }
    function replace():void {if(Tokens.reducedMotion)settlePresentation();else{retreat.stop();swap.restart();}}
    onIncomingChanged:replace()
    Component.onCompleted:replace()
    Connections {target:Tokens;function onReducedMotionChanged(){if(Tokens.reducedMotion)root.settlePresentation();}}
    Connections {target:root.shown;function onPopupClosingChanged(){if(root.shown?.popupClosing){if(Tokens.reducedMotion)root.settlePresentation();else{swap.stop();retreat.restart();}}}}
    function revealFocus():void {
        const focused=root.Window.window?.activeFocusItem;
        let item=focused;
        while(item&&item!==card)item=item.parent;
        if(!item||focused===card)return;
        const top=focused.mapToItem(card,0,0).y;
        if(top<viewport.contentY)viewport.contentY=top;
        else if(top+focused.height>viewport.contentY+viewport.height)viewport.contentY=Math.min(top,top+focused.height-viewport.height);
    }
    Connections {target:root.Window.window;function onActiveFocusItemChanged(){root.revealFocus();}}
    SequentialAnimation {
        id:swap
        NumberAnimation {target:root;property:"presence";to:0;duration:root.presence>0?Tokens.animMedium:0;easing.type:Easing.InCubic}
        ScriptAction {script:root.showIncoming()}
        NumberAnimation {target:root;property:"presence";to:1;duration:Tokens.animMedium;easing.type:Easing.OutQuint}
    }
    NumberAnimation {id:retreat;target:root;property:"presence";to:0;duration:Tokens.animMedium;easing.type:Easing.InCubic}
    Flickable {
        id:viewport;objectName:"notificationScroll"
        onHeightChanged:Qt.callLater(root.revealFocus)
        anchors.fill:parent;anchors.bottomMargin:root.height-root.viewportHeight;contentHeight:card.implicitHeight;clip:true;boundsBehavior:Flickable.StopAtBounds
        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
        NotificationCard {
            id:card;objectName:"popupCard";width:parent.width;height:implicitHeight
            notification:root.shown;popup:true;interactive:!!root.shown&&!root.shown.popupClosing
            onImplicitHeightChanged:if(root.shown===root.incoming)Notifications.popupHeight=implicitHeight
            Component.onCompleted:Notifications.popupHeight=implicitHeight
            opacity:root.presence;transform:Translate {y:-6*(1-root.presence)}
            onDismissed:Notifications.dismiss(root.shown)
            HoverHandler {id:hover;onHoveredChanged:if(root.shown)root.shown.popupHovered=hovered}
            Component.onDestruction:if(root.shown)root.shown.popupHovered=false
        }
    }
}
