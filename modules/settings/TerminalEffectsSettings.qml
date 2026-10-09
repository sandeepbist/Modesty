import QtQuick
import QtQuick.Layouts
import Quickshell.Io
import qs.services
import qs.components
import qs.theme

ColumnLayout {
    id: root
    objectName: "terminalEffectsSettings"
    spacing: 10
    property string availability: "checking"
    property bool trailEnabled: false
    property string message: "Checking optional Kitty profile..."
    property string error: ""
    readonly property string backend: Qt.resolvedUrl("../../scripts/terminal-effects.py").toString().replace("file://", "")
    readonly property string installer: Qt.resolvedUrl("../../install.py").toString().replace("file://", "")
    readonly property bool busy: operation.running || setup.running
    readonly property bool actionsAllowed: !busy && !Preferences.preview && !Session.locked
    function refresh(): void {
        if (!busy) {
            operation.command = ["python3", backend, "--status"];
            operation.running = true;
        }
    }
    function perform(args): void {
        if (!actionsAllowed) return;
        error = "";
        operation.command = ["python3", backend].concat(args);
        operation.running = true;
    }
    function reveal(key) {
        if (!actionsAllowed) return statusText;
        if (key === "setup" || availability !== "ready") return setupButton;
        return key === "open" ? openButton : trail.control;
    }
    Component.onCompleted: refresh()
    Process {
        id: operation
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    root.availability = result.availability;
                    root.trailEnabled = result.enabled;
                    root.message = result.message;
                    if (result.availability === "error") root.error = result.message;
                } catch (e) {
                    root.availability = "error";
                    root.error = "Could not read terminal effects status.";
                }
            }
        }
        onExited: code => { if (code !== 0 && !root.error) root.error = "Terminal action failed. Run optional setup to repair it."; }
    }
    Process {
        id: setup
        command: ["foot", "--title=Modesty terminal setup", "python3", root.installer, "--install-terminal-effects"]
        onExited: code => {
            if (code !== 0) root.error = "Terminal setup did not finish. Retry setup to review approvals.";
            root.refresh();
        }
    }
    PreferenceSwitch {
        id: trail
        Layout.fillWidth: true
        label: "Native cursor trail"
        description: "Applies to new Modesty Kitty windows. Foot cannot animate cursor movement."
        checked: root.trailEnabled
        enabled: root.actionsAllowed && root.availability === "ready"
        onToggled: checked => root.perform(["--set-trail", checked ? "on" : "off"])
    }
    PanelText {
        id: statusText
        activeFocusOnTab: true
        Accessible.name: text
        objectName: "terminalEffectsStatus"
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        elide: Text.ElideNone
        text: root.error || root.message
        font.pixelSize: 12
        color: root.error ? Theme.red : Theme.subtext
    }
    Flow {
        Layout.fillWidth: true
        spacing: 8
        ActionButton {
            id: setupButton
            objectName: "terminalEffectsSetup"
            text: root.availability === "ready" ? "Repair optional profile" : "Set up optional profile"
            enabled: root.actionsAllowed
            onClicked: { if (root.actionsAllowed) { root.error = ""; setup.running = true; } }
        }
        ActionButton {
            id: openButton
            objectName: "terminalEffectsOpen"
            text: "Open animated terminal"
            enabled: root.actionsAllowed && root.availability === "ready"
            onClicked: root.perform(["--open"])
        }
    }
    PanelText {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        elide: Text.ElideNone
        text: Preferences.preview ? "Preview session actions are disabled." : Session.locked ? "Unlock to change or launch the optional profile." : "Setup asks separately for Kitty packages and file changes. Foot, Super+T and ordinary Kitty stay unchanged."
        font.pixelSize: 12
        color: Theme.subtext
    }
}
