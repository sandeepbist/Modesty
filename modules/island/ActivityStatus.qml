import QtQuick
import qs.components
import qs.services
import qs.theme
Item {
    id:root
    property real selection:Activities.primary==="focus"?1:0
    Behavior on selection {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.InOutCubic}}
    Item {
        width:Activities.primaryWidth;height:parent.height;clip:true
        RecordingStatus {width:parent.width;height:parent.height;y:-height*root.selection;enabled:Activities.primary==="recording";visible:root.selection<1}
        FocusStatus {width:parent.width;height:parent.height;y:height*(1-root.selection);enabled:Activities.primary==="focus";visible:root.selection>0}
    }
    Item {
        id:secondary
        x:Activities.primaryWidth;width:40;height:parent.height
        visible:Activities.dual
        Rectangle {anchors.verticalCenter:parent.verticalCenter;width:1;height:14;color:Theme.withAlpha(Theme.text,.12)}
        Icon {anchors.centerIn:parent;icon:Activities.primary==="recording"?(FocusTimer.phase==="paused"?"pause":"timer"):"videocam";size:16;color:Activities.primary==="recording"?Theme.accent:Theme.red}
        TapHandler {onTapped:Activities.cycle()}
        HoverHandler {onHoveredChanged:hovered?Hints.show(secondary,Activities.primary==="recording"?"Show focus timer":"Show recording"):Hints.hide(secondary)}
        Accessible.role:Accessible.Button;Accessible.name:Activities.primary==="recording"?"Show focus timer":"Show recording"
    }
    WheelHandler {
        enabled:Activities.dual
        property real lastChange:0
        onWheel:event=>{if(Date.now()-lastChange>240&&Math.abs(event.angleDelta.y)>10){Activities.cycle();lastChange=Date.now();}event.accepted=true;}
    }
    Item {
        id:deviceSlot
        x:Activities.primaryWidth;width:40;height:parent.height;visible:Activities.headphones
        Rectangle {anchors.verticalCenter:parent.verticalCenter;width:1;height:14;color:Theme.withAlpha(Theme.text,.12)}
        StatusOrb {anchors.centerIn:parent}
        TapHandler {onTapped:IslandState.openMenu("bluetooth")}
        Accessible.role:Accessible.Button;Accessible.name:"Bluetooth devices"
    }
}
