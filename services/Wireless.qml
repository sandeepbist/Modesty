pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Networking

Singleton {
    id: root
    readonly property bool preview: Quickshell.env("MODESTY_PREVIEW") === "1"
    readonly property var adapters: Networking.devices.values.filter(d => d.type === DeviceType.Wifi)
    property string adapterName: ""
    readonly property var device: adapters.find(d => d.name === adapterName) ?? adapters[0] ?? null
    readonly property bool available: !!device
    readonly property bool enabled: Networking.wifiEnabled
    readonly property bool hardwareEnabled: Networking.wifiHardwareEnabled
    readonly property var networks: (device?.networks.values ?? []).slice().sort((a, b) => Number(b.connected) - Number(a.connected) || Number(b.known) - Number(a.known) || b.signalStrength - a.signalStrength)
    readonly property string connectedName: networks.find(n => n.connected)?.name ?? ""
    readonly property string connectivity: NetworkConnectivity.toString(Networking.connectivity)
    property var pending: null
    property var passwordNetwork: null
    property string error: ""
    readonly property bool busy: pending !== null
    function needsPsk(network): bool { return [WifiSecurityType.WpaPsk, WifiSecurityType.Wpa2Psk, WifiSecurityType.Sae].includes(network.security); }
    function join(network, password: string): void {
        if (preview) { error = "Preview — network changes are disabled"; return; }
        if (!network || busy) return;
        error = "";
        if (!network.known && needsPsk(network) && !password.length) { passwordNetwork = network; return; }
        if (!network.known && !needsPsk(network) && ![WifiSecurityType.Open, WifiSecurityType.Owe].includes(network.security)) {
            error = "Use Advanced for this network's certificate or enterprise settings."; return;
        }
        pending = network; passwordNetwork = null; timeout.restart();
        if (password.length) network.connectWithPsk(password); else network.connect();
    }
    function cancel(): void { if (preview) return; if (pending) pending.disconnect(); pending = null; passwordNetwork = null; timeout.stop(); }
    function disconnect(network): void { if (!preview && network) network.disconnect(); }
    function forget(network): void { if (!preview && network) network.forget(); }
    function advanced(): void { if (!preview) { Quickshell.execDetached(["nm-connection-editor"]); IslandState.closeMenu(); } }
    Binding { target: root.device; property: "scannerEnabled"; value: IslandState.menu === "wifi"; when: !!root.device && !root.preview; restoreMode: Binding.RestoreBindingOrValue }
    Connections {
        target: root.pending
        function onConnectedChanged() { if (root.pending?.connected) { timeout.stop(); root.pending = null; root.error = ""; } }
        function onConnectionFailed(reason) {
            timeout.stop();
            if (reason === ConnectionFailReason.NoSecrets && root.pending && root.needsPsk(root.pending)) { root.passwordNetwork = root.pending; root.error = "Check the password and try again."; }
            else root.error = "Connection failed: " + ConnectionFailReason.toString(reason);
            root.pending = null;
        }
    }
    Timer { id: timeout; interval: 45000; onTriggered: { root.cancel(); root.error = "Connection timed out. Check the network and try again."; } }
}
