import QtQuick
import qs.services
import qs.theme
import "SpringPhysics.js" as Physics

QtObject {
    id: root
    property real targetValue: 0
    property Item owner: null
    property real value: targetValue
    property real velocity: 0
    property bool pressFeedback: false
    readonly property real frequency: pressFeedback ? 7 : 4.8
    readonly property real dampingRatio: Preferences.motion === "gentle" ? 1 : .75
    property real positionTolerance: .25
    readonly property real velocityTolerance: positionTolerance * 2 * Math.PI * frequency * Preferences.motionSpeed
    property real minimumValue: -Infinity
    property real maximumValue: Infinity
    readonly property bool available: !Tokens.reducedMotion && (!owner || (owner.visible && owner.enabled && (!owner.Window.window || owner.Window.window.visible)))
    property bool enabled: available
    readonly property bool running: frames.running
    property bool ready: false

    function reset(position: real): void {
        frames.stop();
        velocity = 0;
        value = position;
    }
    function finish(): void { reset(targetValue); }
    function start(): void {
        if (!ready || !enabled) finish();
        else if (Math.abs(value - targetValue) > positionTolerance || Math.abs(velocity) > velocityTolerance) frames.start();
        else finish();
    }
    onTargetValueChanged: start()
    onEnabledChanged: if (!enabled) finish()
    Component.onCompleted: { finish(); ready = true; }

    property FrameAnimation frames: FrameAnimation {
        onTriggered: {
            const next = Physics.step(root.value, root.velocity, root.targetValue, frameTime,
                                      root.frequency * Preferences.motionSpeed, root.dampingRatio);
            root.value = next[0];
            root.velocity = next[1];
            // A constrained endpoint has no visible rebound beyond its boundary.
            if ((root.targetValue <= root.minimumValue && root.value <= root.minimumValue && root.velocity <= 0)
                    || (root.targetValue >= root.maximumValue && root.value >= root.maximumValue && root.velocity >= 0)
                    || (Math.abs(root.value - root.targetValue) <= root.positionTolerance
                        && Math.abs(root.velocity) <= root.velocityTolerance)) root.finish();
        }
    }
}
