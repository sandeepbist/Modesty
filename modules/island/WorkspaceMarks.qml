import QtQuick
import QtQuick.Controls
import Quickshell.Hyprland
import qs.services
import qs.theme
import qs.components

Flickable {
    id: root
    property var monitor: null
    property var workspaces: Hyprland.workspaces.values
    function ordinary(workspace):bool {
        return !!workspace && workspace.id!==-99 && workspace.name!=="special" && !workspace.name.startsWith("special:");
    }
    readonly property var members: workspaces.filter(w=>ordinary(w)&&!!monitor&&w.monitor===monitor).slice().sort((a,b)=>a.id-b.id||a.name.localeCompare(b.name))
    readonly property int activeIndex: members.indexOf(monitor?.activeWorkspace)
    readonly property int targetPitch:20
    readonly property real preferredWidth:Math.min(5*targetPitch,contentWidth)
    readonly property real maximumScroll:Math.max(0,contentWidth-width)
    readonly property bool nativeScroll:dragging||flicking
    property real scrollTarget:0
    property bool revealPending:false
    FrameSpring {id:selectorMotion;owner:root.parent;targetValue:root.activeIndex<0?0:root.activeIndex*root.targetPitch+root.targetPitch/2;positionTolerance:.01}
    FrameSpring {
        id:scrollMotion;owner:root.parent;targetValue:root.scrollTarget;positionTolerance:.01
        enabled:available&&!root.nativeScroll
        onValueChanged:if(!root.nativeScroll)root.contentX=Math.max(0,Math.min(root.maximumScroll,value))
    }
    function scrollTo(position:real):void {
        scrollTarget=Math.max(0,Math.min(maximumScroll,position));
    }
    function revealActive():void {
        if(nativeScroll){revealPending=true;return;}
        revealPending=false;
        if(activeIndex<0){scrollTo(contentX);return;}
        const x=activeIndex*targetPitch;
        scrollTo(x<contentX?x:x+targetPitch>contentX+width?x+targetPitch-width:contentX);
    }
    function activate(workspace):void {
        if(Session.isLocked()||Session.secure||!members.includes(workspace))return;
        workspace.activate();
    }
    onActiveIndexChanged:Qt.callLater(revealActive)
    onMembersChanged:Qt.callLater(revealActive)
    onWidthChanged:Qt.callLater(revealActive)
    onMaximumScrollChanged: {
        if(!nativeScroll)contentX=Math.max(0,Math.min(maximumScroll,contentX));
        scrollTarget=Math.max(0,Math.min(maximumScroll,scrollTarget));
        Qt.callLater(revealActive);
    }
    onNativeScrollChanged: {
        if(nativeScroll)scrollMotion.reset(contentX);
        else {
            scrollTarget=Math.max(0,Math.min(maximumScroll,contentX));
            scrollMotion.reset(scrollTarget);
            if(revealPending)Qt.callLater(revealActive);
        }
    }
    contentWidth:members.length*targetPitch
    contentHeight:height
    boundsBehavior:Flickable.StopAtBounds
    clip:true
    WheelHandler {onWheel:event=>{root.cancelFlick();root.scrollTo(root.scrollTarget-event.angleDelta.y/8);event.accepted=true;}}
    Rectangle {
        objectName:"workspaceSelector"
        x:selectorMotion.value-width/2;y:(root.height-height)/2
        width:8;height:4;radius:2;antialiasing:true
        visible:root.activeIndex>=0
        color:root.members[root.activeIndex]?.urgent?Theme.red:Theme.withAlpha(Theme.text,.95)
    }
    Repeater {
        model:root.members
        AbstractButton {
            id:mark
            required property var modelData
            required property int index
            x:index*root.targetPitch;width:root.targetPitch;height:root.height
            activeFocusOnTab:true
            Accessible.name:"Workspace "+modelData.name+(root.monitor?.activeWorkspace===modelData?", active":"")+(modelData.urgent?", urgent":"")
            onClicked:root.activate(modelData)
            onActiveFocusChanged:if(activeFocus)root.scrollTo(x-root.width/2+width/2)
            background:Rectangle {anchors.centerIn:parent;width:mark.activeFocus?12:0;height:20;radius:5;color:"transparent";border.width:mark.activeFocus?1:0;border.color:Theme.accent}
            contentItem:Item {
                Rectangle {anchors.centerIn:parent;width:4;height:4;radius:2;antialiasing:true;color:mark.modelData.urgent?Theme.red:Theme.withAlpha(Theme.text,.35)}
            }
        }
    }
}
