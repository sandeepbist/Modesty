import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes
import Quickshell.Io
import qs.services
import qs.components
import qs.theme

FocusScope {
    id: root
    objectName: "powerPanel"
    property int selected: 2
    readonly property var actions: [
        {icon:"dark_mode", label:"Sleep", action:"suspend", destructive:false},
        {icon:"logout", label:"Log out", action:"logout", destructive:true},
        {icon:"lock", label:"Lock", action:"lock", destructive:false},
        {icon:"restart_alt", label:"Reboot", action:"reboot", destructive:true},
        {icon:"power_settings_new", label:"Power off", action:"poweroff", destructive:true}
    ]
    property int pressTarget: -1
    property string pressOwner: ""
    property int pressKey: 0
    property real progress: 0
    property double uptimeSeconds: -1
    readonly property int holdDuration: 900
    readonly property string uptimeLabel: {
        if (uptimeSeconds < 0) return "Uptime unavailable";
        const minutes = Math.floor(uptimeSeconds / 60);
        const hours = Math.floor(minutes / 60);
        return "Up " + (hours >= 24 ? Math.floor(hours / 24) + " d " : "")
            + (hours > 0 ? hours % 24 + " h " : "") + minutes % 60 + " min";
    }
    implicitHeight: body.implicitHeight
    function measure(): void { IslandState.measurePanel("power", body.implicitHeight + Preferences.innerPadding * 2); }
    function cancelPress(): void {
        hold.stop();
        pressTarget = -1;
        pressOwner = "";
        pressKey = 0;
        progress = 0;
    }
    function invoke(index: int): void {
        const action = actions[index].action;
        if (action === "suspend") Session.requestSleep("suspend");
        else if (action === "lock") Session.lock(false);
        else SystemInfo.action(action, "");
    }
    function beginPress(index: int, owner: string, key: int): void {
        if (!visible || !enabled || pressTarget >= 0) return;
        selected = index;
        pressTarget = index;
        pressOwner = owner;
        pressKey = key;
        if (actions[index].destructive) hold.start();
    }
    function releasePress(index: int, owner: string): void {
        if (pressTarget !== index || pressOwner !== owner) return;
        const safe = !actions[index].destructive;
        cancelPress();
        if (safe && visible && enabled) invoke(index);
    }
    function select(index: int): void {
        cancelPress();
        selected = (index + actions.length) % actions.length;
        buttons.itemAt(selected).forceActiveFocus(Qt.TabFocusReason);
    }
    function accessibleActivate(index: int): void {
        select(index);
        if (!actions[index].destructive) invoke(index);
    }
    function diagnostics(): var { return {selected,pressTarget,pressOwner,progress,height:body.implicitHeight}; }
    Component.onCompleted: Qt.callLater(measure)
    onVisibleChanged: { cancelPress(); if (visible) uptime.reload(); }
    onEnabledChanged: cancelPress()
    onActiveFocusChanged: if (!activeFocus) cancelPress()
    Connections {
        target: root.Window.window
        function onActiveChanged() { if (!root.Window.window.active) root.cancelPress(); }
        function onVisibilityChanged() { root.cancelPress(); }
    }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Escape) {
            const holding = root.pressTarget >= 0;
            root.cancelPress();
            event.accepted = holding;
        }
        else if (event.key === Qt.Key_Left || event.key === Qt.Key_Right) {
            if (!event.isAutoRepeat) root.select(root.selected + (event.key === Qt.Key_Left ? -1 : 1));
            event.accepted = true;
        } else if ([Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter].includes(event.key)) {
            if (!event.isAutoRepeat) root.beginPress(root.selected, "key", event.key);
            event.accepted = true;
        }
    }
    Keys.onReleased: event => {
        if ([Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter].includes(event.key)) {
            if (!event.isAutoRepeat && event.key === root.pressKey) root.releasePress(root.pressTarget, "key");
            event.accepted = true;
        }
    }
    NumberAnimation {
        id: hold
        target: root
        property: "progress"
        from: 0
        to: 1
        duration: root.holdDuration
        onFinished: {
            if (root.pressTarget >= 0 && root.visible && root.enabled)
                root.invoke(root.pressTarget);
        }
    }
    FileView {
        id: uptime
        path: "/proc/uptime"
        printErrors: false
        onLoaded: {
            const seconds = Number(text().slice(0, 64).trim().split(/\s+/)[0]);
            root.uptimeSeconds = Number.isFinite(seconds) && seconds >= 0 ? seconds : -1;
        }
    }
    Timer { interval:60000; repeat:true; running:root.visible; onTriggered:uptime.reload() }
    ColumnLayout {
        id: body
        width: parent.width
        spacing: 0
        onImplicitHeightChanged: root.measure()
        PanelText {
            Layout.fillWidth: true; Layout.topMargin: 5; Layout.preferredHeight: 18
            text: root.uptimeLabel; color: Theme.subtext
            font.pixelSize: Tokens.captionSize; horizontalAlignment: Text.AlignHCenter
        }
        Item {
            Layout.fillWidth: true; Layout.topMargin: 12; Layout.preferredHeight: 66
            Row {
                id: row
                anchors.centerIn: parent
                spacing: Math.min(18, body.width * .045)
                readonly property real diameter: Math.max(0, Math.min(44, (body.width - spacing * 4 - 12) / 5))
                Repeater {
                    id: buttons
                    model: root.actions
                    AbstractButton {
                        id: button
                        required property var modelData
                        required property int index
                        objectName: "power-" + modelData.action
                        width: row.diameter; height: width
                        text: modelData.label
                        readonly property color tone: modelData.destructive ? Theme.red : Theme.accent
                        readonly property bool chosen: root.selected === index
                        readonly property real pressScale: faceMotion.value
                        FrameSpring {
                            id: faceMotion
                            owner: button
                            targetValue: root.pressTarget === button.index ? .95 : 1
                            pressFeedback: true
                            positionTolerance: .0002
                        }
                        Accessible.name: text
                        Accessible.description: modelData.destructive ? "Hold Space, Return, or pointer for 900 milliseconds to " + text.toLowerCase() + ". Release to cancel." : text
                        Accessible.onPressAction: root.accessibleActivate(index)
                        onEnabledChanged: if (!enabled && root.pressTarget === index) root.cancelPress()
                        onVisibleChanged: if (!visible && root.pressTarget === index) root.cancelPress()
                        onActiveFocusChanged: {
                            if (activeFocus) root.selected = index;
                            else if (root.pressTarget === index) root.cancelPress();
                        }
                        Keys.priority: Keys.BeforeItem
                        Keys.forwardTo: [root]
                        Keys.onPressed: event => { event.accepted = false; }
                        Keys.onReleased: event => { event.accepted = false; }
                        background: Rectangle {
                            radius: width / 2
                            scale: button.pressScale
                            color: button.chosen ? Theme.withAlpha(button.tone, button.modelData.destructive ? .18 : .9) : Theme.withAlpha(Theme.text, .07)
                            border.width: 1
                            border.color: button.chosen ? Theme.withAlpha(button.tone, .38) : Theme.withAlpha(Theme.text, .12)
                            Behavior on color { ColorAnimation { duration: Tokens.animFast } }
                            Behavior on border.color { ColorAnimation { duration: Tokens.animFast } }
                        }
                        contentItem: Item {
                            scale: button.pressScale
                            Icon {
                                anchors.centerIn: parent; icon: button.modelData.icon; size: Math.min(19, button.width * .65)
                                color: button.chosen ? (button.modelData.destructive ? Theme.red : Theme.accentText) : Theme.subtext
                                Behavior on color { ColorAnimation { duration: Tokens.animFast } }
                            }
                        }
                        Shape {
                            id: ring
                            anchors.fill: parent
                            anchors.margins: -5
                            opacity: root.pressTarget === button.index && button.modelData.destructive ? 1 : 0
                            visible: opacity > 0
                            Behavior on opacity { NumberAnimation { duration: Tokens.animFast; easing.type: Easing.OutCubic } }
                            preferredRendererType: Shape.CurveRenderer
                            ShapePath {
                                fillColor: "transparent"
                                strokeWidth: 2.5
                                strokeColor: Theme.withAlpha(button.tone, .2)
                                PathAngleArc {
                                    centerX: ring.width / 2; centerY: ring.height / 2
                                    radiusX: centerX - 2; radiusY: radiusX
                                    startAngle: -90; sweepAngle: 360
                                }
                            }
                            ShapePath {
                                fillColor: "transparent"
                                strokeWidth: 2.5
                                strokeColor: button.tone
                                capStyle: ShapePath.RoundCap
                                PathAngleArc {
                                    centerX: ring.width / 2; centerY: ring.height / 2
                                    radiusX: centerX - 2; radiusY: radiusX
                                    startAngle: -90; sweepAngle: root.progress * 360
                                }
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onEntered: if (root.pressTarget < 0) root.selected = button.index
                            onPressed: { button.forceActiveFocus(Qt.MouseFocusReason); root.beginPress(button.index, "pointer", 0); }
                            onReleased: root.releasePress(button.index, "pointer")
                            onExited: if (root.pressTarget === button.index && root.pressOwner === "pointer") root.cancelPress()
                            onCanceled: root.cancelPress()
                        }
                    }
                }
            }
        }
        RollingText {
            Layout.fillWidth: true; Layout.topMargin: 7; Layout.preferredHeight: 19
            text: {
                const action = root.actions[root.selected];
                return hold.running ? "Keep holding to " + action.label.toLowerCase() : action.label;
            }
            color: root.actions[root.selected].destructive ? Theme.red : Theme.text
            Behavior on color { ColorAnimation { duration: Tokens.animFast } }
            font.pixelSize: Tokens.captionSize + 1
            Accessible.ignored: true
        }
    }
}
