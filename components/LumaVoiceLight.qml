import QtQuick
import qs.theme
import qs.services

// One shader handles border light and voice waves without blur textures.
Item {
    id: root
    property string activity: "listening"
    property real level: 0
    property bool active: true
    property bool edge: false
    property real radius: 24
    property bool revealOnActivate: false
    property bool revealing: false
    property bool initialized: false
    readonly property bool allowed: Preferences.lumaEffects && !Tokens.reducedMotion
    readonly property bool working: !["error","idle"].includes(activity)
    readonly property bool rendering: active && visible && opacity > 0 && Preferences.lumaEffects && (!edge || working || revealing || activity === "error")
    readonly property real measuredEnergy: activity === "listening" ? Math.pow(Math.max(0, Math.min(1, level)), .75) : 0
    property real energy: measuredEnergy
    property real mode: activity === "finishing" ? 1 : activity === "acting" ? 3 : activity === "thinking" ? 2 : 0
    readonly property bool moving: rendering && allowed && (working || revealing)
    implicitWidth: 260
    implicitHeight: 64
    Behavior on energy { SmoothedAnimation { velocity: -1; duration: root.measuredEnergy > root.energy ? 55 : 220; reversingMode: SmoothedAnimation.Immediate } }
    Behavior on mode { NumberAnimation { duration: Tokens.animSlow; easing.type: Easing.InOutCubic } }
    function updateEntrance():void {
        if(!initialized)return;
        entrance.stop();
        shader.opacity=edge||Tokens.reducedMotion&&rendering?1:0;
        if(!edge&&rendering&&allowed)entrance.start();
    }
    function beginReveal():void {if(active&&revealOnActivate&&allowed&&!working)revealing=true;}
    onRenderingChanged: updateEntrance()
    onActiveChanged: {if(active)Qt.callLater(beginReveal);else revealing=false;}
    onAllowedChanged: if(!allowed){revealing=false;updateEntrance();}
    onWorkingChanged: if(working)revealing=false
    Component.onCompleted: {initialized=true;updateEntrance();Qt.callLater(beginReveal);}
    function diagnostics():var {return {active,rendering,moving,activity,ribbonOpacity:shader.opacity,entranceRunning:entrance.running,shaderStatus:shader.status,shaderError:shader.log,orbitRunning:orbit.running,sweepRunning:sweep.running,primaryColor:String(shader.primaryColor),secondaryColor:String(shader.secondaryColor)};}
    // Start at activation, independent of panel travel and microphone changes.
    NumberAnimation {id:entrance;target:shader;property:"opacity";from:0;to:1;duration:Tokens.animSlow;easing.type:Easing.InOutCubic}
    ShaderEffect {
        id:shader;anchors.fill: parent;visible:root.rendering
        opacity:root.edge?1:0
        property real phase: 0
        UniformAnimator on phase {
            id:orbit;running: root.moving && root.working
            from: 0; to: Math.PI * 2; duration: root.edge ? 6400 : 8000; loops: Animation.Infinite
        }
        property real revealProgress: 1
        property real summon: root.revealing ? 1 : 0
        UniformAnimator on revealProgress {
            id:sweep;running:root.moving&&root.revealing&&!root.working
            from:0;to:1;duration:1400
            onFinished:root.revealing=false
        }
        property real energy: Tokens.reducedMotion ? 0 : root.energy
        property real mode: root.mode
        property real edge: root.edge ? 1 : 0
        property size extent: Qt.size(width, height)
        property real radius: root.radius
        property color primaryColor: root.activity === "error" ? Theme.red : Theme.accent
        property color secondaryColor: root.activity === "error" ? Theme.red : Theme.secondary
        property color tertiaryColor: root.activity === "error" ? Theme.red : Theme.tertiary
        fragmentShader: Qt.resolvedUrl("../assets/shaders/luma-voice.frag.qsb")
    }
}
