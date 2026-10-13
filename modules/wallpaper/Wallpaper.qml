import QtQuick
import "../../services/FileUrls.js" as FileUrls
import Quickshell
import Quickshell.Wayland
import qs.components
import qs.services

PanelWindow {
    id: root

    exclusionMode: ExclusionMode.Ignore
    color: "#121a1b"
    WlrLayershell.namespace: "modesty-wallpaper"
    WlrLayershell.layer: WlrLayer.Background
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

    onWidthChanged: root.updatesEnabled = true
    onHeightChanged: root.updatesEnabled = true
    onScreenChanged: root.updatesEnabled = true
    onDevicePixelRatioChanged: root.updatesEnabled = true
    onVisibleChanged: root.updatesEnabled = true
    onBackingWindowVisibleChanged: root.updatesEnabled = true
    onWindowConnected: root.updatesEnabled = true
    onColorChanged: root.updatesEnabled = true
    onMaskChanged: root.updatesEnabled = true

    anchors {
        top: true
        bottom: true
        left: true
        right: true
    }

    CrossfadeImage {
        id: wallpaper
        anchors.fill: parent
        source: SystemInfo.displayedWallpaper || FileUrls.fromPath(SystemInfo.wallpaper)
        decodeWidth: Math.round(root.screen.width * root.screen.devicePixelRatio)
        decodeHeight: Math.round(root.screen.height * root.screen.devicePixelRatio)
        transitionDuration: Preferences.wallpaperTransition === "none" ? 0 : SystemInfo.previewWallpaperPath ? 130 : Math.round(Preferences.wallpaperDuration * 1000)
        onSourceChanged: root.updatesEnabled = true
        onDecodeWidthChanged: root.updatesEnabled = true
        onDecodeHeightChanged: root.updatesEnabled = true
        onTransitioningChanged: root.updatesEnabled = true
        onFailed: SystemInfo.error = "This wallpaper couldn't be loaded"
    }

    Connections {
        target: wallpaper.Window.window
        function onExposed() { root.updatesEnabled = true; }
        function onAfterAnimating() {
            // Qt completes this accepted frame after afterAnimating, including the polished input mask.
            if (!wallpaper.transitioning) root.updatesEnabled = false;
        }
    }

    mask: Region {
    }

}
