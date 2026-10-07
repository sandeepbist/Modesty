import QtQuick
import QtQuick.Effects
import Quickshell.Widgets
import qs.services
import qs.theme
import qs.components
Item {
    id: root
    property real restingWidth:stage==="clock"?Preferences.collapsedWidth+(Preferences.showSeconds?20:0):Preferences.barHeight
    property string stage
    signal activated(real localX)
    property string panel: "idle"
    property real targetWidth: 33
    property real targetHeight: Preferences.barHeight
    readonly property var panelSources: ({dropcue:"DropCue.qml",files:"FileDropMenu.qml",activities:"ActivityStatus.qml",clock:"WeekCard.qml", context:"ContextPanel.qml",toast:"ToastStack.qml",calendar:"CalendarMenu.qml",media:"MediaCard.qml",privacy:"PrivacyMenu.qml",quicksettings:"ControlCenter.qml",themes:"ThemesMenu.qml",wallpapers:"WallpaperMenu.qml",power:"PowerMenu.qml",launcher:"LauncherMenu.qml",authentication:"AuthenticationMenu.qml",unlockcheck:"UnlockCheckMenu.qml"})
    property bool expanded: panel !== "idle"
    property bool inlineContext: false
    property bool continuousWidth: false
    readonly property bool resizing: widthMotion.running || heightMotion.running
    readonly property alias capsule: capsule
    readonly property Item inputRegion: Item {
        parent: root
        Component.onCompleted: parent = root
        x: -6
        width: root.width + 12
        height: root.height + 7
    }
    default property alias restingContent: rest.data
    readonly property bool nearRest: width <= restingWidth * 1.1 && height <= Preferences.barHeight * 1.1
    readonly property bool restingHovered: !expanded && nearRest && IslandState.pointerInside && IslandState.hoverStage === stage
    readonly property bool outgoingContentVisible: {
        if(panel==="idle")return false;
        for(let i=0;i<contentPanes.count;i++) {
            const pane=contentPanes.itemAt(i);
            if(pane&&!pane.selected&&pane.opacity>.01)return true;
        }
        return false;
    }
    scale: 1
    property real hoverLift: restingHovered ? Preferences.hoverLift : 0
    Behavior on hoverLift { NumberAnimation { duration:Tokens.reducedMotion?0:170;easing.type:Easing.OutCubic } }
    function diagnostics(): var {
        const entries=[];for(let i=0;i<contentPanes.count;i++){const p=contentPanes.itemAt(i);entries.push({name:p.modelData,selected:p.selected,opacity:p.opacity,enabled:p.enabled,loaded:!!p.item,status:p.status,width:p.width,height:p.height,input:p.item?.diagnostics?p.item.diagnostics():null});}
        return {name:stage,panel,x,y,width,height,targetWidth,targetHeight,radius:capsule.radius,visible,scale,hoverLift,restingHovered,restWidth:rest.width,restHeight:rest.height,restOpacity:rest.opacity,entries};
    }
    width: targetWidth; height: targetHeight
    // Native velocity continuity keeps a new target from restarting the gesture.
    Behavior on width { enabled:!Tokens.reducedMotion&&!root.continuousWidth; SmoothedAnimation { id:widthMotion; velocity:-1; duration:root.expanded?Tokens.morphDuration:Tokens.collapseDuration; reversingMode:SmoothedAnimation.Immediate } }
    Behavior on height { enabled:!Tokens.reducedMotion; SmoothedAnimation { id:heightMotion; velocity:-1; duration:root.expanded?Tokens.morphDuration:Tokens.collapseDuration; reversingMode:SmoothedAnimation.Immediate } }
    RectangularShadow { anchors.fill: outline; radius: outline.radius; blur: root.expanded ? 24 : root.restingHovered ? 16 : 10; offset.y: root.expanded ? 7 : root.restingHovered ? 6 : 3; color: "#65000000"; visible: Preferences.shadows; cached: false
        Behavior on blur { NumberAnimation { duration: Tokens.animMedium } }
        Behavior on offset.y { NumberAnimation { duration: Tokens.animMedium } }
    }
    Rectangle {
        id: outline
        x: 0; y: root.hoverLift
        width: root.width; height: root.height
        radius: capsule.radius
        color: Theme.bgSolid; antialiasing:true
        border.width: 1; border.pixelAligned:false; border.color:Theme.withAlpha(Theme.text,.055)
    }
    ClippingRectangle {
        id: capsule
        anchors.fill: parent
        transform: Translate { y: root.hoverLift }
        contentInsideBorder: false
        antialiasing: true
        // Shape follows the aperture on every frame, including interrupted closes.
        radius: Math.max(0, Math.min(Preferences.expandedRadius, width / 2, height / 2))
        color: "transparent"
        border.width: 0
        SurfaceLighting {anchors.fill:parent;radius:capsule.radius;active:root.expanded;visible:root.expanded;interactive:true;focused:root.panel==="authentication"}
        Item { id: rest
            width:Math.min(root.width,root.restingWidth)
            height: Preferences.barHeight
            x: root.stage === "media" ? parent.width - width : root.stage === "controls" ? 0 : (parent.width - width) / 2
            opacity: !root.expanded && root.height <= Preferences.barHeight * 1.1 ? 1 : 0
            visible: opacity > 0; enabled: !root.expanded && root.nearRest
            Behavior on opacity { NumberAnimation { duration: Tokens.animFast } }
        }
        Repeater {
            id: contentPanes
            model: ["clock", "activities", "context", "dropcue", "files", "toast", "calendar", "media", "privacy", "quicksettings", "themes", "wallpapers", "power", "launcher", "authentication", "unlockcheck"]
            delegate: Loader {
                id: content
                required property string modelData
                readonly property bool selected: root.expanded && root.panel === modelData && !(modelData === "context" && root.inlineContext)
                property real outgoingScale:1
                property real outgoingReveal:1
                property bool presented:false
                property real heldWidth: IslandState.sizes[modelData]?.[0] ?? 33
                property real heldHeight: IslandState.sizes[modelData]?.[1] ?? 33
                function resizeContent() { if (selected) { heldWidth = root.targetWidth; heldHeight = root.targetHeight; if(presentationScale>=.995)presented=true; } }
                onSelectedChanged: { if(!selected){outgoingScale=visibleScale;outgoingReveal=revealAmount;presented=false;}else if (modelData === "launcher" && item) item.beginSearch(); Qt.callLater(resizeContent); Qt.callLater(focusContent); }
                Connections { target: root; enabled: content.selected; function onTargetWidthChanged() { Qt.callLater(content.resizeContent); } function onTargetHeightChanged() { Qt.callLater(content.resizeContent); } }
                Component.onCompleted: Qt.callLater(resizeContent)
                readonly property real inset: ["context","activities","dropcue"].includes(modelData) ? 0 : Preferences.innerPadding
                width: Math.max(0, heldWidth - inset * 2); height: Math.max(0, heldHeight - inset * 2)
                x: root.stage === "media" ? parent.width - heldWidth + inset : root.stage === "controls" ? inset : (parent.width - width) / 2
                y: inset
                readonly property real presentationScale:Math.max(0,Math.min(1,(root.width-inset*2)/Math.max(1,width),(root.height-inset*2)/Math.max(1,height)))
                readonly property real visibleScale:presented?1:presentationScale
                onPresentationScaleChanged:if(selected&&presentationScale>=.995)presented=true
                readonly property real revealAmount: {
                    if(presented)return 1;
                    const t=Math.max(0,Math.min(1,(presentationScale-.55)/.43));
                    return t*t*(3-2*t);
                }
                transform:Scale {
                    origin.x:root.stage==="media"?content.width:root.stage==="controls"?0:content.width/2
                    xScale:content.selected?content.visibleScale:content.outgoingScale
                    yScale:xScale
                }
                source: root.panelSources[modelData]
                active: selected || opacity > 0 || (root.stage === "clock" && ["clock","launcher"].includes(modelData)) || (root.stage === "controls" && modelData === "quicksettings")
                asynchronous: !["launcher", "wallpapers", "dropcue", "files"].includes(modelData)
                visible: opacity > 0 || (selected && modelData === "launcher")
                enabled: selected && (modelData === "launcher" || opacity > 0.7)
                // Render the settled layout once and fit it into the moving aperture.
                // Geometry drives the reveal; no per-frame opacity animation restarts.
                property real exposure:selected&&status===Loader.Ready&&!root.outgoingContentVisible?1:0
                Behavior on exposure {NumberAnimation {duration:Tokens.reducedMotion?0:content.selected?Tokens.animFast:Math.round(70/Preferences.motionSpeed);easing.type:Easing.OutCubic}}
                opacity:exposure*(selected?revealAmount:outgoingReveal)
                z: selected ? 1 : 0
                function focusContent(): void { if (enabled && item && IslandState.menuOpen) item.forceActiveFocus(); }
                onEnabledChanged: Qt.callLater(focusContent)
                onLoaded: Qt.callLater(focusContent)
            }
        }
    }
    // Keep pointer geometry still while the visible surface settles under it.
    HoverHandler { id: hover; margin: 6; blocking: false; onHoveredChanged: IslandState.hover(root.stage, hovered) }
    MouseArea {
        parent: root
        Component.onCompleted: parent = root
        x: -6; y: 0; width: root.width + 12; height: root.height + 7
        enabled: (!root.expanded && root.nearRest) || root.panel === "context"
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.PointingHandCursor
        onClicked: mouse => root.activated(mouse.x - 6)
    }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: IslandState.menuOpen ? IslandState.dismissCurrent() : IslandState.openMenu("quicksettings") }
}
