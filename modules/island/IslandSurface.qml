import QtQuick
import qs.services
import qs.theme
import qs.components
Item {
    id: root
    property real availableWidth: 1000
    readonly property string panel: IslandState.state
    readonly property alias capsule: center.capsule
    readonly property alias mediaStage: left
    readonly property alias clockStage: center
    readonly property alias controlStage: right
    readonly property alias trayIcons: tray
    readonly property alias trayMenu: trayMenu
    readonly property real levelProgress: clockViewport.levelAmount
    readonly property var levelStatus: ({kind:clockViewport.levelEvent.kind,value:clockViewport.levelEvent.value,progress:clockViewport.levelAmount})
    readonly property bool agentPulse: AgentWork.pulse && left.mode !== "agent" && center.panel === "idle" && clockViewport.welcomeAmount === 0
    // One progress value drives label travel, aperture width and privacy spacing.
    property real agentReveal: agentPulse ? 1 : 0
    property bool agentApertureActive: false
    onAgentPulseChanged: if(agentPulse)agentApertureActive=center.panel==="idle"&&!center.resizing
    onAgentRevealChanged: if(agentReveal===0&&!agentPulse)agentApertureActive=false
    readonly property bool agentWidthHeld: center.panel === "idle" && (agentPulse || agentReveal > 0)
    Behavior on agentReveal { NumberAnimation { duration:Tokens.reducedMotion?0:Tokens.morphDuration; easing.type:Easing.InOutCubic } }
    readonly property real targetWidth: (left.visible ? left.targetWidth : 0) + center.targetWidth + right.targetWidth + gap * ((left.visible ? 1 : 0) + (right.visible ? 1 : 0))
    readonly property real targetHeight: Math.max(left.targetHeight, center.targetHeight, right.targetHeight)
    readonly property real gap: Preferences.clusterGap
    width: availableWidth / Preferences.uiScale
    height: Math.max(left.height, center.height, right.height,trayMenu.visible?trayMenu.y+trayMenu.height:Preferences.barHeight+8)
    function diagnostics(): var {
        return {
            dropGuard:{visible:root.visible,enabled:root.enabled,secure:Session.secure,locked:Session.isLocked(),busy:IslandDrop.busy},
            dropEnabled:fileDrop.enabled,
            dropOffer:fileDrop.offer,
            dragging:IslandDrop.dragging,
            dropFiles:IslandDrop.files.length,
            dropError:IslandDrop.error,
            panel,
            width,
            height,
            targetWidth,
            targetHeight,
            mediaPlaying:Media.playing,
            activityMode:left.mode,
            captureCount:Audio.captureStreams.length,
            privacyKind:Audio.indicatorKind,
            privacySummary:Audio.captureSummary,
            visualizerRunning:LiveMedia.listening&&Preferences.mediaVisualizer,
            agentActivity:({available:AgentWork.available,active:AgentWork.active,pulse:root.agentPulse,label:root.agentPulse?AgentWork.shownLabel:"",lastProvider:AgentWork.providerLabel,startPending:AgentWork.startPending,canPresent:AgentWork.canPresent,interval:Preferences.agentActivityInterval,tasks:AgentWork.tasks.length}),
            pointerInside:IslandState.pointerInside,
            clockOpacity:clockViewport.clockOpacity,
            level:root.levelStatus,
            welcomeProgress:clockViewport.welcomeAmount,
            hoverStage:IslandState.hoverStage,
            menu:IslandState.menu,
            fontFamily:Tokens.font,
            stages:[left.diagnostics(),center.diagnostics(),right.diagnostics()],
            trayItems:Tray.items.map(i=>({id:i.id,title:i.title,hasMenu:i.hasMenu})),
            trayOpen:Tray.open,
            trayHovered:Tray.pointerInside,
            trayRect:({x:tray.x,y:tray.y,width:tray.width,height:tray.height}),
            entries:[],
            uiScale: Preferences.uiScale,
            topMargin: Preferences.topMargin
        };
    }
    function bounded(value: real): real { return Math.min(value, (availableWidth - 32) / Preferences.uiScale - 2 * (Preferences.barHeight + gap)); }
    Binding {target:LiveMedia;property:"visibleOnScreen";value:root.visible&&left.visible&&left.mode==="media"&&!left.expanded}
    DropArea {
        id:fileDrop;z:100
        property var offer:({})
        x:center.x-6;y:center.hoverLift;width:center.width+12;height:center.height+7
        enabled:root.visible&&!Session.secure&&!Session.locked&&!IslandDrop.busy
        // Validate actual URI offers before accepting a Copy drop.
        onEntered:drag=>{offer={hasUrls:drag.hasUrls,actions:drag.supportedActions,formats:drag.formats};drag.accepted=drag.hasUrls&&!!(drag.supportedActions&Qt.CopyAction);if(drag.accepted){IslandDrop.beginDrag(fileDrop);drag.accept(Qt.CopyAction);}else IslandDrop.endDrag(fileDrop);}
        onEnabledChanged:if(!enabled)IslandDrop.endDrag(fileDrop)
        onExited:IslandDrop.endDrag(fileDrop)
        onDropped:drop=>{if(IslandDrop.accept(drop.urls))drop.accept(Qt.CopyAction);else drop.accepted=false;IslandDrop.endDrag(fileDrop);}
    }
    Stage {
        id: left
        maximumWidth: root.bounded(Infinity)
        x: center.x - (visible ? root.gap : 0) - width
        stage: "media"
        readonly property bool mediaAvailable: Preferences.showAlbum && (!Preferences.mediaAutoHide || Media.hasSession || sessionGrace.running)
        readonly property bool agentAvailable: AgentWork.needsAttention || (AgentWork.pulse && AgentWork.kind !== "working")
        readonly property string agentName: AgentWork.needsAttention ? (AgentWork.tasks.find(t=>t.waiting)?.provider || "Agent") : (AgentWork.providerLabel || "Agent")
        readonly property string agentText: agentName
        readonly property string mode: root.panel === "media" ? "media" : mediaAvailable ? "media" : agentAvailable ? "agent" : "none"
        readonly property bool wanted: IslandState.owner === "media" || mode !== "none"
        // Brief metadata gaps between tracks/players should not blink the pill.
        Timer { id: sessionGrace; interval: 800 }
        Connections {
            target: Media
            function onHasSessionChanged() {
                if (Media.hasSession) sessionGrace.stop();
                else sessionGrace.restart();
            }
        }
        opacity: wanted ? 1 : 0
        visible: wanted || opacity > 0
        enabled: wanted
        Behavior on opacity { NumberAnimation { duration: Tokens.reducedMotion ? 0 : 180; easing.type: Easing.InOutCubic } }
        panel: IslandState.owner === "media" ? root.panel : "idle"
        readonly property real textBudget: Math.max(0, Math.min(440, center.x - root.gap - 16))
        readonly property bool titleRevealed:!LiveMedia.compactTitle||(IslandState.pointerInside&&IslandState.hoverStage==="media")
        TextMetrics {id: lyricMeasure; text: LiveMedia.lyric || Media.title; font.family: Tokens.font; font.pixelSize: 13; font.weight: Font.Medium}
        TextMetrics {id: agentMeasure; text:left.agentText; font.family:Tokens.font; font.pixelSize:12; font.weight:Font.DemiBold}
        readonly property real mediaRestingWidth: LiveMedia.expanded ? Math.min(textBudget, Preferences.barHeight + 24 + (Preferences.mediaVisualizer ? 38 : 0) + (Preferences.mediaLyrics && titleRevealed ? Math.max(140, lyricMeasure.advanceWidth + 8) : 0)) : Preferences.barHeight
        restingWidth: mode === "media" ? mediaRestingWidth : mode === "agent" ? Math.min(195,agentMeasure.advanceWidth+43) : Preferences.barHeight
        // Preserve the circle's geometry while fading; collapsing its width
        // would squeeze the artwork during the next appearance.
        targetWidth: expanded ? root.bounded(IslandState.sizes[panel][0]) : restingWidth
        targetHeight: expanded ? IslandState.sizes[panel][1] : Preferences.barHeight
        Art {anchors.right:parent.right;anchors.rightMargin:(Preferences.barHeight-23)/2;anchors.verticalCenter:parent.verticalCenter;width:23;height:23;source:Media.artUrl;radius:width/2;compact:true;visible:left.mode==="media"}
        Item {
            x: 6; anchors.verticalCenter: parent.verticalCenter; width: 23; height: 23
            visible: left.mode === "agent"
            AgentGlyph { anchors.centerIn: parent; kind: AgentWork.needsAttention ? "waiting" : AgentWork.kind }
        }
        RollingText { x:32; width:parent.width-40; height:parent.height; visible:left.mode==="agent"; text:left.agentText; font.pixelSize:12; font.weight:Font.DemiBold; horizontalAlignment:Text.AlignLeft;verticalAlignment:Text.AlignVCenter }
        Item {x:12;width:parent.width-Preferences.barHeight-20;height:parent.height;clip:true;visible:left.mode==="media"&&LiveMedia.expanded
            Row {id:levels;anchors.left:parent.left;anchors.verticalCenter:parent.verticalCenter;spacing:2;visible:Preferences.mediaVisualizer
                Repeater {model:6;Rectangle {required property int index;width:3;height:Math.max(3,LiveMedia.bars[index]*18);radius:1.5;anchors.verticalCenter:parent.verticalCenter;color:Theme.accent;Behavior on height {NumberAnimation {duration:65;easing.type:Easing.OutQuad}}}}
                height:20
            }
            RollingText {
                anchors.left: parent.left; anchors.leftMargin: levels.visible ? 38 : 0
                anchors.right: parent.right; height: parent.height
                visible: Preferences.mediaLyrics && opacity>0; opacity:left.titleRevealed?1:0; Behavior on opacity {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}} marquee: true
                readingTime: LiveMedia.lineRemaining
                text: LiveMedia.lyric || Media.title
                horizontalAlignment: Text.AlignLeft
                font.family: Tokens.font; font.pixelSize: 13; font.weight: Font.Medium
            }
        }
        onActivated: localX => {
            if (mode === "agent") AgentWork.focusT3();
            else IslandState.toggle("media");
        }
    }
    Stage {
        id: center
        maximumWidth: root.bounded(Infinity)
        readonly property bool privacySpace: Preferences.privacyRadar && !!Audio.indicatorKind && panel === "idle"
        readonly property real clockRestingWidth: Math.max(Preferences.collapsedWidth+(Preferences.showSeconds?20:0),clockViewport.clockTextWidth+clockViewport.privacyPadding*2)
        readonly property real agentRestingWidth: Math.max(AgentWork.width,clockViewport.agentLabelWidth+clockViewport.privacyPadding*2)
        readonly property real baseRestingWidth: clockRestingWidth+(agentRestingWidth-clockRestingWidth)*root.agentReveal
        readonly property real restingLabelWidth: clockViewport.clockTextWidth+(clockViewport.agentLabelWidth-clockViewport.clockTextWidth)*root.agentReveal
        continuousWidth:panel==="idle"&&root.agentApertureActive
        onPanelChanged:if(panel!=="idle")root.agentApertureActive=false
        // Follow the animated width so only the right edge grows for privacy.
        readonly property real privacyExtension: panel === "idle" ? Math.max(Math.min(0,clockViewport.privacyTail),Math.min(Math.max(0,clockViewport.privacyTail),width-baseRestingWidth)) : 0
        x: (root.width - width + privacyExtension) / 2
        stage: "clock"
        restingWidth:baseRestingWidth+(privacySpace?clockViewport.privacyTail:0)
        panel: IslandState.owner === "clock" ? root.panel : "idle"
        inlineContext:clockViewport.levelRequested||clockViewport.levelAmount>0
        targetWidth: root.bounded(clockViewport.welcomeRequested||clockViewport.welcomeAmount>0?clockViewport.welcomeWidth:panel==="idle"?restingWidth:root.agentWidthHeld?AgentWork.width:(IslandState.sizes[panel]?.[0] ?? Preferences.collapsedWidth))
        targetHeight: IslandState.sizes[panel]?.[1] ?? Preferences.barHeight
        // One persistent clock survives both directions of the weekly expansion.
        onActivated: localX => {if (privacySpace && localX >= clockPrivacy.x && localX <= clockPrivacy.x + clockPrivacy.width) IslandState.toggle("privacy"); else if (root.agentPulse) AgentWork.focusT3(); else if (Context.active && Context.kind === "luma") CanvasState.show(); else IslandState.toggle("clock");}
    }
    ClockViewport {
        id: clockViewport
        stage: center
        agentReveal: root.agentReveal
        agentPulse: root.agentPulse
    }
    Rectangle {
        x:center.privacySpace?center.x+10:center.x+center.width-12;y:center.hoverLift+Preferences.barHeight/2-2
        width:4;height:4;radius:2;color:Theme.yellow
        visible:AgentWork.needsAttention&&left.mode!=="agent"&&!root.agentWidthHeld&&center.panel==="idle"
    }
    Stage {
        id: right
        maximumWidth: root.bounded(Infinity)
        x: center.x + center.width + (visible ? root.gap : 0)
        stage: "controls"; visible: Preferences.showStatus || IslandState.owner === "controls" || Recorder.active || FocusTimer.active
        panel: IslandState.owner === "controls" ? (["recording","focusstatus"].includes(root.panel)?"activities":root.panel==="context"?"context":"quicksettings") : (Recorder.active&&!Recorder.selecting)||FocusTimer.active ? "activities" : "idle"
        targetWidth: !visible ? 0 : expanded ? root.bounded(IslandState.sizes[panel==="quicksettings"?root.panel:panel]?.[0]??Preferences.controlsWidth) : Preferences.barHeight
        targetHeight: expanded ? IslandState.sizes[panel==="quicksettings"?root.panel:panel][1] : Preferences.barHeight
        StatusOrb { anchors.centerIn:parent }
        onActivated: {
            if (panel === "context" && Context.kind === "audiooutput") {
                Context.clear();
                IslandState.openMenu("sound");
            } else IslandState.toggle("quicksettings");
        }
    }
    Item {id:tray;visible:false;width:0;height:0;x:right.x+right.width;y:0}
    TrayMenu {id:trayMenu;x:Math.min(root.width-width-8,tray.x);y:Preferences.barHeight+8}
    HintBubble {maximumY:root.height+7}
}
