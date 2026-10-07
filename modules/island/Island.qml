import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.services

PanelWindow {
    id: root

    readonly property alias surface: surface
    property var dropTargetWindow:null

    readonly property var monitor: Hyprland.monitorFor(screen)
    readonly property bool fullscreen: (monitor?.activeWorkspace?.toplevels.values ?? []).some(t => (t.lastIpcObject.fullscreen ?? 0) === 2)
    // The editor already contains a frozen screenshot of the island. Let its
    // full-screen canvas receive input, including the space under our pills.
    readonly property bool captureActive: Recorder.selecting || Hyprland.toplevels.values.some(t => {
        const c = t.lastIpcObject;
        return /^(flameshot|org\.flameshot\.Flameshot)$/i.test(c.class || "")
            && /^flameshot$/i.test(c.title || "") && c.mapped !== false;
    })
    readonly property bool hiddenByFullscreen: captureActive || (fullscreen && !IslandState.menuOpen && !Tray.open)
    Timer {id:fullscreenRefresh;interval:50;onTriggered:Hyprland.refreshToplevels()}
    Connections {target:Hyprland;function onRawEvent(event){if(["fullscreen","activewindowv2","workspacev2","movewindowv2","closewindow","openwindow","windowtitlev2"].includes(event.name))fullscreenRefresh.restart();}}
    Component.onCompleted: Hyprland.refreshToplevels()

    // The rounded input region still follows the visible capsule every frame.
    implicitWidth: screen?.width ?? 1920
    implicitHeight: screen?.height ?? 1080
    // Reserve the resting pill plus the user's optional extra window gap.
    // Opening a panel must never reflow the user's tiled windows.
    exclusiveZone: Math.max(0,Math.ceil(Preferences.topMargin + Preferences.barHeight * Preferences.uiScale + Preferences.windowGap))
    color: "transparent"
    WlrLayershell.namespace: "modesty-island"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: IslandState.menuOpen && !captureActive ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

    anchors {
        top: true
    }
    // Stable backing surface: resizing it during a morph causes Wayland configure/buffer churn.

    // Compositor dismissal also works when a shortcut opens under a stationary pointer.
    HyprlandFocusGrab {
        active: IslandState.menuOpen && root.visible && !root.captureActive
        windows: root.dropTargetWindow?.visible ? [root,root.dropTargetWindow] : [root]
        onCleared: if (IslandState.menuOpen) IslandState.dismissCurrent()
    }

    IslandSurface {
        id: surface

        anchors.horizontalCenter: parent.horizontalCenter
        y: Preferences.topMargin-6*(1-Startup.progress)
        opacity:Startup.progress
        scale: Preferences.uiScale
        transformOrigin: Item.Top
        availableWidth: root.width
        visible: !root.hiddenByFullscreen
        focus: true
        Keys.onEscapePressed: { Tray.close(); IslandState.dismissCurrent(); }
    }

    mask: Region {
        item: root.captureActive || root.hiddenByFullscreen ? null : surface.clockStage.inputRegion
        radius: surface.clockStage.capsule.radius
        Region { item: root.hiddenByFullscreen || !surface.mediaStage.visible || !surface.mediaStage.enabled ? null : surface.mediaStage.inputRegion; radius: surface.mediaStage.capsule.radius }
        Region { item: root.hiddenByFullscreen || !surface.controlStage.visible ? null : surface.controlStage.inputRegion; radius: surface.controlStage.capsule.radius }
        Region { item: root.hiddenByFullscreen || !surface.trayIcons.visible ? null : surface.trayIcons; radius: Preferences.barHeight / 2 }
        Region { item: Tray.open && !root.hiddenByFullscreen ? surface.trayMenu : null; radius:18 }
    }

}
