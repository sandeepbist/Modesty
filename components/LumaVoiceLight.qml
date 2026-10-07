import QtQuick
import qs.theme
import qs.services

// Palette light stays on the render thread; no canvas, timers or audio inference.
Item {
    id: root
    property string activity: "listening"
    property real level: 0
    property bool active: true
    property bool edge: false
    property real radius: 24
    readonly property real measuredEnergy: activity === "listening" ? Math.pow(Math.max(0, Math.min(1, level)), .75) : 0
    property real energy: measuredEnergy
    property real mode: activity === "finishing" ? 1 : activity === "acting" ? 3 : activity === "thinking" ? 2 : 0
    readonly property bool moving: active && visible && opacity > 0 && !["error","idle"].includes(activity) && Preferences.lumaEffects && !Tokens.reducedMotion
    implicitWidth: 260
    implicitHeight: 64
    Behavior on energy { SmoothedAnimation { velocity: -1; duration: root.measuredEnergy > root.energy ? 55 : 220; reversingMode: SmoothedAnimation.Immediate } }
    Behavior on mode { NumberAnimation { duration: Tokens.animSlow; easing.type: Easing.InOutCubic } }
    ShaderEffect {
        anchors.fill: parent
        property real phase: 0
        UniformAnimator on phase {
            running: root.moving
            from: 0; to: Math.PI * 2; duration: 8000; loops: Animation.Infinite
        }
        property real energy: Tokens.reducedMotion ? 0 : root.energy
        property real mode: root.mode
        property real edge: root.edge ? 1 : 0
        property size extent: Qt.size(width, height)
        property real radius: root.radius
        property color primaryColor: root.activity === "error" ? Theme.red : Theme.accent
        property color secondaryColor: root.activity === "error" ? Theme.red : Theme.pal.secondary ? Theme.secondary : Theme.green
        property color tertiaryColor: root.activity === "error" ? Theme.red : Theme.pal.tertiary ? Theme.tertiary : Theme.yellow
        fragmentShader: Qt.resolvedUrl("../assets/shaders/luma-voice.frag.qsb")
    }
}
