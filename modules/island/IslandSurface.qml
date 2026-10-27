import QtQuick
import Quickshell.Hyprland
import qs.services
import qs.theme
import qs.components
Item {
    id: root
    property real availableWidth: 1000
    property real availableHeight: 1080
    property var monitor: null
    readonly property real dockProgress: Math.max(0,Math.min(1,dockMotion.value))
    readonly property real dockVelocity: dockMotion.velocity
    FrameSpring {id:dockMotion;owner:root;targetValue:IslandState.restingMode===IslandState.Dock||(root.compactDisclosure&&root.dockBody)?1:0;minimumValue:0;maximumValue:1;positionTolerance:.0002}
    readonly property real naturalCenterX: (width-center.naturalWidth+center.privacyExtension)/2
    readonly property real naturalLeftX: naturalCenterX-(left.visible?gap:0)-left.naturalWidth
    readonly property real naturalRightX: naturalCenterX+center.naturalWidth+(right.visible?gap:0)
    readonly property real maximumDockWidth: Math.max(0,width-32/Preferences.uiScale)
    readonly property real dockWidth: Math.max(0,Math.min(maximumDockWidth,dockWidthMotion.value))
    readonly property real dockHeight: Math.max(0,Math.min(maximumHeight,dockHeightMotion.value))
    readonly property real dockX: Math.max(16/Preferences.uiScale,Math.min(width-16/Preferences.uiScale-dockWidth,dockRestLeft-(dockWidth-dockRestWidth)/2))
    readonly property var dockPanels:[left,center,right].filter(s=>s.expanded&&!(s===center&&s.panel==="context"&&["workspace","welcome"].includes(Context.kind)))
    readonly property bool dockBody:dockPanels.length>0||center.inlineContext
    readonly property real dockEdgePadding:compactDisclosure?6:12
    readonly property real dockCenterGap:compactDisclosure?6:12
    readonly property real dockMediaGap:8
    readonly property real preferredDockPrivacyNeed: Audio.indicatorKind?clockViewport.dockPrivacyWidth:0
    readonly property real dockPrivacyNeed: Audio.indicatorKind?(compactDisclosure?Math.max(clockViewport.dockPrivacyMinimumWidth,Math.min(preferredDockPrivacyNeed,halfCapacity-clockViewport.clockTextWidth/2-dockCenterGap-dockEdgePadding-overflowWidth)):preferredDockPrivacyNeed):0
    readonly property real dockClockNeed: clockViewport.clockTextWidth+dockPrivacyNeed
    readonly property real dockClockStart: width/2-clockViewport.clockTextWidth/2
    readonly property bool dockMediaWanted: left.dockMediaAvailable||left.mode==="agent"
    readonly property real fullMediaNeed: left.mode==="agent"?Math.min(195,agentMeasure.advanceWidth+43):Preferences.barHeight
    readonly property real fullLeftNeed: workspaces.preferredWidth+(dockMediaWanted?fullMediaNeed+(workspaces.preferredWidth>0?dockMediaGap:0):0)
    readonly property real fullRightNeed: (Activities.active?Activities.width:0)+(right.visible?status.dockImplicitWidth+(Activities.active?dockMediaGap:0):0)
    readonly property real halfCapacity: Math.max(0,width/2-16/Preferences.uiScale)
    readonly property bool compactDisclosure: clockViewport.clockTextWidth/2+24+fullLeftNeed>halfCapacity||clockViewport.clockTextWidth/2+preferredDockPrivacyNeed+24+fullRightNeed>halfCapacity||clockViewport.clockTextWidth+preferredDockPrivacyNeed+48+fullLeftNeed+fullRightNeed>Math.min(680,maximumDockWidth)
    readonly property real dockMediaNeed: compactDisclosure?28:fullMediaNeed
    readonly property real compactActivityCapacity: Math.max(0,rightCapacity-overflowWidth)
    readonly property real dockActivityNeed: Activities.active?(compactDisclosure?(compactActivityCapacity>=activity.condensedMinimumWidth?Math.min(Math.max(64,activity.condensedMinimumWidth),compactActivityCapacity):compactActivityCapacity>=20?20:0):Activities.width):0
    readonly property real overflowWidth: compactDisclosure?20:0
    readonly property real dockRightNeed: dockActivityNeed+(compactDisclosure?overflowWidth:right.visible?(dockActivityNeed>0?dockMediaGap:0)+status.dockImplicitWidth:0)
    readonly property real leftCapacity: Math.max(0,halfCapacity-clockViewport.clockTextWidth/2-dockCenterGap-dockEdgePadding)
    readonly property real rightCapacity: Math.max(0,halfCapacity-clockViewport.clockTextWidth/2-dockPrivacyNeed-dockCenterGap-dockEdgePadding)
    readonly property bool dockMediaFits: dockMediaWanted&&dockMediaNeed<=leftCapacity
    readonly property real dockMediaWidth: dockMediaFits?dockMediaNeed:0
    readonly property real dockWorkspaceWidth: Math.min(workspaces.preferredWidth,Math.floor(Math.max(0,leftCapacity-dockMediaWidth-(dockMediaWidth>0&&workspaces.preferredWidth>0?dockMediaGap:0))/workspaces.targetPitch)*workspaces.targetPitch)
    readonly property real dockLeftNeed: dockWorkspaceWidth+dockMediaWidth+(dockWorkspaceWidth>0&&dockMediaWidth>0?dockMediaGap:0)
    readonly property real dockMinimumWidth: dockClockNeed+2*(dockEdgePadding+dockCenterGap)+dockLeftNeed+dockRightNeed
    readonly property bool dockHeaderSupported: dockMinimumWidth<=Math.min(680,maximumDockWidth)&&dockRightNeed<=rightCapacity
    readonly property real dockRestWidth: Math.min(maximumDockWidth,Math.min(680,dockMinimumWidth))
    readonly property real dockRestLeft: dockClockStart-dockCenterGap-dockEdgePadding-dockLeftNeed
    readonly property real dockClockWidth: dockClockNeed
    readonly property real dockSideWidth: Math.max(dockLeftNeed,dockRightNeed)
    readonly property real dockStatusWidth: dockRightNeed
    readonly property real dockActivityWidth: dockActivityNeed
    readonly property real dockWorkspaceX: dockClockStart-dockCenterGap-dockLeftNeed-dockX
    readonly property real dockMediaX: dockClockStart-dockCenterGap-dockMediaWidth-dockX
    readonly property real dockStatusX: dockClockStart+dockClockNeed+dockCenterGap-dockX
    FrameSpring {id:dockWidthMotion;owner:root;targetValue:Math.min(root.maximumDockWidth,Math.max(root.dockRestWidth,...root.dockPanels.map(s=>s.targetWidth)));minimumValue:0;maximumValue:root.maximumDockWidth;positionTolerance:.02}
    FrameSpring {id:dockHeightMotion;owner:root;targetValue:Math.min(root.maximumHeight,Preferences.barHeight+Math.max(center.inlineContext?Preferences.barHeight:0,...root.dockPanels.filter(s=>!s.inlineContext).map(s=>s.targetHeight)));minimumValue:Math.min(Preferences.barHeight,root.maximumHeight);maximumValue:root.maximumHeight;positionTolerance:.02}
    readonly property real sharedLift: sharedHover.value
    FrameSpring {id:sharedHover;owner:root;targetValue:IslandState.pointerInside&&!root.dockBody?Preferences.hoverLift:0;positionTolerance:.01}
    function project(s,restX,restWidth):var {
        const p=dockProgress;
        const naturalX=s===left?naturalLeftX:s===right?naturalRightX:naturalCenterX;
        const naturalWidth=Math.min(s.naturalWidth,s.restingWidth);
        const origin=naturalX+(s===left?s.naturalWidth-naturalWidth:s===center?(s.naturalWidth-naturalWidth)/2:0);
        const body=s===left?Math.max(0,Math.min(1,(s.naturalHeight-Preferences.barHeight)/Preferences.barHeight)):0;
        const clearance=Preferences.barHeight*p*(1-p)*body*body*(3-2*body);
        return {progress:p,width:s.naturalWidth+(dockWidth-s.naturalWidth)*p,height:Math.min(root.maximumHeight,s.naturalHeight+(dockHeight-s.naturalHeight)*p+clearance),header:Preferences.barHeight*p+clearance,restSceneX:origin+(dockX+restX-origin)*p,restX,restWidth:naturalWidth+(restWidth-naturalWidth)*p};
    }
    function projectedX(natural):real {return natural+(dockX-natural)*dockProgress;}
    readonly property Item clockHitRegion: Item {
        parent:root
        x:root.width/2-clockViewport.clockTextWidth/2-6
        y:center.hoverLift
        width:Math.max(0,Math.min(clockViewport.clockTextWidth+12,Audio.indicatorKind?clockViewport.clockTextWidth+clockViewport.privacyGap-2:Infinity))
        height:Preferences.barHeight
    }
    readonly property Item clockOrigin: Item {parent:root;x:root.clockHitRegion.x;y:root.clockHitRegion.y;width:root.clockHitRegion.width;height:root.clockHitRegion.height}
    readonly property bool clockAvailable: dockProgress>0 || center.nearRest
    DockContour {
        z:-1;mergeProgress:root.dockProgress
        frames:[root.mediaStage,root.clockStage,root.controlStage].map(s=>({x:s.x,y:s.y+s.hoverLift,width:s.width,height:s.height,radius:s.capsule.radius,alpha:s.visible?s.opacity:0}))
    }
    readonly property real maximumHeight: Math.max(0,(availableHeight-16)/Preferences.uiScale)
    readonly property string panel: IslandState.state
    readonly property alias capsule: center.capsule
    readonly property alias mediaStage: left
    readonly property alias clockStage: center
    readonly property alias controlStage: right
    readonly property alias trayIcons: tray
    readonly property alias trayMenu: trayMenu
    readonly property Item popupInputRegion: center.popupInputRegion
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
    readonly property real settledClockExtension: center.privacySpace ? clockViewport.privacyTail : 0
    readonly property real settledClockLeft: (width-center.targetWidth+settledClockExtension)/2
    readonly property real settledClockRight: settledClockLeft+center.targetWidth
    readonly property real leftBudget: Math.max(0,settledClockLeft-gap-16/Preferences.uiScale)
    readonly property real rightBudget: Math.max(0,width-16/Preferences.uiScale-settledClockRight-gap)
    readonly property real leftSafetyWidth: Math.max(0,naturalCenterX-gap-16/Preferences.uiScale)
    readonly property real rightSafetyWidth: Math.max(0,width-16/Preferences.uiScale-naturalCenterX-center.naturalWidth-gap)
    width: availableWidth / Preferences.uiScale
    height: Math.max(left.height, center.height, right.height,trayMenu.visible?trayMenu.y+trayMenu.height:Preferences.barHeight+8)
    function diagnostics(): var {
        const activityOrigin=activity.mapToItem(root,0,0);
        return {
            focus:{phase:FocusTimer.phase,remaining:FocusTimer.remaining,timeText:FocusTimer.timeText,deadline:FocusTimer.deadline},
            compactActivity:{present:Activities.active,visible:activity.visible&&activity.parent.visible,enabled:activity.enabled&&activity.parent.enabled,x:activityOrigin.x,y:activityOrigin.y,width:activity.width,height:activity.height},
            dropGuard:{visible:root.visible,enabled:root.enabled,secure:Session.secure,locked:Session.isLocked(),busy:IslandDrop.busy},
            dropEnabled:fileDrop.enabled,
            dropOffer:fileDrop.offer,
            dragging:IslandDrop.dragging,
            dropFiles:IslandDrop.files.length,
            dropError:IslandDrop.error,
            dock:{mode:IslandState.restingMode,progress:dockProgress,velocity:dockVelocity,x:dockX,width:dockWidth,height:dockHeight,headerSupported:dockHeaderSupported,minimumWidth:dockMinimumWidth,activityWidth:dockActivityWidth},
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
    function bounded(value: real): real { return Math.max(0,Math.min(value, root.compactDisclosure?root.maximumDockWidth:(availableWidth - 32) / Preferences.uiScale - 2 * (Preferences.barHeight + gap))); }
    Binding {target:LiveMedia;property:"visibleOnScreen";value:root.visible&&left.visible&&left.opacity>0&&left.mode==="media"&&(!left.expanded||root.dockProgress>0)}
    DropArea {
        id:fileDrop;z:100
        property var offer:({})
        property bool holding:false
        property bool completing:false
        property rect heldBox:Qt.rect(0,0,0,0)
        readonly property rect liveBox:Qt.rect(root.clockHitRegion.x-6,root.clockHitRegion.y,root.clockHitRegion.width+12,root.clockHitRegion.height+7)
        readonly property rect box:holding||completing?heldBox:liveBox
        x:box.x;y:box.y;width:box.width;height:box.height
        enabled:root.visible&&!Session.secure&&!Session.locked&&(completing||!IslandDrop.busy)
        // Validate actual URI offers before accepting a Copy drop.
        onEntered:drag=>{offer={hasUrls:drag.hasUrls,actions:drag.supportedActions,formats:drag.formats};drag.accepted=drag.hasUrls&&!!(drag.supportedActions&Qt.CopyAction);if(drag.accepted){if(!holding&&!completing)heldBox=liveBox;holding=true;IslandDrop.beginDrag(fileDrop);drag.accept(Qt.CopyAction);}else IslandDrop.endDrag(fileDrop);}
        onEnabledChanged:if(!enabled){holding=false;completing=false;IslandDrop.endDrag(fileDrop);}
        onExited:{holding=false;IslandDrop.endDrag(fileDrop);}
        onDropped:drop=>{completing=true;if(IslandDrop.accept(drop.urls))drop.accept(Qt.CopyAction);else drop.accepted=false;holding=false;IslandDrop.endDrag(fileDrop);Qt.callLater(()=>completing=false);}
    }
    Stage {
        id: left
        externalDecoration:true
        sharedHoverLift:root.sharedLift
        maximumWidth: root.compactDisclosure&&expanded?root.maximumDockWidth:root.leftSafetyWidth
        maximumHeight: root.maximumHeight
        x: root.projectedX(root.naturalLeftX)
        presentation:root.project(left,root.dockMediaX,root.dockMediaWidth)
        stage: "media"
        readonly property bool mediaAvailable: Preferences.showAlbum && (!Preferences.mediaAutoHide || Media.hasSession || sessionGrace.running)
        readonly property bool dockMediaAvailable: Preferences.showAlbum && (Media.hasSession || sessionGrace.running)
        readonly property bool agentAvailable: AgentWork.needsAttention || (AgentWork.pulse && AgentWork.kind !== "working")
        readonly property string agentName: AgentWork.needsAttention ? (AgentWork.tasks.find(t=>t.waiting)?.provider || "Agent") : (AgentWork.providerLabel || "Agent")
        readonly property string agentText: agentName
        readonly property string mode: root.panel === "media" ? "media" : mediaAvailable ? "media" : agentAvailable ? "agent" : "none"
        readonly property bool wanted: IslandState.owner === "media" || mode !== "none"
        // Brief metadata gaps between tracks/players should not blink the pill.
        property bool hadSession: Media.hasSession
        Timer { id: sessionGrace; interval: 800 }
        Connections {
            target: Media
            function onHasSessionChanged() {
                if (Media.hasSession) {left.hadSession=true;sessionGrace.stop();}
                else if(left.hadSession)sessionGrace.restart();
            }
        }
        opacity: expanded||contentVisible ? 1 : wanted ? (mode==="media"&&((!dockMediaAvailable&&!agentAvailable)||!root.dockMediaFits)?1-root.dockProgress:1) : 0
        visible: wanted || opacity > 0
        enabled: wanted
        Behavior on opacity { NumberAnimation { duration: Tokens.reducedMotion ? 0 : 180; easing.type: Easing.InOutCubic } }
        panel: IslandState.owner === "media" ? root.panel : "idle"
        readonly property real textBudget: Math.max(0, Math.min(440, root.naturalCenterX - root.gap - 16))
        readonly property bool titleRevealed:!LiveMedia.compactTitle||(IslandState.pointerInside&&IslandState.hoverStage==="media")
        TextMetrics {id: lyricMeasure; text: LiveMedia.lyric || Media.title; font.family: Tokens.font; font.pixelSize: 13; font.weight: Font.Medium}
        TextMetrics {id: agentMeasure; text:left.agentText; font.family:Tokens.font; font.pixelSize:12; font.weight:Font.DemiBold}
        readonly property real mediaRestingWidth: LiveMedia.expanded ? Math.min(textBudget, Preferences.barHeight + 24 + (Preferences.mediaVisualizer ? 38 : 0) + (Preferences.mediaLyrics && titleRevealed ? Math.max(140, lyricMeasure.advanceWidth + 8) : 0)) : Preferences.barHeight
        restingWidth: mode === "media" ? mediaRestingWidth : mode === "agent" ? Math.min(195,agentMeasure.advanceWidth+43) : Preferences.barHeight
        // Preserve the circle's geometry while fading; collapsing its width
        // would squeeze the artwork during the next appearance.
        targetWidth: Math.min(root.compactDisclosure&&expanded?root.maximumDockWidth:root.leftBudget,expanded ? IslandState.sizes[panel][0] : restingWidth)
        targetHeight: expanded ? Math.min(root.maximumHeight,IslandState.sizes[panel][1]) : Preferences.barHeight
        Art {anchors.right:parent.right;anchors.rightMargin:(Math.min(Preferences.barHeight,parent.width)-23)/2;anchors.verticalCenter:parent.verticalCenter;width:23;height:23;source:Media.artUrl;radius:width/2;compact:true;opacity:left.dockMediaAvailable&&root.dockMediaFits?1:1-root.dockProgress;visible:left.mode==="media"}
        Item {
            x: 6; anchors.verticalCenter: parent.verticalCenter; width: 23; height: 23
            opacity:left.mode==="agent"?1:root.dockProgress
            visible: left.mode === "agent" || (root.dockProgress>0&&!left.dockMediaAvailable&&left.agentAvailable)
            AgentGlyph { anchors.centerIn: parent; kind: AgentWork.needsAttention ? "waiting" : AgentWork.kind }
        }
        RollingText { x:32; width:parent.width-40; height:parent.height; visible:left.mode==="agent"; text:left.agentText; font.pixelSize:12; font.weight:Font.DemiBold; horizontalAlignment:Text.AlignLeft;verticalAlignment:Text.AlignVCenter }
        Item {x:12;width:parent.width-Preferences.barHeight-20;height:parent.height;clip:true;opacity:1-root.dockProgress;visible:left.mode==="media"&&LiveMedia.expanded
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
            if (mode === "agent" || (root.dockProgress>0&&!dockMediaAvailable&&agentAvailable)) AgentWork.focusT3();
            else IslandState.toggle("media");
        }
    }
    Stage {
        id: center
        externalDecoration:true
        sharedHoverLift:root.sharedLift
        maximumWidth: root.bounded(Infinity)
        maximumHeight: root.maximumHeight
        readonly property bool privacySpace: Preferences.privacyRadar && !!Audio.indicatorKind && panel === "idle"
        readonly property real clockRestingWidth: Math.max(Preferences.collapsedWidth+(Preferences.showSeconds?20:0),clockViewport.clockTextWidth+clockViewport.privacyPadding*2)
        readonly property real agentRestingWidth: Math.max(AgentWork.width,clockViewport.agentLabelWidth+clockViewport.privacyPadding*2)
        readonly property real baseRestingWidth: clockRestingWidth+(agentRestingWidth-clockRestingWidth)*root.agentReveal
        readonly property real restingLabelWidth: clockViewport.clockTextWidth+(clockViewport.agentLabelWidth-clockViewport.clockTextWidth)*root.agentReveal
        continuousWidth:panel==="idle"&&root.agentApertureActive
        onPanelChanged:if(panel!=="idle")root.agentApertureActive=false
        // Follow the animated width so only the right edge grows for privacy.
        readonly property real privacyExtension: panel === "idle" ? Math.max(Math.min(0,clockViewport.privacyTail),Math.min(Math.max(0,clockViewport.privacyTail),naturalWidth-baseRestingWidth)) : 0
        x: root.projectedX(root.naturalCenterX)
        presentation:root.project(center,root.width/2-root.dockClockWidth/2-root.dockX,root.dockClockWidth)
        stage: "clock"
        restingWidth:baseRestingWidth+(privacySpace?clockViewport.privacyTail:0)
        panel: IslandState.owner === "clock" ? root.panel : "idle"
        inlineContext:clockViewport.levelRequested||clockViewport.levelAmount>0
        targetWidth: root.bounded(clockViewport.welcomeRequested||clockViewport.welcomeAmount>0?clockViewport.welcomeWidth:panel==="idle"?restingWidth:root.agentWidthHeld?AgentWork.width:(IslandState.sizes[panel]?.[0] ?? Preferences.collapsedWidth))
        targetHeight: Math.min(root.maximumHeight,IslandState.sizes[panel]?.[1] ?? Preferences.barHeight)
        // One persistent clock survives both directions of the weekly expansion.
        onActivated: localX => {if (clockViewport.privacyContains(localX)) IslandState.toggle("privacy"); else if (root.agentPulse) AgentWork.focusT3(); else if (Context.active && Context.kind === "luma") CanvasState.show(); else IslandState.toggle("clock");}
    }
    ClockViewport {
        id: clockViewport
        stage: center
        dockProgress:root.dockProgress
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
        externalDecoration:true
        sharedHoverLift:root.sharedLift
        maximumWidth: root.compactDisclosure&&expanded?root.maximumDockWidth:root.rightSafetyWidth
        maximumHeight: root.maximumHeight
        x: root.projectedX(root.naturalRightX)
        presentation:root.project(right,root.dockStatusX,root.dockStatusWidth)
        stage: "controls"; visible: Preferences.showStatus || IslandState.owner === "controls" || Activities.active
        panel: IslandState.owner === "controls" && !["recording","focusstatus"].includes(root.panel) ? (root.panel==="context"?"context":"quicksettings") : "idle"
        restingWidth: Activities.active ? Activities.width : Preferences.barHeight
        restingContentInteractive: Activities.active
        targetWidth: !visible ? 0 : Math.min(root.compactDisclosure&&expanded?root.maximumDockWidth:root.rightBudget,expanded ? (IslandState.sizes[panel==="quicksettings"?root.panel:panel]?.[0]??Preferences.controlsWidth) : restingWidth)
        targetHeight: expanded ? Math.min(root.maximumHeight,IslandState.sizes[panel==="quicksettings"?root.panel:panel][1]) : Preferences.barHeight
        ActivityStatus {
            id:activity;objectName:"compactActivity"
            width:Math.min(parent.width,Activities.width+(root.dockActivityWidth-Activities.width)*root.dockProgress)
            height:Preferences.barHeight
            visible:Activities.active&&width>0;enabled:visible
            dockProgress:root.dockProgress
            condensed:root.compactDisclosure&&root.dockProgress>0
        }
        StatusOrb {
            id:status;objectName:"systemStatus"
            x:Activities.active?activity.width+root.dockMediaGap*root.dockProgress:(1-root.dockProgress)*Math.max(0,(parent.width-width)/2)
            y:(parent.height-height)/2;dockProgress:root.dockProgress
            opacity:root.compactDisclosure?1-root.dockProgress:Activities.active?root.dockProgress:1;visible:opacity>0
        }
        onActivated: {
            if (panel === "context" && Context.kind === "audiooutput") {
                Context.clear();
                IslandState.openMenu("sound");
            } else IslandState.toggle("quicksettings");
        }
    }
    WorkspaceMarks {
        id:workspaces;monitor:root.monitor
        parent:center.capsule.contentItem
        x:(left.visible&&left.opacity>.01?left.presentation.restSceneX-(left.presentation.restWidth>0?root.dockMediaGap:0)-root.dockWorkspaceWidth:root.dockX+root.dockWorkspaceX)-center.x;y:0;width:root.dockWorkspaceWidth;height:Preferences.barHeight
        opacity:root.dockProgress;visible:opacity>0;enabled:opacity>.7
    }
    Item {
        id:overflow;objectName:"dockOverflow"
        parent:center.capsule.contentItem
        x:right.presentation.restSceneX+activity.width-center.x
        width:root.overflowWidth;height:Preferences.barHeight
        opacity:root.dockProgress;visible:root.compactDisclosure&&opacity>0;enabled:visible
        activeFocusOnTab:true
        Icon {anchors.centerIn:parent;icon:"more_horiz";size:18}
        Rectangle {anchors.fill:parent;anchors.margins:2;radius:height/2;color:"transparent";border.width:parent.activeFocus?1:0;border.color:Theme.accent}
        Accessible.role:Accessible.Button
        Accessible.name:"More controls and activities. "+(Activities.focus?"Focus timer, "+FocusTimer.timeText+". ":"")+(Activities.recording?"Recording, "+Recorder.label+". ":"")+status.statusText
        Accessible.onPressAction:IslandState.toggle("quicksettings")
        Keys.onReturnPressed:IslandState.toggle("quicksettings")
        Keys.onSpacePressed:IslandState.toggle("quicksettings")
        MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:IslandState.toggle("quicksettings")}
    }
    Repeater {
        model:[{role:"media",stage:root.mediaStage},{role:"clock",stage:root.clockStage},{role:"controls",stage:root.controlStage}]
        Item {
            required property var modelData
            objectName:modelData.role+"DockHit"
            readonly property bool clockRole:modelData.role==="clock"
            readonly property bool statusRole:modelData.role==="controls"
            x:clockRole?root.clockHitRegion.x:modelData.stage.presentation.restSceneX+(statusRole&&Activities.active?activity.width+root.dockMediaGap*root.dockProgress:0)
            y:modelData.stage.hoverLift
            width:clockRole?root.clockHitRegion.width:statusRole?Math.max(0,Math.min(status.width,modelData.stage.presentation.restWidth-(Activities.active?activity.width+root.dockMediaGap*root.dockProgress:0))):modelData.stage.presentation.restWidth
            height:Preferences.barHeight
            visible:root.dockProgress>0&&modelData.stage.visible&&modelData.stage.opacity>.05&&(!statusRole||!root.compactDisclosure)
            enabled:visible
            activeFocusOnTab:true
            Accessible.role:Accessible.Button
            Accessible.name:clockRole?"Clock":statusRole?"Control center":"Media"
            Accessible.onPressAction:modelData.stage.activated(width/2)
            Keys.onReturnPressed:modelData.stage.activated(width/2)
            Keys.onSpacePressed:modelData.stage.activated(width/2)
            HoverHandler {blocking:false;onHoveredChanged:IslandState.hover(modelData.role,hovered)}
            Rectangle {anchors.fill:parent;radius:height/2;color:"transparent";border.width:parent.activeFocus?1:0;border.color:Theme.accent}
            MouseArea {anchors.fill:parent;acceptedButtons:Qt.LeftButton;cursorShape:Qt.PointingHandCursor;onClicked:modelData.stage.activated(parent.width/2)}
        }
    }
    Item {id:tray;visible:false;width:0;height:0;x:right.x+right.width;y:0}
    TrayMenu {id:trayMenu;x:Math.min(root.width-width-8,tray.x);y:Preferences.barHeight+8}
    HintBubble {maximumY:root.height+7}
}
