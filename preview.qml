//@ pragma DefaultEnv QT_QUICK_CONTROLS_STYLE=Basic
//@ pragma DefaultEnv QSG_USE_SIMPLE_ANIMATION_DRIVER=1
//@ pragma Env QT_QPA_PLATFORMTHEME=generic
//@ pragma Env MODESTY_PREVIEW=1
import QtQuick
import Quickshell
import Quickshell.Io
import "modules/settings" as Settings
import "modules/island" as Island
import "modules/lock" as Lock
import qs.services
import qs.theme
ShellRoot {
    LazyLoader { active: IslandState.settingsOpen; Settings.SettingsWindow {} }
    FloatingWindow {
        id: window
        title: "Modesty · Preview"
        implicitWidth: 1100; implicitHeight: 760
        color: "#233b3e"
        Item {
            id: scene; anchors.fill: parent
            Rectangle { anchors.fill: parent; gradient: Gradient { GradientStop { position: 0; color: "#305255" } GradientStop { position: 1; color: "#162628" } } }
            Island.IslandSurface { id: surface; anchors.horizontalCenter: parent.horizontalCenter; y: 56 + Preferences.topMargin; scale: Preferences.uiScale; transformOrigin: Item.Top; availableWidth: scene.width; focus: true; Keys.onEscapePressed: IslandState.dismissCurrent() }
            Loader { anchors.fill: parent; active: lockPreview; sourceComponent: Lock.LockContent { preview: true } }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 22; spacing: 5
                Repeater {
                    model: ["idle", "media", "calendar", "quicksettings", "settings", "themes", "wallpapers", "power", "lock"]
                    Rectangle {
                        id: tab; required property string modelData
                        width: 106; height: 30; radius: 15
                        color: (lockPreview ? modelData === "lock" : IslandState.state === modelData) ? Theme.accent : Theme.surfaceSolid
                        Text { anchors.centerIn: parent; text: tab.modelData === "idle" ? "Live hover" : tab.modelData; font.family: Tokens.font; font.pixelSize: 10; color: (lockPreview ? tab.modelData === "lock" : IslandState.state === tab.modelData) ? Theme.bgSolid : Theme.text }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { lockPreview = tab.modelData === "lock"; if (tab.modelData === "idle") IslandState.dismissCurrent(); else if (tab.modelData === "settings") IslandState.openMenu("settings"); else if (!lockPreview) IslandState.previewPanel = tab.modelData; } }
                    }
                }
            }
        }
    }
    property bool lockPreview: false
    IpcHandler {
        target: "preview"
        function reset(): void { IslandState.dismissCurrent(); IslandState.resetHover(); }
        function panel(name: string): void { lockPreview = name === "lock"; if(name === "settings") IslandState.openMenu(name); else if (IslandState.sizes[name]) IslandState.previewPanel = name; }
        function capture(path: string): void { scene.grabToImage(result => result.saveToFile(path)); }
        function geometry(): string { return JSON.stringify(surface.diagnostics()); }
        function notification(): void { Notifications.previewNotify(2000); }
    }
}
