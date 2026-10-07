import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Services.UPower

Scope {
    id: root
    readonly property bool enabled: Quickshell.env("MODESTY_COMPAT") === "1" && Quickshell.env("MODESTY_PREVIEW") !== "1"
    property bool sleeping: false
    property bool inhibitAudio: true
    property bool inhibitCharging: false
    property var rules: [{ timeout: 180, idleAction: "lock" }, { timeout: 300, idleAction: "dpms off", returnAction: "dpms on" }, { timeout: 600, idleAction: ["systemctl", "suspend-then-hibernate"] }]
    FileView {
        path: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/modesty/session.json"
        printErrors: false
        onLoaded: {
            try { const config = JSON.parse(text()).general?.idle; if (config) { if (Array.isArray(config.timeouts)) root.rules = config.timeouts; root.inhibitAudio = config.inhibitWhenAudio ?? true; root.inhibitCharging = config.inhibitWhenCharging ?? false; } }
            catch (e) { console.warn("Could not read idle settings; using 3/5/10 minute defaults"); }
        }
    }
    function action(value): void {
        if (!enabled || !value) return;
        if (value === "lock") Session.lock(false);
        else if (value === "dpms off" || value === "dpms on") Quickshell.execDetached(["hyprctl", "eval", "hl.dispatch(hl.dsp.dpms({action='" + (value === "dpms off" ? "disable" : "enable") + "'}))"]);
        else if (Array.isArray(value) && value[0] === "systemctl" && ["suspend", "suspend-then-hibernate", "hibernate", "hybrid-sleep"].includes(value[1])) Session.requestSleep(value[1]);
    }
    Variants {
        model: root.enabled ? root.rules : []
        IdleMonitor {
            required property var modelData
            timeout: Math.max(1, modelData.timeout || 180)
            enabled: !KeepAwake.active && (modelData.enabled ?? true) && !(root.inhibitAudio && Media.playing) && !(root.inhibitCharging && !UPower.onBattery)
            respectInhibitors: modelData.respectInhibitors ?? true
            onIsIdleChanged: root.action(isIdle ? modelData.idleAction : modelData.returnAction)
        }
    }
    Process {
        id: events
        running: root.enabled
        stdinEnabled: true
        command: ["python3", Qt.resolvedUrl("../scripts/session-events.py").toString().replace("file://", "")]
        stdout: SplitParser {
            onRead: line => {
                try {
                    const data = JSON.parse(line);
                    if (data.event === "ready") events.write(JSON.stringify({awake:KeepAwake.active})+"\n");
                    else if (data.event === "awake" && data.error) {KeepAwake.error=data.error;KeepAwake.active=false;}
                    else if (data.event === "sleep") { root.sleeping = true; Session.lock(false); if (Session.secure) events.write(JSON.stringify({secure: true, locked: true}) + "\n"); }
                    else if (data.event === "lock") Session.lock(false);
                    else if (data.event === "resume") root.sleeping = false;
                    else if (data.event === "error") SystemInfo.error = "Session integration: " + data.message;
                } catch (e) { console.warn("Invalid session event"); }
            }
        }
        onExited: exitCode => { if (root.enabled && exitCode !== 0) { SystemInfo.error = "Session event listener stopped; retrying."; retry.restart(); } }
    }
    Timer { id: retry; interval: 5000; onTriggered: if (root.enabled) events.running = true }
    Connections {target:KeepAwake;function onActiveChanged(){if(events.running)events.write(JSON.stringify({awake:KeepAwake.active})+"\n");}}
    Connections {
        target: Session
        function onSecureChanged() { if (events.running) events.write(JSON.stringify({locked: Session.secure, secure: root.sleeping && Session.secure}) + "\n"); }
    }
}
