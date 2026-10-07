pragma Singleton
import QtQuick
import Quickshell
Singleton {
    id: root
    property string menu: "none"
    property string previewPanel: ""
    property bool settingsOpen: false
    property string settingsPage: "layout"
    property string hoverStage: "clock"
    property bool pointerInside: false
    property var measuredPanels: ({})
    function measurePanel(name:string, height:real):void {
        if(!Number.isFinite(height)||height<=0)return;
        const value=Math.ceil(height);
        if(measuredPanels[name]!==value)measuredPanels=Object.assign({},measuredPanels,{[name]:value});
    }
    function detailHeight(name:string, maximum:real):real {
        return measuredPanels[name] ? Math.min(maximum,Math.max(250,measuredPanels[name]+Preferences.innerPadding*2+80)) : maximum;
    }
    readonly property bool menuOpen: menu !== "none"
    // Playback never changes the resting shape. Only deliberate interaction reveals media.
    readonly property string state: IslandDrop.dragging ? "dropcue" : previewPanel || (menuOpen ? menu : Context.active ? "context" : Notifications.popups.length ? "toast" : Recorder.active&&!Recorder.selecting ? "recording" : FocusTimer.active ? "focusstatus" : "idle")
    readonly property var sizes: ({ dropcue:[176,Preferences.barHeight],files:[380,IslandDrop.panelHeight],performance:[Preferences.controlsWidth,root.detailHeight("performance",610)],activities:[Activities.width,Preferences.barHeight],focusstatus:[Activities.width,Preferences.barHeight],focus:[Preferences.controlsWidth,root.detailHeight("focus",440)], recording:[Activities.width,Preferences.barHeight],recorder:[Preferences.controlsWidth,root.detailHeight("recorder",360)],unlockcheck: [390, 280], wifi:[Preferences.controlsWidth,root.detailHeight("wifi",480)], bluetooth: [Preferences.controlsWidth, Math.max(310,Math.min(480,226+Radio.devices.length*48))], display:[Preferences.controlsWidth,root.detailHeight("display",510)], sound:[Preferences.controlsWidth,root.detailHeight("sound",490)], authentication: [380, root.measuredPanels.authentication?root.measuredPanels.authentication+Preferences.innerPadding*2:286], context: [Context.width, Preferences.barHeight], idle: [Preferences.collapsedWidth + (Preferences.showSeconds ? 20 : 0), Preferences.barHeight], clock: [216, 96], media: [Preferences.mediaWidth, 186], privacy: [350, Math.max(200, Math.min(350, 135 + Audio.captureStreams.length * 65))], toast: [390, Math.max(128,Math.min(260,Notifications.popupHeight+Preferences.innerPadding*2))], calendar: [Reminders.calendarEditing?Math.max(340,Preferences.calendarWidth):Preferences.calendarWidth,Reminders.calendarExpanded?460:320], quicksettings: [Preferences.controlsWidth, ControlLayout.panelHeight], settings: [900, 650], themes: [570, 210], wallpapers: [730, 186], power: [420, root.measuredPanels.power ?? 94], launcher: [Preferences.launcherWidth, 94+Preferences.launcherVisibleRows*56], notifhistory: [Preferences.controlsWidth, 400] })
    readonly property string owner: ["performance", "quicksettings", "wifi", "bluetooth", "display", "sound", "notifhistory", "recorder", "focus", "recording", "focusstatus"].includes(state) || (state==="context"&&!["workspace","welcome","volume","brightness","luma"].includes(Context.kind)) ? "controls" : state === "media" ? "media" : "clock"
    function hover(stage: string, inside: bool): void {
        if (inside) { hoverStage = stage; pointerInside = true; }
        else if (hoverStage === stage) pointerInside = false;
    }
    function setHovered(inside: bool): void { pointerInside = inside; }
    function resetHover(): void {
        pointerInside = false;
    }
    function openMenu(name: string): void {
        if(name==="calendar"&&menu!=="calendar"){Reminders.calendarExpanded=false;Reminders.calendarEditing=false;}
        if (name === "settings") {
            closeMenu();
            Tray.close();
            // Release the layer's exclusive keyboard focus before mapping Settings.
            Qt.callLater(() => settingsOpen = true);
            return;
        }
        if (sizes[name] && !["idle", "toast", "context"].includes(name)) { previewPanel = ""; menu = name; }
    }
    function closeMenu(): void { previewPanel = ""; menu = "none"; }
    function toggle(name: string): void { if (name === "settings") { if (settingsOpen) settingsOpen = false; else openMenu(name); return; } if (menu === name) dismissCurrent(); else openMenu(name); }
    function dismissCurrent(): void {
        closeMenu();
        if (Notifications.popups.length) Notifications.dismiss(Notifications.popups[0]);
    }
}
