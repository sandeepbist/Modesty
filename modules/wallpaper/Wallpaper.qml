import QtQuick
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

    anchors {
        top: true
        bottom: true
        left: true
        right: true
    }

    CrossfadeImage {
        anchors.fill: parent
        source: SystemInfo.displayedWallpaper || (SystemInfo.wallpaper ? "file://" + SystemInfo.wallpaper : "")
        decodeWidth: Math.round(root.screen.width * root.screen.devicePixelRatio)
        decodeHeight: Math.round(root.screen.height * root.screen.devicePixelRatio)
        transitionDuration: Preferences.wallpaperTransition === "none" ? 0 : SystemInfo.previewWallpaperPath ? 130 : Math.round(Preferences.wallpaperDuration * 1000)
        onFailed: SystemInfo.error = "This wallpaper couldn't be loaded"
    }

    mask: Region {
    }

}
