import QtQuick
import QtQuick.Controls
import Quickshell.Widgets
import qs.components
import qs.services
import qs.theme

Item {
    id: root
    required property bool preview
    required property bool departing
    required property real arrival
    required property real departure
    required property Image wallpaper
    readonly property alias passwordInput: password

    readonly property real clockTravel: arrival * (1 - departure)
    readonly property real capsuleTravel: Tokens.smoothStep(clockTravel * 3)
    readonly property real compactMix: Tokens.smoothStep(1 - clockTravel / .045)
    readonly property real compactHeight: Preferences.barHeight * Preferences.uiScale
    readonly property real compactWidth: Math.max(Preferences.collapsedWidth + (Preferences.showSeconds ? 20 : 0),
        compactMetrics.advanceWidth + 40) * Preferences.uiScale
    readonly property real compactCenter: Preferences.topMargin + compactHeight / 2
    readonly property real lockedCenter: Math.max(compactCenter + 14, height * .055)
    readonly property real clockCenter: compactCenter + Math.max(-Preferences.topMargin, (height * .493 - compactCenter) * clockTravel)
    readonly property real capsuleLimit: Math.max(0, Math.min(width - 24, 320))
    readonly property real restingCapsuleWidth: 50
    readonly property real typingWidth: Math.max(restingCapsuleWidth, typingMotion.value)
    readonly property int clockSize: Math.max(12, Math.round(Math.min(height * .34,
        width * (Preferences.showSeconds ? .136 : .21), 368) * Preferences.lockClockSize / 160))
    readonly property bool foldingAttempt: rejectedPulse.running && typingWidth > restingCapsuleWidth + 4
    readonly property bool showError: !preview && !password.busy && !departing && !password.length
        && !submittedDots && !foldingAttempt && !!Session.error
    readonly property int typedDots: password.echoMode === TextInput.Password ? Math.min(64, Array.from(password.text).length) : 0
    readonly property int dotCount: submittedDots || typedDots
    property int submittedDots: 0
    property real dotOpacity: 1

    function resetAttempt(): void {
        rejectedPulse.stop();
        submittedDots = 0;
        dotOpacity = 1;
    }
    onDepartingChanged: if (departing) {
        rejectedPulse.stop();
        submittedDots = 0;
    }
    Connections {
        target: Session
        function onErrorChanged() {
            if (!Session.error || !root.submittedDots || root.departing) return;
            if (Tokens.reducedMotion) root.resetAttempt();
            else rejectedPulse.restart();
        }
    }
    Connections {
        target: Tokens
        function onReducedMotionChanged() { if (Tokens.reducedMotion && rejectedPulse.running) root.resetAttempt(); }
    }
    SequentialAnimation {
        running: root.submittedDots > 0 && password.busy && !root.departing && !rejectedPulse.running && !Tokens.reducedMotion
        loops: Animation.Infinite
        NumberAnimation { target: root; property: "dotOpacity"; to: .38; duration: Tokens.animFast; easing.type: Easing.InOutSine }
        NumberAnimation { target: root; property: "dotOpacity"; to: 1; duration: Tokens.animFast; easing.type: Easing.InOutSine }
    }
    SequentialAnimation {
        id: rejectedPulse
        NumberAnimation { target: root; property: "dotOpacity"; to: .38; duration: Math.round(Tokens.animFast * .55); easing.type: Easing.InOutSine }
        NumberAnimation { target: root; property: "dotOpacity"; to: 1; duration: Math.round(Tokens.animFast * .6); easing.type: Easing.InOutSine }
        ScriptAction { script: root.submittedDots = 0 }
        PauseAnimation { duration: Tokens.animSlow }
    }

    ClippingRectangle {
        id: pill
        objectName: "modernLockCapsule"
        x: (parent.width - width) / 2 + (compactPlane.x + compactPlane.width/2 - parent.width/2) * root.compactMix
        y: Math.min(root.compactCenter, root.clockCenter) + (root.lockedCenter - root.compactCenter) * root.capsuleTravel - height / 2
        width: Math.min(root.capsuleLimit, root.compactWidth + (root.typingWidth - root.compactWidth) * root.capsuleTravel)
        height: root.compactHeight + (Preferences.barHeight - root.compactHeight) * root.capsuleTravel
        radius: height / 2
        color: Qt.tint("#fa080a0a", Theme.withAlpha(Theme.bgSolid, root.compactMix))
        antialiasing: true
        contentInsideBorder: false
        border.width: root.departing ? 0 : 1
        border.color: Theme.withAlpha(Theme.red, rejectedPulse.running ? .5 : 0)
        Behavior on border.color { ColorAnimation { duration: Tokens.animFast } }

        FrameSpring {
            id: typingMotion
            owner: pill
            targetValue: password.responseVisible ? 286 : root.restingCapsuleWidth + root.dotCount * dots.pitch
            frequency: 5.4
            dampingRatio: .82
            positionTolerance: .08
        }

        LockPasswordInput {
            id: password
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            preview: root.preview
            departing: root.departing
            onSubmitting: {
                root.resetAttempt();
                root.submittedDots = root.typedDots;
            }
            onLengthChanged: if (length && (root.submittedDots || rejectedPulse.running)) root.resetAttempt()
            onBusyChanged: if (!busy) Qt.callLater(() => {
                if (!busy && !root.departing && !rejectedPulse.running) root.resetAttempt();
            })
        }

        Item {
            anchors.fill: parent
            opacity: root.capsuleTravel * (1 - root.departure)
            visible: opacity > 0

            Icon {
                objectName: "modernLockStatusIcon"
                anchors.centerIn: parent
                icon: "lock"
                size: 15
                color: root.showError ? Theme.red : Theme.wallpaperText
                visible: !root.departing && opacity > 0
                opacity: root.departing || password.busy || root.dotCount || root.foldingAttempt
                    || password.length || password.responseVisible ? 0 : 1
                Behavior on opacity { NumberAnimation { duration: Tokens.animFast; easing.type: Easing.OutCubic } }
            }
            PasswordDots {
                id: dots
                objectName: "modernLockDots"
                anchors.centerIn: parent
                length: root.dotCount
                maximumWidth: Math.max(0, pill.width - 20)
                pitch: 12
                dotSize: 6
                animatedSpan: root.typingWidth - root.restingCapsuleWidth
                color: Theme.wallpaperText
                opacity: Tokens.reducedMotion || (!root.submittedDots && !root.departing) ? 1 : root.dotOpacity
            }
            BusyIndicator {
                anchors.centerIn: parent
                width: 18; height: 18
                visible: password.busy && !root.dotCount && !root.departing && !Tokens.reducedMotion
                running: visible
                palette.dark: Theme.accent
                palette.light: Theme.accent
            }
            Icon { anchors.centerIn: parent; visible: password.busy && !root.dotCount && !root.departing && Tokens.reducedMotion; icon: "lock"; size: 15; color: Theme.accent }
        }
    }

    SlidingDigits {
        id: clock
        objectName: "modernLockClock"
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.clockCenter - height / 2
        width: implicitWidth
        height: font.pixelSize * 1.25
        text: Time.timeStr
        font.family: Tokens.clockFont
        font.pixelSize: root.clockSize
        font.weight: Font.ExtraBold
        tracking: -root.clockSize * .032
        font.features: ({tnum: 1})
        color: layer.enabled ? "white" : Theme.withAlpha(foregroundTone, .91)
        opacity: 1 - root.compactMix
        visible: opacity > 0
        scale: compactScale + (1 - compactScale) * root.clockTravel * (1 - root.compactMix)
        readonly property real compactScale: Tokens.pillTextSize * Preferences.uiScale / font.pixelSize
        readonly property real horizontalSqueeze: 1 - .16 * root.clockTravel
        readonly property real glassReveal: Tokens.smoothStep(root.clockTravel / .25)
        readonly property color foregroundTone: Qt.tint(Theme.text, Theme.withAlpha(Theme.wallpaperText, glassReveal))
        transform: Scale {
            origin.x: clock.width / 2
            xScale: clock.horizontalSqueeze
        }
        layer.enabled: visible && Preferences.lockFrost > 0 && root.wallpaper.status === Image.Ready && GraphicsInfo.api !== GraphicsInfo.Software
        layer.smooth: true
        layer.effect: ShaderEffect {
            property var source
            property Image backdrop: root.wallpaper
            property real glassAmount: clock.glassReveal * Preferences.lockFrost / 100
            property color frostTint: clock.foregroundTone
            property vector2d blurStep: Qt.vector2d(13 / Math.max(1, backdrop.paintedWidth), 13 / Math.max(1, backdrop.paintedHeight))
            property vector4d sampleRect: {
                const w = clock.width * clock.scale * clock.horizontalSqueeze / Math.max(1, backdrop.paintedWidth);
                const h = clock.height * clock.scale / Math.max(1, backdrop.paintedHeight);
                const y = (root.clockCenter - root.height / 2) / Math.max(1, backdrop.paintedHeight);
                return Qt.vector4d((1 - w) / 2, (1 - h) / 2 + y, w, h);
            }
            fragmentShader: Qt.resolvedUrl("../../assets/shaders/lock-clock.frag.qsb")
        }
    }
    Item {
        id: compactPlane
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.clockCenter - root.compactHeight / 2
        width: root.width / Preferences.uiScale
        height: Preferences.barHeight
        scale: Preferences.uiScale
        transformOrigin: Item.Top

        RollingText {
            id: compactClock
            objectName: "modernLockCompactClock"
            x: (parent.width - width) / 2
            width: compactMetrics.advanceWidth + 2
            height: parent.height
            opacity: root.compactMix
            visible: opacity > 0
            text: Time.timeStr
            slideDigits: true
            font.family: Tokens.clockFont
            font.pixelSize: Tokens.pillTextSize
            font.weight: Font.DemiBold
            font.kerning: true
            font.hintingPreference: Font.PreferVerticalHinting
            font.preferTypoLineMetrics: true
            font.features: ({tnum: 1})
        }
    }
    TextMetrics { id: compactMetrics; text: compactClock.text; font: compactClock.font }

    PanelText {
        objectName: "modernLockPrompt"
        anchors.horizontalCenter: parent.horizontalCenter
        y: pill.y + pill.height + 10
        width: Math.max(0, Math.min(root.width - 24, 360))
        text: root.showError ? Session.error : password.responseVisible ? Session.prompt : ""
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
        elide: Text.ElideNone
        font.pixelSize: Tokens.textSize(13)
        color: root.showError ? Theme.red : Theme.wallpaperText
        visible: opacity > 0
        opacity: text.length && !root.departing ? root.capsuleTravel : 0
        Behavior on opacity { NumberAnimation { duration: Tokens.animFast } }
    }
}
