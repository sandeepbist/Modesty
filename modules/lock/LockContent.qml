import QtQuick
import QtQuick.Effects
import QtQuick.Controls
import QtQuick.Window
import Quickshell
import qs.services
import qs.components
import qs.theme
Item {
    id: root
    property bool preview: false
    property bool previewDeparting: false
    // Only a successful PAM response starts departure. Keep the background
    // composited as one opaque image until then, rather than fading each of its
    // overlapping wallpaper/dim layers separately.
    readonly property bool revealDesktop: !preview && SystemInfo.lockDesktopVisible
    property real arrival: 0
    property bool arrivalStarted:false
    property real departure: 0
    readonly property bool modern: Preferences.lockScreenStyle === "modern"
    readonly property int transitionDuration: Tokens.lockTransitionDuration
    readonly property real departureElapsed: departure * Tokens.lockDepartureDuration
    readonly property real clockDockedAt: Tokens.lockReturnLead + transitionDuration
    readonly property real desktopRevealAt: clockDockedAt + Tokens.lockReboundDuration
    readonly property real clockDeparture: {
        if (!Tokens.modernLockMotion) return departure;
        const travel = Math.max(0, Math.min(1, (departureElapsed - Tokens.lockReturnLead) / transitionDuration));
        if (departureElapsed <= clockDockedAt || !Tokens.lockReboundDuration)
            return (1 - Math.cos(Math.PI * travel)) / 2;
        const settle = Math.min(1, (departureElapsed - clockDockedAt) / Tokens.lockReboundDuration);
        const lift = Math.sin(Math.PI * settle);
        return 1 + .006 * lift * lift;
    }
    readonly property real desktopReveal: Tokens.modernLockMotion
        ? Tokens.smoothStep((departureElapsed - desktopRevealAt) / Tokens.lockDesktopFade) : departure
    onDepartingChanged: if (departing || (departure > 0 && Session.locked)) {
        departureMotion.stop();
        departureMotion.to = departing ? 1 : 0;
        departureMotion.start();
    }
    property real errorOffset: 0
    readonly property real identityArrival: Math.max(0, Math.min(1, (arrival - .18) / .82))
    readonly property bool departing: preview ? previewDeparting : Session.unlocking
    function focusPassword():void {
        // Restore local input focus only on the compositor's active lock surface.
        const input = presentation.item?.passwordInput;
        if (input?.enabled && root.Window.window?.active && !input.activeFocus)
            input.forceActiveFocus();
    }
    Component.onCompleted: {
        if (!SystemInfo.lockWallpaper && !SystemInfo.wallpaper && !SystemInfo.wallpapers.length) SystemInfo.scanWallpapers();
        Qt.callLater(focusPassword);
    }
    // Start after the first presented buffer, not while the lock surface and
    // its cached blur are still being created. Input remains compositor-locked.
    Connections {
        target:root.Window.window
        function onFrameSwapped(){if(!root.arrivalStarted){root.arrivalStarted=true;arrivalMotion.start();}}
        function onActiveChanged(){Qt.callLater(root.focusPassword);}
        function onActiveFocusItemChanged(){Qt.callLater(root.focusPassword);}
    }
    NumberAnimation {id: arrivalMotion; target: root; property: "arrival"; to: 1; duration: root.transitionDuration; easing.type: root.modern ? Easing.InOutSine : Easing.OutCubic}
    NumberAnimation {id: departureMotion; target: root; property: "departure"; duration: Tokens.lockDepartureDuration; easing.type: root.modern ? Easing.Linear : Easing.InOutCubic}
    Item {
        id: backdrop
        anchors.fill: parent
        opacity: root.revealDesktop ? root.arrival * (1 - root.desktopReveal) : 1
        // This texture exists only while locked. Its static contents are reused
        // throughout departure, without scaling or rebuilding the blur.
        layer.enabled: !root.modern || root.revealDesktop
        Rectangle { anchors.fill: parent; color: Theme.wallpaperScrim }
        Image {
            id: wallpaperImage
            anchors.fill: parent
            source: Session.wallpaperSource
            sourceSize.width: Session.wallpaperDecodeWidth
            fillMode: Image.PreserveAspectCrop
            asynchronous: false; cache: true
        }
        MultiEffect {
            anchors.fill: parent; source: wallpaperImage
            blurEnabled: !root.modern && Preferences.lockBlur > 0
            blurMax: 48; blur: Preferences.lockBlur; saturation: -.04
            visible: wallpaperImage.status === Image.Ready && blurEnabled
        }
        Rectangle {
            anchors.fill: parent
            color: Theme.wallpaperScrim
            opacity: Preferences.lockDim * (root.modern && !root.revealDesktop ? root.arrival * (1 - root.desktopReveal) : 1)
        }
        Rectangle {
            anchors.fill: parent
            visible: !root.modern
            gradient: Gradient {
                GradientStop { position: 0; color: "#18000000" }
                GradientStop { position: .45; color: "#00000000" }
                GradientStop { position: 1; color: "#50000000" }
            }
        }
        MouseArea {
            anchors.fill:parent;acceptedButtons:Qt.AllButtons
            onPressed:root.focusPassword()
        }
    }
    Loader {
        id: presentation
        anchors.fill: parent
        focus: true
        opacity: root.modern && root.revealDesktop ? 1 - root.desktopReveal : 1
        sourceComponent: root.modern ? modernView : legacyView
        onLoaded: Qt.callLater(root.focusPassword)
    }
    Component {
        id: modernView
        ModernLockView {
            preview: root.preview; departing: root.departing
            arrival: root.arrival; departure: root.clockDeparture
            wallpaper: wallpaperImage
        }
    }
    Component {
        id: legacyView
        Item {
        readonly property alias passwordInput: password
        opacity: root.arrival*(1-root.departure)
        transform: Translate { y: 14 * (1 - root.arrival) - 10 * root.departure }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: Math.max(42, parent.height * .105)
        spacing: 4
        PanelText {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Time.format("dddd, MMMM d")
            font.pixelSize: 18; font.weight: Font.Medium
            color: Theme.withAlpha(Theme.wallpaperText,.9)
        }
        SlidingDigits {
            id:lockTime
            anchors.horizontalCenter: parent.horizontalCenter
            width:implicitWidth;height:font.pixelSize*1.22
            text: Time.timeStr
            font.family: Tokens.clockFont
            font.pixelSize: Math.min(Preferences.lockClockSize, root.height * .18)
            font.weight: Preferences.lockClockStyle === "sculpted" ? Font.DemiBold : Preferences.lockClockStyle === "classic" ? Font.Medium : Font.Light
            font.variableAxes: ({wght:Preferences.lockClockStyle === "sculpted" ? 600 : Preferences.lockClockStyle === "classic" ? 500 : 320, opsz:32})
            tracking: Preferences.lockClockStyle === "classic" ? -2 : -4
            font.features: ({tnum:1})
            color: Theme.wallpaperText
        }
    }
    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: Math.max(root.height * .48, root.height - implicitHeight - Math.max(42, root.height * .075))
        spacing: 14
        opacity: root.identityArrival
        transform: Translate { y: 12 * (1 - root.identityArrival) }
        Rectangle {
            anchors.horizontalCenter:parent.horizontalCenter;width:72;height:72;radius:36
            color:Theme.withAlpha(Theme.wallpaperText,.065);border.width:1;border.color:Theme.withAlpha(Theme.wallpaperText,.15);antialiasing:true
            ProfileAvatar {anchors.centerIn:parent;width:64;height:64}
        }

        PanelText { anchors.horizontalCenter: parent.horizontalCenter; text: Quickshell.env("USER"); font.pixelSize: 15; font.weight: Font.Medium; color: Theme.wallpaperText }
        Rectangle {
            id: passwordField
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(272, root.width - 48); height: 46; radius: 23
            antialiasing: true
            transform: Translate { x: root.errorOffset }
            readonly property bool busy: !root.preview && Session.authenticating
            readonly property bool hasError: !root.preview && !!Session.error
            color: Theme.withAlpha(hasError ? Theme.red : "#ffffff", password.activeFocus ? .14 : .09)
            border.width: 0
            Behavior on color { ColorAnimation { duration: Tokens.animMedium } }
            LockPasswordInput {
                id: password
                anchors.fill: parent; anchors.leftMargin: 38; anchors.rightMargin: 38
                preview: root.preview
                departing: root.departing
                onEnabledChanged:if(enabled)Qt.callLater(root.focusPassword)
                PanelText {
                    anchors.fill: parent; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter
                    opacity: password.text.length || root.departing ? 0 : 1
                    visible: opacity > 0
                    Behavior on opacity { NumberAnimation { duration: Tokens.reducedMotion ? 0 : 90 } }
                    text: passwordField.busy ? "" : root.preview ? "Password" : Session.prompt
                    font.pixelSize: 14; color: Theme.withAlpha(Theme.wallpaperText,.72)
                }
            }
            PasswordDots {
                anchors.centerIn:parent;maximumWidth:parent.width-92
                length:Array.from(password.text).length;color:Theme.wallpaperText
                visible:!password.responseVisible
                opacity:passwordField.busy||root.departing?0:1
                Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
            }
            Item {
                anchors.right: parent.right; anchors.rightMargin: 7; anchors.verticalCenter: parent.verticalCenter
                width: 32; height: 32
                IconButton {
                    anchors.fill: parent; size: 16; label: "Unlock"
                    activeFocusOnTab:false
                    icon: "arrow_forward"
                    color: Theme.wallpaperText
                    background: Theme.withAlpha(Theme.wallpaperText,.1)
                    // Keep the control visually stable when empty, instead of
                    // applying the shared disabled-opacity jump.
                    opacity: passwordField.busy || root.departing || !password.text.length ? 0 : 1
                    Behavior on opacity { NumberAnimation { duration: Tokens.animFast } }
                    enabled: !root.preview && password.enabled && password.text.length > 0
                    onClicked: password.submit()
                }
                BusyIndicator {
                    anchors.fill: parent
                    running: passwordField.busy && !Tokens.reducedMotion
                    visible: passwordField.busy
                    palette.dark: Theme.accent; palette.light: Theme.accent
                }
            }
        }
        PanelText { anchors.horizontalCenter: parent.horizontalCenter; width: Math.min(380, root.width - 40); height: 36; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap; elide: Text.ElideNone; text: root.preview ? "" : Session.error; color: Theme.red; font.pixelSize: 12; opacity:text.length?1:0; Behavior on opacity {NumberAnimation {duration:Tokens.animFast}} }
    }
    }
    }
    SequentialAnimation {
        id: errorMotion
        NumberAnimation {target: root; property: "errorOffset"; to: -4; duration: 50; easing.type: Easing.OutQuad}
        NumberAnimation {target: root; property: "errorOffset"; to: 4; duration: 70; easing.type: Easing.InOutQuad}
        NumberAnimation {target: root; property: "errorOffset"; to: -2; duration: 65; easing.type: Easing.InOutQuad}
        NumberAnimation {target: root; property: "errorOffset"; to: 0; duration: 90; easing.type: Easing.OutCubic}
    }
    Connections {
        target: Session
        function onAuthenticatingChanged() {Qt.callLater(root.focusPassword);}
        function onUnlockingChanged() { if (Session.unlocking && !root.preview) presentation.item?.passwordInput.clear(); }
        function onErrorChanged() {if (Session.error && !root.modern && !root.preview && !Tokens.reducedMotion) errorMotion.restart();}
    }
}
