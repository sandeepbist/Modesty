pragma Singleton
import QtQuick
import Quickshell
import qs.theme
import Quickshell.Hyprland
Singleton {
    id: root
    // Keep the last event intact while the capsule closes. Clearing the data
    // changes the outgoing layout halfway through its fade.
    property var event: ({kind:"",label:"",icon:"",value:0,workspaceId:1,direction:0})
    readonly property string kind:event.kind
    readonly property string label:event.label
    readonly property string icon:event.icon
    readonly property real value:event.value
    readonly property int workspaceId:event.workspaceId
    readonly property int direction:event.direction
    property bool active:false
    TextMetrics {id:labelMetrics;font.family:Tokens.clockFont;font.pixelSize:Tokens.pillTextSize;font.weight:Tokens.pillTextWeight;text:root.label}
    readonly property int width:kind==="welcome"?136:kind==="workspace"?Math.min(390,Math.max(Preferences.collapsedWidth+(Preferences.showSeconds?20:0),Math.ceil(labelMetrics.advanceWidth)+32)):["volume","brightness"].includes(kind)?176:Math.min(360,Math.max(180,Math.ceil(labelMetrics.advanceWidth)+66))
    property bool ready: false
    property int previousWorkspace: Hyprland.focusedWorkspace?.id ?? 1
    property var workspaceFocus: ({})
    function rememberFocus(address: string): void {
        const window = Hyprland.toplevels.values.find(t => t.address.replace(/^0x/, "") === address.replace(/^0x/, ""));
        const id = window?.workspace?.id ?? window?.lastIpcObject?.workspace?.id;
        if (id !== undefined) workspaceFocus = Object.assign({}, workspaceFocus, {[id]:window.address});
    }
    function workspaceApp(id: int, name: string): string {
        const windows = Hyprland.toplevels.values.filter(t => {
            const c = t.lastIpcObject;
            return (t.workspace?.id ?? c.workspace?.id) === id && c.mapped !== false && !c.hidden;
        });
        windows.sort((a,b) => {
            if (a.address === workspaceFocus[id]) return -1;
            if (b.address === workspaceFocus[id]) return 1;
            const rank = t => t.lastIpcObject.focusHistoryID >= 0 ? t.lastIpcObject.focusHistoryID : Number.MAX_SAFE_INTEGER;
            return rank(a)-rank(b);
        });
        if (!windows.length) return workspaceLabel(name || String(id));
        const client = windows[0].lastIpcObject;
        const appId = client.class || client.initialClass || "";
        const aliases = {zen:"Zen", "zen-browser":"Zen", "com.t3tools.t3code":"T3 Code", antigravity:"Antigravity", "antigravity-ide":"Antigravity"};
        if (aliases[appId.toLowerCase()]) return aliases[appId.toLowerCase()];
        const entry = DesktopEntries.applications.values.find(a => !a.noDisplay && a.startupClass && a.startupClass.toLowerCase() === appId.toLowerCase()) || DesktopEntries.heuristicLookup(appId);
        if (entry?.name) return entry.name;
        const shortName = appId.split(".").pop();
        return shortName ? shortName.charAt(0).toUpperCase()+shortName.slice(1) : workspaceLabel(name || String(id));
    }
    function show(type: string, text: string, glyph: string, level: real): void {
        if ((type!=="welcome"&&!Preferences.contextEvents) || (type==="volume"&&!Preferences.contextVolume) || (type==="brightness"&&!Preferences.contextBrightness) || (type==="workspace"&&!Preferences.contextWorkspace)) return;
        event={kind:type,label:text,icon:glyph,value:Math.max(0,Number.isFinite(level)?level:0),workspaceId:event.workspaceId,direction:type==="workspace"?event.direction:0};
        active=true;expiry.restart();
    }
    function workspaceLabel(name: string): string {
        const clean=name.replace(/^special:/,"");
        return ({music:"Music",sysmon:"Sysmon",communication:"Chat",discord:"Chat",todo:"Tasks",special:"Scratchpad"})[clean]||(/^\d+$/.test(clean)?clean:clean.charAt(0).toUpperCase()+clean.slice(1));
    }
    function workspace(id: int, name: string): void {
        const direction=id>previousWorkspace?1:id<previousWorkspace?-1:0;
        previousWorkspace=id;
        if(!Preferences.contextEvents||!Preferences.contextWorkspace)return;
        event={kind:"workspace",label:workspaceApp(id,name),icon:"view_carousel",value:0,workspaceId:id,direction};
        active=true;expiry.restart();
    }
    function clear(): void { expiry.stop(); active=false; }
    function volume(): void { if (ready && Audio.sink) show("volume", Audio.muted ? "Muted" : "Volume", Audio.muted ? "volume_off" : "volume_up", Audio.muted ? 0 : Audio.volume); }
    Timer { id: expiry; interval: root.kind==="welcome"?3400:Preferences.contextDuration; onTriggered: root.active=false }
    Timer { interval: 1500; running: true; onTriggered: { root.ready = true; root.previousWorkspace = Hyprland.focusedWorkspace?.id ?? 1; } }
    Connections {
        target: Hyprland
        function onRawEvent(event) {
            if (event.name === "activewindowv2") root.rememberFocus(event.data);
            if (!root.ready) return;
            if (event.name === "workspacev2") {
                const comma = event.data.indexOf(",");
                root.workspace(parseInt(event.data.slice(0, comma)), event.data.slice(comma + 1));
            } else if (event.name === "activespecial") {
                const name = event.data.split(",")[0];
                if (name) {
                    const target = Hyprland.workspaces.values.find(w => w.name === name);
                    root.event=Object.assign({},root.event,{direction:0});
                    root.show("workspace", target ? root.workspaceApp(target.id,name) : root.workspaceLabel(name), "layers", 0);
                }
            }
        }
    }
    Connections { target: Audio; function onVolumeChanged() { root.volume(); } function onMutedChanged() { root.volume(); } }
    Connections { target: SystemInfo; function onBrightnessChanged() { if (root.ready && SystemInfo.brightnessAvailable) root.show("brightness", "Brightness", "light_mode", SystemInfo.brightness); } }
    property string connectedWifi:""
    property var connectedBluetooth:[]
    property real lastBattery:100
    Timer {interval:2500;running:true;onTriggered:{root.connectedWifi=Wireless.connectedName;root.connectedBluetooth=Radio.devices.filter(d=>d.connected).map(d=>({address:d.address,name:d.name}));root.lastBattery=SystemInfo.batteryPercent;}}
    Connections {target:Wireless;function onConnectedNameChanged(){
        const name=Wireless.connectedName;
        if(root.ready&&Preferences.contextDevices&&name!==root.connectedWifi)root.show("connection",name||"Wi-Fi disconnected","wifi",0);
        root.connectedWifi=name;
    }}
    readonly property var bluetoothNow:Radio.devices.filter(d=>d.connected).map(d=>({address:d.address,name:d.name}))
    onBluetoothNowChanged:{
        const current=bluetoothNow;
        if(root.ready&&Preferences.contextDevices){
            const added=current.find(d=>!root.connectedBluetooth.some(old=>old.address===d.address));
            const removed=root.connectedBluetooth.find(d=>!current.some(now=>now.address===d.address));
            if(added)root.show("connection",added.name+" connected","bluetooth",0);
            else if(removed)root.show("connection",removed.name+" disconnected","bluetooth",0);
        }
        root.connectedBluetooth=current;
    }
    Connections {target:SystemInfo;
        function onChargingChanged(){if(root.ready&&Preferences.contextBattery&&SystemInfo.hasBattery)root.show("battery",SystemInfo.charging?"Charging":"On battery",SystemInfo.charging?"battery_charging_full":"battery_full",0);}
        function onBatteryPercentChanged(){const current=SystemInfo.batteryPercent;if(root.ready&&Preferences.contextBattery&&SystemInfo.hasBattery&&!SystemInfo.charging&&[20,10,5].some(level=>root.lastBattery>level&&current<=level))root.show("battery","Battery · "+Math.round(current)+"%","battery_alert",0);root.lastBattery=current;}
    }
    Connections { target: Preferences; function onContextEventsChanged() { if (!Preferences.contextEvents) root.clear(); } function onContextWorkspaceChanged() { if (!Preferences.contextWorkspace && root.kind==="workspace") root.clear(); } }
}
