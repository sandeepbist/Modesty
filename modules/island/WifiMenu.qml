import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Networking
import qs.services
import qs.theme
import qs.components

FocusScope {
    id: root
    objectName: "wifiPanel"
    property var selected: null
    property bool confirmForget: false
    function select(network): void { selected = network; confirmForget = false; password.clear(); Wireless.passwordNetwork = null; Wireless.error = ""; }
    Connections { target: Wireless; function onPasswordNetworkChanged() { if (Wireless.passwordNetwork) { root.selected = Wireless.passwordNetwork; password.forceActiveFocus(); } } }
    ColumnLayout {
        id:body;anchors.fill: parent; spacing: 12
        PanelHeader {
            title:"Wi-Fi"
            Toggle { text:"Wi-Fi";checked:Wireless.enabled;enabled:Wireless.available&&Wireless.hardwareEnabled&&!SystemInfo.busy;onToggled:SystemInfo.action("wifi",String(checked)) }
        }
        PanelText { Layout.fillWidth:true;visible:!Wireless.available||!Wireless.hardwareEnabled;text:!Wireless.available?"No Wi-Fi adapter":"Blocked by the hardware switch";color:Theme.subtext;font.pixelSize:11 }
        RowLayout {
            visible: Wireless.adapters.length > 1; Layout.fillWidth: true
            Repeater { model: Wireless.adapters; ActionButton { required property var modelData; text: modelData.name; primary: Wireless.device === modelData; onClicked: { Wireless.adapterName = modelData.name; root.select(null); } } }
        }
        ListView {
            id: list; Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight:0;implicitHeight:Math.max(112,contentHeight);clip: true; spacing: 8
            model: Wireless.enabled ? Wireless.networks : []
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                id: row; required property var modelData
                width: list.width; height: 54; radius: 12
                color: root.selected === modelData ? Theme.accentLow : mouse.containsMouse ? Theme.withAlpha(Theme.text,.085) : Theme.withAlpha(Theme.text,.035)
                Behavior on color { ColorAnimation {duration:Tokens.animFast} }
                Icon { x: 12; anchors.verticalCenter: parent.verticalCenter; icon: row.modelData.connected ? "wifi" : row.modelData.signalStrength > .5 ? "network_wifi" : "network_wifi_1_bar"; size: 19; color: row.modelData.connected ? Theme.accent : Theme.subtext }
                Column { x: 44; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 80; spacing: 3
                    PanelText { width: parent.width; text: row.modelData.name; font.pixelSize: 13; font.weight: Font.Medium }
                    PanelText { width: parent.width; text: row.modelData.stateChanging ? "Connecting…" : row.modelData.connected ? "Connected" : row.modelData.known ? "Saved" : WifiSecurityType.toString(row.modelData.security); color: Theme.subtext; font.pixelSize: Tokens.captionSize }
                }
                Icon { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; icon: row.modelData.connected ? "check" : "chevron_right"; size: 16; color: Theme.accent }
                MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { root.select(row.modelData); if (!row.modelData.connected && !Wireless.busy) Wireless.join(row.modelData, ""); } }
            }
            PanelText { parent:list;anchors.centerIn: parent; width:Math.max(0,parent.width-28);wrapMode:Text.WordWrap;horizontalAlignment:Text.AlignHCenter;visible: list.count === 0; text: Wireless.enabled ? "Looking for nearby networks…" : "Your saved networks will be here"; color: Theme.subtext; font.pixelSize: 11 }
        }
        ColumnLayout {
            visible: !!root.selected && Wireless.enabled; Layout.fillWidth: true; spacing: 8
            PanelText { Layout.fillWidth: true; text: root.selected?.name ?? ""; font.weight: Font.Medium }
            EntryField { id: password; objectName: "wifiPassword"; Layout.fillWidth: true; visible: !!Wireless.passwordNetwork; echoMode: TextInput.Password; placeholderText: "Network password"; onAccepted: { Wireless.join(root.selected, text); clear(); } }
            RowLayout { Layout.fillWidth: true
                ActionButton { text: Wireless.busy ? "Cancel" : root.selected?.connected ? "Disconnect" : "Connect"; primary: !root.selected?.connected; onClicked: { if (Wireless.busy) Wireless.cancel(); else if (root.selected?.connected) Wireless.disconnect(root.selected); else Wireless.join(root.selected, password.text); password.clear(); } }
                Item { Layout.fillWidth: true }
                ActionButton { visible: !!root.selected?.known; text: root.confirmForget ? "Confirm forget" : "Forget"; enabled: !Wireless.busy; onClicked: { if (root.confirmForget) { Wireless.forget(root.selected); root.select(null); } else root.confirmForget = true; } }
            }
        }
        PanelText { Layout.fillWidth: true; visible: (Wireless.error || SystemInfo.error).length > 0; text: Wireless.error || SystemInfo.error; color: Theme.red; wrapMode: Text.WordWrap; elide: Text.ElideNone; font.pixelSize: Tokens.captionSize }
        RowLayout {
            Layout.fillWidth: true
            PanelText { Layout.fillWidth: true; text: Wireless.connectedName ? Wireless.connectivity === "Portal" ? "Sign-in required by this network" : "" : "Hidden or enterprise network?"; color: Theme.subtext; font.pixelSize: Tokens.captionSize }
            ActionButton { text: "Advanced"; onClicked: Wireless.advanced() }
        }
    }
    implicitHeight:body.implicitHeight
    Component.onDestruction: { password.clear(); Wireless.passwordNetwork = null; }
}
