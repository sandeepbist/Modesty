import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.services

// Hyprland initially enters a drag at the native surface's centre. Reserve the
// cue width before entry so the native surface stays still while the pill grows.
PanelWindow {
    id:root
    required property var sourceIsland
    readonly property var clock:sourceIsland.surface.clockStage
    readonly property Item clockHit:sourceIsland.surface.clockHitRegion??clock
    property bool holding:false
    property bool completing:false
    property rect heldBox:Qt.rect(0,0,1,1)
    readonly property rect liveBox: {
        clockHit.x;clockHit.width;clockHit.y;sourceIsland.surface.x;sourceIsland.surface.y;sourceIsland.surface.width;
        const presentedWidth=root.interactive?clockHit.width:clock.restingWidth;
        const width=Math.max(presentedWidth,(sourceIsland.surface.dockProgress??0)>0?clockHit.width:IslandState.sizes.dropcue[0]);
        const p=clockHit.mapToItem(sourceIsland.surface.parent,(clockHit.width-width)/2-6,0);
        return Qt.rect(Math.floor(p.x),Math.floor(p.y),Math.ceil((width+12)*Preferences.uiScale),Math.ceil((Preferences.barHeight+7)*Preferences.uiScale));
    }
    function hold():void {
        if(!holding&&!completing)heldBox=liveBox;
        holding=true;
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
    onBoxChanged:root.updatesEnabled=true
    onInteractiveChanged:root.updatesEnabled=true
    onWidthChanged:root.updatesEnabled=true
    onHeightChanged:root.updatesEnabled=true
    onScreenChanged:root.updatesEnabled=true
    onDevicePixelRatioChanged:root.updatesEnabled=true
    onBackingWindowVisibleChanged:root.updatesEnabled=true
    onWindowConnected:root.updatesEnabled=true
    onWindowTransformChanged:root.updatesEnabled=true
    onColorChanged:root.updatesEnabled=true
    onMaskChanged:root.updatesEnabled=true
    // Keep the native surface mapped; use an empty input region while another
    // panel is active so rapid drops do not race surface remapping.
    visible:!Session.locked&&!Session.secure&&!!sourceIsland.screen&&!sourceIsland.hiddenByFullscreen&&sourceIsland.surface.visible&&Startup.progress>.99
    readonly property bool interactive:visible&&(holding||completing||((sourceIsland.surface.dockProgress??0)>0)||(clock.panel==="idle"&&clock.nearRest)||clock.panel==="context")
    mask:Region {
        item:root.interactive?clockInput:null;radius:root.clock.capsule.radius*Preferences.uiScale
        onItemChanged:root.updatesEnabled=true
        onRadiusChanged:if(item)root.updatesEnabled=true
    }
    onVisibleChanged:{root.updatesEnabled=true;if(!visible){holding=false;completing=false;IslandDrop.endDrag(root);IslandState.hover("clock",false);}}
    Connections {
        target:hit.Window.window
        function onExposed() {root.updatesEnabled=true;}
        function onAfterAnimating() {root.updatesEnabled=false;}
    }
    Item {
        id:hit;anchors.fill:parent
        // Capture the visible clock, leaving neighbouring pill edges untouched.
        Item {id:clockInput;x:(parent.width-width)/2;width:root.holding||root.completing?parent.width-12*Preferences.uiScale:root.clockHit.width*Preferences.uiScale;height:root.holding||root.completing?parent.height:Preferences.barHeight*Preferences.uiScale}
        HoverHandler {enabled:root.interactive;onHoveredChanged:IslandState.hover("clock",hovered)}
        MouseArea {
            anchors.fill:parent;enabled:root.interactive;acceptedButtons:Qt.LeftButton|Qt.RightButton;cursorShape:Qt.PointingHandCursor
            onClicked:mouse=>{
                if(mouse.button===Qt.RightButton)IslandState.menuOpen?IslandState.dismissCurrent():IslandState.openMenu("quicksettings");
                else {const p=root.clock.mapFromItem(root.sourceIsland.surface.parent,root.box.x+mouse.x,root.box.y+mouse.y);root.clock.activated(p.x);}
            }
        }
        DropArea {
            anchors.fill:parent;z:100;enabled:root.interactive&&(root.completing||!IslandDrop.busy)
            // Clearing the cue changes interactive; finish after its binding settles.
            onEnabledChanged:if(!enabled)Qt.callLater(()=>{if(!enabled){root.holding=false;IslandDrop.endDrag(root);}})
            onEntered:drag=>{
                drag.accepted=drag.hasUrls&&!!(drag.supportedActions&Qt.CopyAction);
                if(drag.accepted){root.hold();IslandDrop.beginDrag(root);drag.accept(Qt.CopyAction);}
            }
            onExited:{root.holding=false;IslandDrop.endDrag(root);}
            onDropped:drop=>{
                root.completing=true;
                if(IslandDrop.accept(drop.urls))drop.accept(Qt.CopyAction);else drop.accepted=false;
                root.holding=false;IslandDrop.endDrag(root);
                Qt.callLater(()=>root.completing=false);
            }
        }
    }
}
