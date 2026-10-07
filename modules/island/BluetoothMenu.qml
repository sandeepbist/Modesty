import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Bluetooth
import qs.services
import qs.theme
import qs.components

FocusScope {
    id: root
    objectName: "bluetoothPanel"
    property var selected: null
    property bool confirmForget: false
    readonly property var groupedDevices: Radio.devices.filter(d=>Radio.enabled||d.paired||d.connected).map(d=>({device:d,group:d.connected?"Connected":d.paired?"Saved":"Nearby"}))
    Component.onCompleted: if(Radio.enabled)Radio.startScan()
    function deviceIcon(device): string { const icon = device.icon || ""; return icon.includes("head") ? "headphones" : icon.includes("audio") ? "speaker" : icon.includes("mouse") ? "mouse" : icon.includes("keyboard") ? "keyboard" : icon.includes("phone") ? "smartphone" : "bluetooth"; }
    Connections { target: Radio; function onPromptChanged() { pin.clear(); if (["pin", "passkey"].includes(Radio.prompt)) pin.forceActiveFocus(); } }
    ColumnLayout {
        id:body;anchors.fill: parent; spacing: 12
        PanelHeader {
            title:"Bluetooth"
            Toggle { text:"Bluetooth";checked:Radio.enabled;enabled:Radio.available&&!Radio.blocked&&!SystemInfo.busy&&!Radio.busy;onToggled:SystemInfo.action("bluetooth",String(checked)) }
        }
        RowLayout { Layout.fillWidth: true
            PanelText { Layout.fillWidth: true; text: !Radio.enabled ? "Bluetooth is off" : Radio.scanRequested ? "Looking for nearby devices…" : "Your devices"; color: Theme.subtext; font.pixelSize: 11 }
            ActionButton { text: Radio.scanRequested ? "Stop" : "Scan"; implicitHeight:25;implicitWidth:48;padding:4; enabled: Radio.enabled && !Radio.busy; onClicked: Radio.scanRequested ? Radio.stopScan() : Radio.startScan() }
        }
        ListView {
            id: list; Layout.fillWidth: true; Layout.fillHeight: true;Layout.minimumHeight:0;implicitHeight:Math.max(112,contentHeight);clip: true; spacing: 8; model: root.groupedDevices
            section.property:"group";section.criteria:ViewSection.FullString
            section.delegate:PanelText {required property string section; width:list.width;height:26;verticalAlignment:Text.AlignVCenter;text:section;font.pixelSize:11;color:Theme.subtext}
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                id: row; required property var modelData
                readonly property var device:modelData.device
                width: list.width; height: 54; radius: 12
                color: root.selected === row.device ? Theme.accentLow : mouse.containsMouse ? Theme.withAlpha(Theme.text,.085) : Theme.withAlpha(Theme.text,.035)
                Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                Rectangle {x:8;anchors.verticalCenter:parent.verticalCenter;width:27;height:27;radius:13.5;color:row.device.connected?Theme.accent:Theme.withAlpha(Theme.text,.05)
                    Icon {anchors.centerIn:parent;icon:root.deviceIcon(row.device);size:15;color:row.device.connected?Theme.accentText:Theme.subtext}
                }
                Column { x: 43; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 130; spacing: 3
                    PanelText { width: parent.width; text: row.device.name; font.pixelSize: 13; font.weight: Font.Medium }
                    PanelText { width: parent.width; text: row.device.connected ? "Connected" + (row.device.batteryAvailable ? " · " + Math.round(row.device.battery * 100) + "% battery" : "") : row.device.pairing ? "Pairing…" : row.device.paired ? "Saved" : "Available to pair"; color: Theme.subtext; font.pixelSize: 11 }
                }
                MouseArea { id: mouse; anchors.fill: parent;enabled:Radio.enabled; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { root.selected = row.device; root.confirmForget = false; Radio.error = ""; } }
                ActionButton { anchors.right:parent.right;anchors.rightMargin:8;anchors.verticalCenter:parent.verticalCenter;implicitWidth:76;implicitHeight:26;padding:4;text:row.device.connected?"Disconnect":row.device.paired?"Connect":"Pair";enabled:Radio.enabled&&!Radio.busy;onClicked:{root.selected=row.device;Radio.act(row.device,row.device.connected?"disconnect":row.device.paired?"connect":"pair");} }

            }
            PanelText { parent:list;anchors.centerIn: parent; visible: list.count === 0; width: parent.width - 28; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; text: Radio.enabled ? "Put your device in pairing mode to find it here." : "Turn on Bluetooth to connect your devices."; color: Theme.subtext; font.pixelSize: 11 }
        }
        RowLayout {
            visible: !!root.selected && !Radio.busy && Radio.enabled; Layout.fillWidth: true
            ActionButton { primary: !root.selected?.connected; text: root.selected?.connected ? "Disconnect" : root.selected?.paired ? "Connect" : "Pair & connect"; onClicked: Radio.act(root.selected, root.selected.connected ? "disconnect" : root.selected.paired ? "connect" : "pair") }
            Item { Layout.fillWidth: true }
            ActionButton { visible: !!root.selected?.paired; text: root.confirmForget ? "Confirm forget" : "Forget"; onClicked: { if (root.confirmForget) { Radio.act(root.selected, "forget"); root.selected = null; } else root.confirmForget = true; } }
        }
        ColumnLayout {
            Layout.fillWidth: true; visible: Radio.busy; spacing: 8
            PanelText { Layout.fillWidth: true; text: Radio.status; font.pixelSize: 11; font.weight: Font.Medium }
            PanelText { Layout.fillWidth: true; visible: Radio.prompt.length > 0; text: Radio.prompt === "confirm" ? "Does this code match on " + Radio.deviceName + "?" : Radio.prompt === "display" ? "Type this code on your device, then press Enter." : Radio.prompt === "authorize" ? "Allow this device to pair?" : "Enter the code shown on your device."; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.subtext; font.pixelSize: 11 }
            PanelText { Layout.alignment: Qt.AlignHCenter; visible: Radio.code.length > 0; text: Radio.code; font.pixelSize: 28; font.weight: Font.DemiBold; font.letterSpacing: 4 }
            EntryField { id: pin; objectName: "bluetoothPin"; Layout.fillWidth: true; visible: ["pin", "passkey"].includes(Radio.prompt); placeholderText: "Pairing code"; maximumLength: Radio.prompt === "passkey" ? 6 : 16; inputMethodHints: Radio.prompt === "passkey" ? Qt.ImhDigitsOnly : Qt.ImhNone; onAccepted: { Radio.respond(true, text); clear(); } }
            RowLayout {
                ActionButton { text: "Cancel"; onClicked: Radio.cancel() }
                Item { Layout.fillWidth: true }
                ActionButton { visible: Radio.prompt.length > 0 && Radio.prompt !== "display"; primary: true; text: Radio.prompt === "confirm" ? "Matches" : "Pair"; onClicked: { Radio.respond(true, pin.text); pin.clear(); } }
            }
        }
        PanelText { Layout.fillWidth: true; visible: (Radio.error || SystemInfo.error).length > 0; text: Radio.error || SystemInfo.error; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.red; font.pixelSize: 11 }
    }
    implicitHeight:body.implicitHeight
    Component.onDestruction: pin.clear()
}
