import QtQuick
import qs.services
import qs.theme
import qs.components

Item {
    id: clockViewport
    required property Stage stage
    property real agentReveal: 0
    property bool agentPulse: false
    readonly property real clockTextWidth: privacyClockMeasure.advanceWidth
    readonly property real agentLabelWidth: agentLabel.implicitWidth
    readonly property real clockOpacity: clockLabel.opacity
    TextMetrics {id:privacyClockMeasure;font:clockLabel.font;text:Time.timeStr}
        x:clockViewport.stage.x;y:clockViewport.stage.hoverLift
        width:clockViewport.stage.width;height:Preferences.barHeight+clockLabel.weekOffset
        clip:true
        readonly property int privacyGap:Preferences.privacyIndicatorGap
        readonly property int privacyPadding:20
        readonly property real privacyTail:privacyGap+clockPrivacy.dotSize+Preferences.privacyIndicatorRightPadding-(clockViewport.stage.baseRestingWidth-clockViewport.stage.restingLabelWidth)/2
        readonly property bool welcomeRequested:clockViewport.stage.panel==="context"&&Context.kind==="welcome"
        readonly property bool levelRequested:clockViewport.stage.panel==="context"&&["volume","brightness"].includes(Context.kind)
        property var levelEvent:({kind:"volume",icon:"volume_up",value:0})
        property real levelAmount:levelRequested?1:0
        Behavior on levelAmount {NumberAnimation {duration:clockViewport.levelRequested?Tokens.morphDuration:Tokens.collapseDuration;easing.type:Easing.OutCubic}}
        Connections {target:Context;function onEventChanged(){if(clockViewport.levelRequested)clockViewport.levelEvent=Context.event;}}
        onLevelRequestedChanged:if(levelRequested)levelEvent=Context.event
        readonly property int welcomeWidth:Math.max(Preferences.collapsedWidth+(Preferences.showSeconds?20:0),Math.ceil(helloWord.inkBounds.width/helloWord.inkBounds.height*(Preferences.barHeight-14))+36)
        property real welcomeAmount:0
        function settleWelcome():void {
            welcomeMotion.stop();helloWrite.stop();
            if(!welcomeRequested&&clockViewport.stage.panel!=="idle"){welcomeAmount=0;return;}
            const target=welcomeRequested?1:0;
            welcomeMotion.to=target;
            welcomeMotion.duration=Tokens.reducedMotion?0:Math.round(360/Preferences.motionSpeed*Math.abs(target-welcomeAmount));
            welcomeMotion.start();
            if(welcomeRequested)helloWrite.restart();
        }
        function cancelWelcome():void {welcomeMotion.stop();helloWrite.stop();welcomeAmount=0;}
        onWelcomeRequestedChanged:Qt.callLater(settleWelcome)
        Connections {target:clockViewport.stage;function onPanelChanged(){if(!clockViewport.welcomeRequested&&clockViewport.stage.panel!=="idle")clockViewport.cancelWelcome();}}
        Connections {target:Context;function onKindChanged(){if(Context.kind!=="welcome")clockViewport.cancelWelcome();}}
        NumberAnimation {id:welcomeMotion;target:clockViewport;property:"welcomeAmount";easing.type:Easing.InOutCubic}
    RollingText {
        id: clockLabel
        readonly property bool compactStatus:clockViewport.stage.panel==="context"&&Context.kind==="workspace"
        property bool returningFromWeek: false
        property real weekOffset: clockViewport.stage.panel === "clock" ? 13 : 0
        Connections { target: clockViewport.stage; function onPanelChanged() {
            if (clockViewport.stage.panel === "clock") clockLabel.returningFromWeek = true;
            else if (clockViewport.stage.panel !== "idle") clockLabel.returningFromWeek = false;
        } }
        x:0
        y: weekOffset-Preferences.barHeight*(clockViewport.welcomeAmount+clockViewport.levelAmount) - (clockViewport.stage.panel === "idle" ? Preferences.barHeight * clockViewport.agentReveal : 0)
        width:parent.width-clockViewport.stage.privacyExtension; height: Preferences.barHeight
        scale: clockViewport.stage.panel === "idle" ? clockViewport.stage.scale : 1
        font.family:Tokens.clockFont; font.kerning:true; font.hintingPreference:Font.PreferVerticalHinting; font.preferTypoLineMetrics:true
        font.features: ({tnum:1})
        slideDigits: !compactStatus
        text: compactStatus?Context.label:Time.timeStr; font.pixelSize: clockViewport.stage.panel === "clock" ? 19 : Tokens.pillTextSize; font.weight: compactStatus ? Tokens.pillTextWeight : Font.DemiBold
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        opacity: clockViewport.levelRequested||clockViewport.levelAmount>0||clockViewport.welcomeRequested || compactStatus || clockViewport.stage.panel === "clock" || (clockViewport.stage.panel === "idle"&&(clockViewport.stage.height<=Preferences.barHeight*1.1||returningFromWeek)) ? 1 : 0; visible: opacity > 0
        Behavior on weekOffset { NumberAnimation { duration: clockViewport.stage.expanded ? Tokens.morphDuration : Tokens.collapseDuration; easing.type: Easing.OutCubic } }
        Behavior on font.pixelSize { NumberAnimation { duration: Tokens.morphDuration; easing.type: Easing.InOutCubic } }
        Behavior on opacity { NumberAnimation { duration: Tokens.animFast } }
    }
    PrivacyIndicator {
        id:clockPrivacy
        x:(parent.width-clockViewport.stage.privacyExtension+clockViewport.stage.restingLabelWidth)/2+clockViewport.privacyGap+clockPrivacy.dotSize/2-width/2
        y:0;width:22;height:Preferences.barHeight
        kind:clockViewport.stage.privacySpace ? Audio.indicatorKind : ""
        label:Audio.captureSummary
        onClicked:IslandState.toggle("privacy")
    }
    ContextPanel {
        width:parent.width;height:Preferences.barHeight
        y:Preferences.barHeight*(1-clockViewport.levelAmount)
        visible:clockViewport.levelAmount>0
        kind:clockViewport.levelEvent.kind;icon:clockViewport.levelEvent.icon;value:clockViewport.levelEvent.value
    }
    Item {
        id: helloOverlay
        anchors.fill: parent
        property real reveal: 0
        visible:clockViewport.welcomeAmount>0
        transform:Translate {y:Preferences.barHeight*(1-clockViewport.welcomeAmount)}
        SequentialAnimation {
            id: helloWrite
            PropertyAction { target:helloOverlay; property:"reveal"; value:0 }
            PauseAnimation { duration:Tokens.reducedMotion?0:Math.round(340/Preferences.motionSpeed) }
            NumberAnimation { target:helloOverlay; property:"reveal"; from:0; to:1; duration:Tokens.reducedMotion?0:1550; easing.type:Easing.InOutSine }
        }
        WelcomeWord {id:helloWord;anchors.centerIn:parent;width:Math.max(0,parent.width-36);height:Math.max(16,Preferences.barHeight-14);progress:helloOverlay.reveal}
    }
    TextMetrics {id:agentLabelMetrics;text:AgentWork.providerLabel;font.family:Tokens.font;font.pixelSize:13;font.weight:Font.DemiBold}
    Row {
        id:agentLabel
        anchors.horizontalCenter:parent.horizontalCenter
        anchors.horizontalCenterOffset:-clockViewport.stage.privacyExtension/2
        y:Preferences.barHeight*(1-clockViewport.agentReveal)
        height:Preferences.barHeight
        spacing:8
        visible:clockViewport.agentReveal>0 && clockViewport.stage.panel==="idle"
        Item {
            anchors.verticalCenter:parent.verticalCenter;width:14;height:14
            AgentGlyph {anchors.centerIn:parent;kind:AgentWork.kind;running:clockViewport.agentPulse}
        }
        RollingText {
            text:AgentWork.providerLabel
            width:Math.max(18,Math.min(192,agentLabelMetrics.advanceWidth))
            height:parent.height
            font.pixelSize:13;font.weight:Font.DemiBold
            horizontalAlignment:Text.AlignLeft
            verticalAlignment:Text.AlignVCenter
        }
    }
    }
