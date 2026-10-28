import QtQuick
import QtQuick.Window
import qs.components
import qs.services
import qs.theme
Item {
    id:root
    property real dockProgress:0
    property bool condensed:false
    readonly property real condensedMinimumWidth:Activities.primary==="focus"?focusStatus.condensedMinimumWidth:recordingStatus.condensedMinimumWidth
    readonly property real minimumViewportWidth:Activities.primaryWidth-34
    property real selection:Activities.primary==="focus"?1:0
    Behavior on selection {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.InOutCubic}}
    function revealFocus():void {
        const item=root.Window.window?.activeFocusItem;
        if(!item)return;
        let ancestor=item;
        while(ancestor&&ancestor!==root)ancestor=ancestor.parent;
        if(!ancestor)return;
        const p=item.mapToItem(viewport.contentItem,0,0);
        viewport.contentX=Math.max(0,Math.min(viewport.contentWidth-viewport.width,p.x<viewport.contentX?p.x:Math.max(viewport.contentX,p.x+item.width-viewport.width)));
    }
    Connections {target:root.Window.window;function onActiveFocusItemChanged(){Qt.callLater(root.revealFocus);}}
    onWidthChanged:Qt.callLater(revealFocus)
    onSelectionChanged:Qt.callLater(revealFocus)
    Flickable {
        id:viewport;objectName:"activityViewport"
        anchors.fill:parent;clip:true
        contentWidth:root.condensed?root.width:Activities.width;contentHeight:height
        onContentWidthChanged:Qt.callLater(root.revealFocus)
        flickableDirection:Flickable.HorizontalFlick;boundsBehavior:Flickable.StopAtBounds
        Item {
            width:root.condensed?root.width:Activities.primaryWidth;height:viewport.height;clip:true
            RecordingStatus {id:recordingStatus;condensed:root.condensed;width:parent.width;height:parent.height;y:-height*root.selection;enabled:Activities.recording&&Activities.primary==="recording";visible:root.selection<1}
            FocusStatus {id:focusStatus;condensed:root.condensed;width:parent.width;height:parent.height;y:height*(1-root.selection);enabled:Activities.focus&&Activities.primary==="focus";visible:root.selection>0}
        }
        Item {
            x:Activities.primaryWidth;width:40;height:viewport.height
            visible:Activities.dual&&!root.condensed;enabled:visible
            Rectangle {anchors.verticalCenter:parent.verticalCenter;width:1;height:14;color:Theme.withAlpha(Theme.text,.12)}
            IconButton {objectName:"activitySelector";anchors.centerIn:parent;icon:Activities.primary==="recording"?(FocusTimer.phase==="paused"?"pause":"timer"):"videocam";size:16;color:Activities.primary==="recording"?Theme.accent:Theme.red;label:Activities.primary==="recording"?"Show focus timer":"Show recording";onClicked:Activities.cycle()}
        }
        Item {
            id:deviceSlot;objectName:"activityDevice"
            x:Activities.primaryWidth;width:40;height:viewport.height;visible:Activities.headphones&&!root.condensed;enabled:visible
            activeFocusOnTab:true
            Rectangle {anchors.verticalCenter:parent.verticalCenter;width:1;height:14;color:Theme.withAlpha(Theme.text,.12)}
            Rectangle {anchors.fill:parent;anchors.margins:2;radius:height/2;color:"transparent";border.width:deviceSlot.activeFocus?1:0;border.color:Theme.accent}
            StatusOrb {anchors.centerIn:parent;deviceOnly:true;dockProgress:root.dockProgress}
            MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:IslandState.openMenu("bluetooth")}
            Keys.onReturnPressed:IslandState.openMenu("bluetooth")
            Keys.onSpacePressed:IslandState.openMenu("bluetooth")
            Accessible.role:Accessible.Button;Accessible.name:"Bluetooth devices"
            Accessible.onPressAction:IslandState.openMenu("bluetooth")
        }
    }
    WheelHandler {
        enabled:Activities.dual
        property real lastChange:0
        onWheel:event=>{if(Date.now()-lastChange>240&&Math.abs(event.angleDelta.y)>10){Activities.cycle();lastChange=Date.now();}event.accepted=true;}
    }
}
