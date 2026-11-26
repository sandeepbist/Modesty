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
    readonly property bool sessionBlocked: Session.locked || Session.secure
    readonly property bool preparingUnlock: Session.unlocking === true && Preferences.lockScreenStyle === "modern"
    readonly property bool inputAllowed: !sessionBlocked && surface.visible && !captureActive && !hiddenByFullscreen
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
    WlrLayershell.keyboardFocus: IslandState.menuOpen && inputAllowed ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

    anchors {
        top: true
    }
    // Stable backing surface: resizing it during a morph causes Wayland configure/buffer churn.

    // Compositor dismissal also works when a shortcut opens under a stationary pointer.
    HyprlandFocusGrab {
        active: IslandState.menuOpen && root.visible && root.inputAllowed
        windows: root.dropTargetWindow?.visible ? [root,root.dropTargetWindow] : [root]
        onCleared: if (IslandState.menuOpen) IslandState.dismissCurrent()
    }

    IslandSurface {
        id: surface
        monitor:root.monitor

        anchors.horizontalCenter: parent.horizontalCenter
        y: Preferences.topMargin-6*(1-Startup.progress)
        opacity:Startup.progress
        scale: Preferences.uiScale
        transformOrigin: Item.Top
        availableWidth: root.width
        availableHeight: root.height-y
        visible: !!root.screen && (!root.sessionBlocked || root.preparingUnlock) && !root.hiddenByFullscreen
        focus: !root.sessionBlocked
        Keys.onEscapePressed: { Tray.close(); IslandState.dismissCurrent(); }
    }

    mask: Region {
        item: root.inputAllowed ? surface.clockStage.inputRegion : null
        radius: surface.clockStage.capsule.radius
        Region { item: root.inputAllowed && surface.mediaStage.visible && surface.mediaStage.enabled ? surface.mediaStage.inputRegion : null; radius: surface.mediaStage.capsule.radius }
        Region { item: root.inputAllowed && surface.controlStage.visible ? surface.controlStage.inputRegion : null; radius: surface.controlStage.capsule.radius }
        Region { item: root.inputAllowed && surface.trayIcons.visible ? surface.trayIcons : null; radius: Preferences.barHeight / 2 }
        Region { item: root.inputAllowed && Tray.open ? surface.trayMenu : null; radius:18 }
        Region { item: root.inputAllowed ? surface.popupInputRegion : null; radius:12*Preferences.uiScale }
    }

}
