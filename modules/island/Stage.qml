import QtQuick
import QtQuick.Effects
import Quickshell.Widgets
import qs.services
import qs.theme
import qs.components
Item {
    id: root
    property real restingWidth:stage==="clock"?Preferences.collapsedWidth+(Preferences.showSeconds?20:0):Preferences.barHeight
    property var presentation: null
    property bool externalDecoration: false
    property bool restingContentInteractive: false
    readonly property real dockProgress: presentation?.progress ?? 0
    readonly property real headerInset: presentation?.header ?? 0
    readonly property real bodyApertureWidth: width
    readonly property real bodyApertureHeight: Math.max(0,height-headerInset)
    readonly property real naturalWidth: Math.max(0,Math.min(maximumWidth,Math.max(Math.min(restingWidth,targetWidth),apertureWidth)))
    readonly property real naturalHeight: Math.max(0,Math.min(maximumHeight,Math.max(Math.min(Preferences.barHeight,targetHeight),apertureHeight)))
    property string stage
    signal activated(real localX)
    property string panel: "idle"
    property real targetWidth: 33
    property real targetHeight: Preferences.barHeight
    property real maximumWidth: Infinity
    property real maximumHeight: Infinity
    readonly property var panelSources: ({dropcue:"DropCue.qml",files:"FileDropMenu.qml",notes:"NotesMenu.qml",clock:"WeekCard.qml", context:"ContextPanel.qml",toast:"ToastStack.qml",calendar:"CalendarMenu.qml",media:"MediaCard.qml",privacy:"PrivacyMenu.qml",quicksettings:"ControlCenter.qml",themes:"ThemesMenu.qml",wallpapers:"WallpaperMenu.qml",power:"PowerMenu.qml",launcher:"LauncherMenu.qml",authentication:"AuthenticationMenu.qml",unlockcheck:"UnlockCheckMenu.qml"})
    property bool expanded: panel !== "idle"
    property bool inlineContext: false
    property bool continuousWidth: false
    readonly property bool resizing: widthMotion.running || levelWidthMotion.running || heightMotion.running
    readonly property alias capsule: capsule
    readonly property Item popupInputRegion: {
        for (let i = 0; i < contentPanes.count; i++) {
            const pane = contentPanes.itemAt(i);
            if (pane?.selected && pane.enabled && pane.item?.popupInputRegion) return pane.item.popupInputRegion;
        }
        return null;
    }
    readonly property Item inputRegion: Item {
        parent: root
        Component.onCompleted: parent = root
        x: -6
        width: root.width > 0 && root.height > 0 ? root.width + 12 : 0
        height: width > 0 ? root.height + 7 : 0
    }
    default property alias restingContent: rest.data
    readonly property bool nearRest: width <= restingWidth * 1.1 && height <= Preferences.barHeight * 1.1
    readonly property bool restingHovered: !expanded && nearRest && IslandState.pointerInside && IslandState.hoverStage === stage
    readonly property bool contentVisible: {
        for(let i=0;i<contentPanes.count;i++)if(contentPanes.itemAt(i)?.opacity>.01)return true;
        return false;
    }
    readonly property bool outgoingContentVisible: {
        if(panel==="idle")return false;
        for(let i=0;i<contentPanes.count;i++) {
            const pane=contentPanes.itemAt(i);
            if(pane&&!pane.selected&&pane.opacity>.01)return true;
        }
        return false;
    }
    scale: 1
    property real sharedHoverLift:0
    property real hoverLift: presentation?naturalHoverLift+(sharedHoverLift-naturalHoverLift)*dockProgress:hoverMotion.value
    readonly property real naturalHoverLift: hoverMotion.value
    FrameSpring {id:hoverMotion;owner:root;targetValue:root.restingHovered?Preferences.hoverLift:0;positionTolerance:.01}
    function diagnostics(): var {
        const entries=[];for(let i=0;i<contentPanes.count;i++){const p=contentPanes.itemAt(i);entries.push({name:p.modelData,selected:p.selected,opacity:p.opacity,enabled:p.enabled,loaded:!!p.item,status:p.status,width:p.width,height:p.height,input:p.item?.diagnostics?p.item.diagnostics():null});}
        return {name:stage,panel,x,y,width,height,targetWidth,targetHeight,radius:capsule.radius,visible,scale,hoverLift,restingHovered,restWidth:rest.width,restHeight:rest.height,restOpacity:rest.opacity,entries};
    }
    property real apertureWidth: widthMotion.value
    property real apertureHeight: heightMotion.value
    Component.onCompleted: apertureWidth = widthMotion.value
    onTargetWidthChanged: if (inlineContext || continuousWidth) apertureWidth = targetWidth
    function transferWidth(): void {
        if (inlineContext || continuousWidth) apertureWidth = targetWidth;
        else { widthMotion.reset(apertureWidth); widthMotion.start(); }
    }
    function finishWidth(): void { apertureWidth = targetWidth; }
    onInlineContextChanged: Qt.callLater(transferWidth)
    onContinuousWidthChanged: Qt.callLater(transferWidth)
    // Rebound must not shrink the resting pill or cross the screen's margin.
    width: presentation?.width ?? naturalWidth
    height: presentation?.height ?? naturalHeight
    FrameSpring {
        id:widthMotion;owner:root;targetValue:root.targetWidth
        enabled:widthMotion.available&&!root.inlineContext&&!root.continuousWidth
        minimumValue:Math.min(root.restingWidth,root.targetWidth);maximumValue:root.maximumWidth
        onValueChanged: if (!root.inlineContext && !root.continuousWidth) root.apertureWidth = value
        onAvailableChanged: if (!available && root.inlineContext) Qt.callLater(root.finishWidth)
    }
    // Held volume/brightness keys keep the original short feedback deadline.
    Behavior on apertureWidth {enabled:widthMotion.available&&root.inlineContext&&!root.continuousWidth;SmoothedAnimation {id:levelWidthMotion;velocity:-1;duration:root.expanded?Tokens.morphDuration:Tokens.collapseDuration;reversingMode:SmoothedAnimation.Immediate}}
    FrameSpring {id:heightMotion;owner:root;targetValue:root.targetHeight;minimumValue:Math.min(Preferences.barHeight,root.targetHeight);maximumValue:root.maximumHeight}
    Connections {
        target:Tokens
        function onReducedMotionChanged(){if(Tokens.reducedMotion)root.apertureWidth=root.targetWidth;}
    }
    RectangularShadow { anchors.fill: outline; radius: outline.radius; blur: root.expanded ? 24 : root.restingHovered ? 16 : 10; offset.y: root.expanded ? 7 : root.restingHovered ? 6 : 3; color: "#65000000"; visible: Preferences.shadows && !root.externalDecoration; cached: false
        Behavior on blur { NumberAnimation { duration: Tokens.animMedium } }
        Behavior on offset.y { NumberAnimation { duration: Tokens.animMedium } }
    }
    Rectangle {
        id: outline
        visible: !root.externalDecoration
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
        SurfaceLighting {anchors.fill:parent;radius:capsule.radius;active:root.expanded;opacity:1-root.dockProgress;visible:root.expanded&&opacity>0;interactive:true;focused:root.panel==="authentication"}
        Item { id: rest
            clip:root.externalDecoration
            width:root.presentation?.restWidth??Math.min(root.width,root.restingWidth)
            height: Preferences.barHeight
            x:root.presentation?root.presentation.restSceneX-root.x:root.stage==="media"?parent.width-width:root.stage==="controls"?0:(parent.width-width)/2
            opacity: Math.max(root.dockProgress, !root.expanded && root.height <= Preferences.barHeight * 1.1 ? 1 : 0)
            visible: opacity > 0; enabled: root.dockProgress>0 || (!root.expanded && root.nearRest)
            Behavior on opacity { NumberAnimation { duration: Tokens.animFast } }
        }
        Repeater {
            id: contentPanes
            model: ["clock", "context", "dropcue", "files", "notes", "toast", "calendar", "media", "privacy", "quicksettings", "themes", "wallpapers", "power", "launcher", "authentication", "unlockcheck"]
            delegate: Loader {
                id: content
                required property string modelData
                readonly property bool selected: root.expanded && root.panel === modelData && !(modelData === "context" && root.inlineContext)
                property real outgoingScale:1
                property real outgoingReveal:1
                property bool presented:false
                property string presentation:"held"
                property real resumeScale:1
                property real resumeReveal:1
                property real heldWidth: IslandState.sizes[modelData]?.[0] ?? 33
                property real heldHeight: IslandState.sizes[modelData]?.[1] ?? 33
                function resizeContent() { if (selected) { heldWidth = root.targetWidth; heldHeight = root.targetHeight; if(visibleScale>=.995)presented=true; } }
                onSelectedChanged: {
                    if(!selected) {
                        outgoingScale=visibleScale;outgoingReveal=revealAmount;
                        presentation="held";presented=false;
                    } else {
                        presented=false;
                        if(exposure>0&&item) {
                            resumeScale=outgoingScale;resumeReveal=outgoingReveal;
                            resumeMotion.reset(0);presentation="resume";resumeMotion.start();
                        } else presentation="entrance";
                        if(modelData==="launcher"&&item)item.beginSearch();
                    }
                    Qt.callLater(resizeContent);Qt.callLater(focusContent);
                }
                FrameSpring {
                    id:resumeMotion;owner:root;targetValue:1;minimumValue:0;maximumValue:1;positionTolerance:.0002
                    enabled:available&&content.presentation==="resume"
                    onValueChanged:if(content.selected&&content.presentation==="resume"&&value===1)content.presented=true
                }
                Connections { target: root; enabled: content.selected; function onTargetWidthChanged() { Qt.callLater(content.resizeContent); } function onTargetHeightChanged() { Qt.callLater(content.resizeContent); } }
                Component.onCompleted: Qt.callLater(resizeContent)
                readonly property real inset: ["context","dropcue"].includes(modelData) ? 0 : Preferences.innerPadding
                width: Math.max(0, heldWidth - inset * 2); height: Math.max(0, heldHeight - inset * 2)
                x: {const natural=root.stage === "media" ? parent.width-width-inset : root.stage === "controls" ? inset : (parent.width-width)/2;return natural+((parent.width-width)/2-natural)*root.dockProgress;}
                readonly property real bodyApertureWidth: root.bodyApertureWidth
                readonly property real bodyApertureHeight: root.bodyApertureHeight
                readonly property real maximumBodyHeight:Math.max(0,root.maximumHeight-root.headerInset)
                readonly property real viewportHeight:Math.min(height,Math.max(0,maximumBodyHeight-inset*2))
                y: inset+root.headerInset
                readonly property real resumeAmount:Math.max(0,Math.min(1,resumeMotion.value))
                readonly property real fittingHeight:["quicksettings","notes","toast","media"].includes(modelData)?viewportHeight:height
                readonly property real presentationScale:presentation==="held"?outgoingScale:presentation==="resume"?resumeScale+(1-resumeScale)*resumeAmount:Math.max(0,Math.min(1,(root.bodyApertureWidth-inset*2)/Math.max(1,width),(root.bodyApertureHeight-inset*2)/Math.max(1,fittingHeight)))
                readonly property real visibleScale:presentation==="entrance"&&presented?1:presentationScale
                onPresentationScaleChanged:if(selected&&presentation==="entrance"&&presentationScale>=.995)presented=true
                readonly property real revealAmount: {
                    if(presentation==="held")return outgoingReveal;
                    if(presentation==="resume")return resumeReveal+(1-resumeReveal)*resumeAmount;
                    if(presented)return 1;
                    const t=Math.max(0,Math.min(1,(presentationScale-.55)/.43));
                    return t*t*(3-2*t);
                }
                transform:Scale {
                    origin.x:root.stage==="media"?content.width:root.stage==="controls"?0:content.width/2
                    xScale:content.visibleScale
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
                opacity:exposure*revealAmount*(modelData==="context"&&Context.kind==="workspace"?1-root.dockProgress:1)
                z: selected ? 1 : 0
                function focusContent(): void { if (enabled && item && IslandState.menuOpen) item.forceActiveFocus(); }
                onEnabledChanged: Qt.callLater(focusContent)
                onLoaded: Qt.callLater(focusContent)
            }
        }
    }
    // Keep pointer geometry still while the visible surface settles under it.
    HoverHandler { id: hover; enabled:root.dockProgress===0; margin: 6; blocking: false; onHoveredChanged: IslandState.hover(root.stage, hovered) }
    MouseArea {
        parent: root
        Component.onCompleted: parent = root
        x: -6; y: 0; width: root.width + 12; height: root.height + 7
        enabled: (!root.restingContentInteractive || root.expanded) && root.dockProgress===0 && root.width > 0 && root.height > 0 && ((!root.expanded && root.nearRest) || root.panel === "context")
        acceptedButtons: Qt.LeftButton
        cursorShape: Qt.PointingHandCursor
        onClicked: mouse => root.activated(mouse.x - 6)
    }
    TapHandler { acceptedButtons: Qt.RightButton; onTapped: IslandState.menuOpen ? IslandState.dismissCurrent() : IslandState.openMenu("quicksettings") }
}
