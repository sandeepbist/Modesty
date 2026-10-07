//@ pragma DefaultEnv QT_QUICK_CONTROLS_STYLE=Basic
//@ pragma DefaultEnv QSG_USE_SIMPLE_ANIMATION_DRIVER=1
//@ pragma Env QT_QPA_PLATFORMTHEME=generic
//@ pragma DefaultEnv QS_NO_RELOAD_POPUP=1
import QtQuick
import Quickshell
import Quickshell.Io
import "modules/settings" as Settings
import "modules/island" as Island
import "modules/wallpaper" as Wallpaper
import "modules/companion" as Companion
import "modules/canvas" as Canvas
import qs.services
ShellRoot {
    LazyLoader { active: IslandState.settingsOpen; Settings.SettingsWindow {} }
    Component.onCompleted: Quickshell.watchFiles = Quickshell.env("MODESTY_PREVIEW") === "1"
    readonly property bool bindingsReady:Bindings.loaded
    readonly property bool voiceReady:Voice.ready
    readonly property bool remindersReady:Reminders.loaded
    readonly property bool authorizationReady: Authorization.registered
    LazyLoader { active: Preferences.companionEnabled && !Preferences.preview; Companion.Companion {} }
    Canvas.CommandCanvas {
        id: commandCanvas
        originItem: island.surface.clockStage.capsule
        originScreenName: island.screen?.name ?? ""
        originAvailable: !island.hiddenByFullscreen && island.surface.visible && island.surface.clockStage.nearRest
    }
    Shortcuts {}
    SessionIntegration {}
    Island.Island {
        id: island
        dropTargetWindow:dropTarget
        screen: Quickshell.screens.find(s => s.name === Quickshell.env("MODESTY_SCREEN")) ?? Quickshell.screens[0]
    }
    Island.IslandDropTarget { id:dropTarget;sourceIsland:island }
    Variants {
        model: Quickshell.screens
        LazyLoader {
            required property ShellScreen modelData
            active: SystemInfo.wallpaperDisplay.length > 0 && Quickshell.env("MODESTY_PREVIEW") !== "1"
            Wallpaper.Wallpaper { screen: modelData }
        }
    }
    IpcHandler {
        target: "island"
        function action(name:string):void {Bindings.trigger(name);}
        function open(panel: string): void { IslandState.openMenu(panel); }
        function toggle(panel: string): void { IslandState.toggle(panel); }
        function close(): void { IslandState.closeMenu(); }
        function hello(): void { if(!Session.isLocked()){CanvasState.close();IslandState.closeMenu();Context.show("welcome","","",0);} }
        function lock(): void { Session.lock(false); }
        function wallpaper(path: string): void { SystemInfo.applyWallpaper(path); }
        function file(path: string): bool { return IslandDrop.accept([path]); }
        function geometry(): string { return JSON.stringify(Object.assign(island.surface.diagnostics(), {fullscreen:island.fullscreen,hiddenByFullscreen:island.hiddenByFullscreen})); }
        function tray(index: int): void { if(Tray.items[index])Tray.show(Tray.items[index]); }
        function status(): string { return IslandState.state; }
        function health(): string { return JSON.stringify({ preview: SystemInfo.preview, compatibility: Quickshell.env("MODESTY_COMPAT") === "1", lockStateSource: "native", locked: Session.isLocked(), secure: Session.secure, authenticationVerified: Session.authenticationVerified, policyAgent: Authorization.registered, wifiAvailable: Wireless.available, bluetoothAvailable: Radio.available, error: SystemInfo.error }); }
    }
    IpcHandler {
        target: "canvas"
        function open(): void { CanvasState.show(); }
        function toggle(): void { CanvasState.toggle(); }
        function close(): void { CanvasState.close(); }
        function search(query: string): void { CanvasState.show(); commandCanvas.search(query); }
        function scope(name: string): void { if(commandCanvas.modes.some(mode => mode.id === name)) commandCanvas.setScope(name); }
        function status(): string { return JSON.stringify(commandCanvas.diagnostics()); }
        function capture(path: string): void { commandCanvas.capture(path); }
    }
}
