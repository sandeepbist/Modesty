pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Bluetooth

Singleton {
    id: root
    readonly property bool preview: Quickshell.env("MODESTY_PREVIEW") === "1"
    readonly property var adapter: Bluetooth.defaultAdapter
    readonly property bool available: !!adapter
    readonly property bool enabled: adapter?.enabled ?? false
    readonly property bool blocked: adapter?.state === BluetoothAdapterState.Blocked
    readonly property var devices: (adapter?.devices.values ?? []).slice().sort((a,b) => Number(b.connected) - Number(a.connected) || Number(b.paired) - Number(a.paired) || a.name.localeCompare(b.name))
    property string error: ""
    property string status: ""
    property string deviceName: ""
    property string prompt: ""
    property string code: ""
    readonly property bool busy: operation.running
    property bool receivedResult: false
    property bool scanRequested: false
    function startScan(): void { if (preview || !enabled) return; scanRequested = true; scanTimeout.restart(); }
    function stopScan(): void { scanRequested = false; scanTimeout.stop(); }
    Binding { target: root.adapter; property: "discovering"; value: root.scanRequested; when: !!root.adapter && !root.preview; restoreMode: Binding.RestoreBindingOrValue }
    Timer { id: scanTimeout; interval: 20000; onTriggered: root.scanRequested = false }
    Connections { target: IslandState; function onMenuChanged() { if (IslandState.menu !== "bluetooth") { root.stopScan(); if (root.busy) root.cancel(); } } }
    function act(device, action: string): void {
        if (preview) { error = "Preview — Bluetooth changes are disabled"; return; }
        if (!device || busy) return;
        error = ""; prompt = ""; code = ""; receivedResult = false;
        deviceName = device.name;
        status = action === "pair" ? "Pairing with " + deviceName + "…" : action === "connect" ? "Connecting…" : action === "disconnect" ? "Disconnecting…" : "Forgetting device…";
        operation.command = ["python3", Qt.resolvedUrl("../scripts/bluetooth.py").toString().replace("file://", ""), action, device.dbusPath];
        operation.running = true;
    }
    function respond(accept: bool, value: string): void { if (busy) { operation.write(JSON.stringify({accept, value}) + "\n"); prompt = ""; code = ""; } }
    function cancel(): void { if (busy) operation.write(JSON.stringify({cancel: true}) + "\n"); }
    Process {
        id: operation
        stdinEnabled: true
        stdout: SplitParser {
            onRead: line => {
                try {
                    const data = JSON.parse(line);
                    if (data.event === "prompt") { root.prompt = data.kind; root.code = data.code || ""; }
                    else if (data.event === "waiting") { root.prompt = ""; root.code = ""; }
                    else if (data.event === "result") { root.receivedResult = true; root.error = data.ok ? "" : data.error; root.status = data.ok ? "Done" : ""; root.prompt = ""; root.code = ""; }
                } catch (e) { root.error = "Could not read the Bluetooth response"; }
            }
        }
        onExited: { if (!root.receivedResult) root.error = "Bluetooth helper stopped unexpectedly"; root.prompt = ""; root.code = ""; }
    }
}
