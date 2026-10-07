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
    // Only a successful PAM response starts departure. Keep the background
    // composited as one opaque image until then, rather than fading each of its
    // overlapping wallpaper/dim layers separately.
    readonly property bool revealDesktop: !preview && SystemInfo.lockDesktopVisible
    property real arrival: 0
    property bool arrivalStarted:false
    property real departure: 0
    readonly property int transitionDuration: Tokens.reducedMotion ? 0 : Preferences.lockDuration
    onDepartingChanged: if (departing) departureMotion.start()
    property real errorOffset: 0
    readonly property real identityArrival: Math.max(0, Math.min(1, (arrival - .18) / .82))
    readonly property bool departing: !preview && Session.unlocking
    function focusPassword():void {
        // Restore local input focus only on the compositor's active lock surface.
        if(password.enabled && root.Window.window?.active && !password.activeFocus)
            password.forceActiveFocus();
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
    NumberAnimation {id: arrivalMotion; target: root; property: "arrival"; to: 1; duration: root.transitionDuration; easing.type: Easing.OutCubic}
    NumberAnimation {id: departureMotion; target: root; property: "departure"; to: 1; duration: root.transitionDuration; easing.type: Easing.InOutCubic}
    Item {
        id: backdrop
        anchors.fill: parent
        opacity: root.revealDesktop ? root.arrival * (1 - root.departure) : 1
        // This texture exists only while locked. Its static contents are reused
        // throughout departure, without scaling or rebuilding the blur.
        layer.enabled: true
        Rectangle { anchors.fill: parent; color: Theme.wallpaperScrim }
        Image {
            id: wallpaper
            anchors.fill: parent
            source: Session.wallpaperSource
            sourceSize.width: Session.wallpaperDecodeWidth
            fillMode: Image.PreserveAspectCrop
            asynchronous: false; cache: true
        }
        MultiEffect {
            anchors.fill: parent; source: wallpaper
            blurEnabled: Preferences.lockBlur > 0
            blurMax: 48; blur: Preferences.lockBlur; saturation: -.04
            visible: wallpaper.status === Image.Ready && Preferences.lockBlur > 0
        }
        Rectangle { anchors.fill: parent; color: Theme.wallpaperScrim; opacity: Preferences.lockDim }
        Rectangle {
            anchors.fill: parent
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
    Item {
        anchors.fill: parent
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
            width:timeMetrics.advanceWidth;height:font.pixelSize*1.22
            text: Time.timeStr
            font.family: Tokens.clockFont
            font.pixelSize: Math.min(Preferences.lockClockSize, root.height * .18)
            font.weight: Preferences.lockClockStyle === "sculpted" ? Font.DemiBold : Preferences.lockClockStyle === "classic" ? Font.Medium : Font.Light
            font.variableAxes: ({wght:Preferences.lockClockStyle === "sculpted" ? 600 : Preferences.lockClockStyle === "classic" ? 500 : 320, opsz:32})
            font.letterSpacing: Preferences.lockClockStyle === "classic" ? -2 : -4
            font.features: ({tnum:1})
            color: Theme.wallpaperText
        }
        TextMetrics {id:timeMetrics;font:lockTime.font;text:Time.timeStr}
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
            TextInput {
                id: password
                objectName:"lockPassword"
                anchors.fill: parent; anchors.leftMargin: 38; anchors.rightMargin: 38
                verticalAlignment: TextInput.AlignVCenter
                horizontalAlignment: TextInput.AlignHCenter
                color: Session.responseVisible ? Theme.wallpaperText : "transparent"; font.family: Tokens.font; font.pixelSize: 16
                selectionColor:Theme.accent
                selectedTextColor:Session.responseVisible?Theme.wallpaperText:"transparent"
                renderType: Tokens.textRenderType
                Accessible.name: "Login password"
                echoMode: Session.responseVisible ? TextInput.Normal : TextInput.Password
                passwordCharacter: "•"; passwordMaskDelay: 0
                clip: true; focus: true
                enabled: !passwordField.busy && !root.departing
                onEnabledChanged:if(enabled)Qt.callLater(root.focusPassword)
                font.letterSpacing: Session.responseVisible ? 0 : 2
                selectByMouse: false
                // No idle caret slicing through the placeholder. Native editing
                // retains selection/IME behavior once there is input.
                cursorDelegate: Rectangle {
                    width: 1; color: Theme.wallpaperText
                    visible: Session.responseVisible && password.text.length > 0 && password.cursorVisible
                    opacity: password.activeFocus ? 1 : 0
                }
                onAccepted: { if (!root.preview && text.length) { Session.submit(text); clear(); } }
                Keys.onEscapePressed: clear()
                Keys.onTabPressed:event=>{event.accepted=true;}
                Keys.onBacktabPressed:event=>{event.accepted=true;}
                PanelText {
                    anchors.fill: parent; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter
                    opacity: password.text.length || root.departing ? 0 : 1
                    visible: opacity > 0
                    Behavior on opacity { NumberAnimation { duration: Tokens.reducedMotion ? 0 : 90 } }
                    text: passwordField.busy ? "Verifying…" : root.preview ? "Password" : Session.prompt
                    font.pixelSize: 14; color: Theme.withAlpha(Theme.wallpaperText,.72)
                }
            }
            PasswordDots {
                anchors.centerIn:parent;maximumWidth:parent.width-92
                length:Array.from(password.text).length;color:Theme.wallpaperText
                visible:!Session.responseVisible
                opacity:passwordField.busy||root.departing?0:1
                Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
            }
            Item {
                anchors.right: parent.right; anchors.rightMargin: 7; anchors.verticalCenter: parent.verticalCenter
                width: 32; height: 32
                IconButton {
                    anchors.fill: parent; size: 16; label: "Unlock"
                    activeFocusOnTab:false
                    icon: root.departing ? "check" : "arrow_forward"
                    color: Theme.wallpaperText
                    background: Theme.withAlpha(Theme.wallpaperText,.1)
                    // Keep the control visually stable when empty, instead of
                    // applying the shared disabled-opacity jump.
                    opacity: passwordField.busy ? 0 : password.text.length || root.departing ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: Tokens.animFast } }
                    enabled: !root.preview && password.enabled && password.text.length > 0
                    onClicked: { Session.submit(password.text); password.clear(); }
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
    SequentialAnimation {
        id: errorMotion
        NumberAnimation {target: root; property: "errorOffset"; to: -4; duration: 50; easing.type: Easing.OutQuad}
        NumberAnimation {target: root; property: "errorOffset"; to: 4; duration: 70; easing.type: Easing.InOutQuad}
        NumberAnimation {target: root; property: "errorOffset"; to: -2; duration: 65; easing.type: Easing.InOutQuad}
        NumberAnimation {target: root; property: "errorOffset"; to: 0; duration: 90; easing.type: Easing.OutCubic}
    }
    Component.onDestruction:password.clear()
    Connections {
        target: Session
        function onAuthenticatingChanged() {Qt.callLater(root.focusPassword);}
        function onErrorChanged() {if (Session.error && !root.preview && !Tokens.reducedMotion) errorMotion.restart();}
    }
}
