import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.services

// Hyprland initially enters a drag at the native surface's centre. Keep that
// point inside the clock's input mask, without resizing the visual island layer.
PanelWindow {
    id:root
    required property var sourceIsland
    readonly property var clock:sourceIsland.surface.clockStage
    property bool holding:false
    property bool completing:false
    property rect heldBox:Qt.rect(0,0,1,1)
    readonly property rect liveBox: {
        clock.x;clock.width;clock.hoverLift;sourceIsland.surface.x;sourceIsland.surface.y;sourceIsland.surface.width;
        const p=clock.mapToItem(sourceIsland.surface.parent,-6,clock.hoverLift);
        return Qt.rect(Math.floor(p.x),Math.floor(p.y),Math.ceil((clock.width+12)*Preferences.uiScale),Math.ceil((Preferences.barHeight+7)*Preferences.uiScale));
    }
    readonly property rect box:holding||completing?heldBox:liveBox
    screen:sourceIsland.screen
    color:"transparent"
    implicitWidth:box.width;implicitHeight:box.height
    exclusionMode:ExclusionMode.Ignore
    anchors {top:true;left:true}
    margins {left:root.box.x;top:root.box.y}
    WlrLayershell.namespace:"modesty-island-drop"
    WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.keyboardFocus:WlrKeyboardFocus.None
    visible:!Session.locked&&!Session.secure&&!sourceIsland.hiddenByFullscreen&&sourceIsland.surface.visible&&Startup.progress>.99
        &&(holding||completing||(clock.panel==="idle"&&clock.nearRest)||clock.panel==="context")
    mask:Region {item:clockInput;radius:root.clock.capsule.radius*Preferences.uiScale}
    onVisibleChanged:if(!visible){holding=false;completing=false;IslandDrop.dragging=false;IslandState.hover("clock",false);}
    Item {
        id:hit;anchors.fill:parent
        // Capture the visible clock, leaving neighbouring pill edges untouched.
        Item {id:clockInput;x:6*Preferences.uiScale;width:parent.width-12*Preferences.uiScale;height:Preferences.barHeight*Preferences.uiScale}
        HoverHandler {onHoveredChanged:IslandState.hover("clock",hovered)}
        MouseArea {
            anchors.fill:parent;acceptedButtons:Qt.LeftButton|Qt.RightButton;cursorShape:Qt.PointingHandCursor
            onClicked:mouse=>{
                if(mouse.button===Qt.RightButton)IslandState.menuOpen?IslandState.dismissCurrent():IslandState.openMenu("quicksettings");
                else {const p=root.clock.mapFromItem(root.sourceIsland.surface.parent,root.box.x+mouse.x,root.box.y+mouse.y);root.clock.activated(p.x);}
            }
        }
        DropArea {
            anchors.fill:parent;z:100;enabled:root.visible&&!IslandDrop.busy
            onEntered:drag=>{
                drag.accepted=drag.hasUrls&&!!(drag.supportedActions&Qt.CopyAction);
                if(drag.accepted){root.heldBox=root.liveBox;root.holding=true;IslandDrop.dragging=true;drag.accept(Qt.CopyAction);}
            }
            onExited:{root.holding=false;IslandDrop.dragging=false;}
            onDropped:drop=>{
                root.completing=true;
                if(IslandDrop.accept(drop.urls))drop.accept(Qt.CopyAction);else drop.accepted=false;
                root.holding=false;IslandDrop.dragging=false;
                Qt.callLater(()=>root.completing=false);
            }
        }
    }
}
