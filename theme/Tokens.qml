import QtQuick
import Quickshell
import qs.services
pragma Singleton

Singleton {
    readonly property string clockFont: Preferences.clockFontFamily==="Inter Variable"?interFont.name:Preferences.clockFontFamily
    readonly property string font: Preferences.fontFamily==="Inter Variable"?interFont.name:Preferences.fontFamily

    readonly property FontLoader
    interFont: FontLoader {
        source: Qt.resolvedUrl("../assets/fonts/InterVariable.ttf")
    }

    readonly property int textRenderType: Preferences.crispText ? Text.CurveRendering : Text.QtRendering
    readonly property int captionSize: 11
    readonly property int labelSize: 13
    readonly property int pillTextSize: 14
    readonly property int pillTextWeight: Font.Medium

    readonly property int readingSize:14
    readonly property real readingLeading:1.42
    readonly property int surfaceRadius:16
    readonly property int fieldRadius:12
    readonly property real titleTracking:-.25
    readonly property real borderAlpha:.08
    readonly property string iconFont: "Material Symbols Rounded"
    readonly property bool reducedMotion: Quickshell.env("MODESTY_REDUCED_MOTION") === "1" || Preferences.motion === "instant"
    readonly property int animFast: reducedMotion ? 0 : Math.round(140 / Preferences.motionSpeed)
    readonly property int animMedium: reducedMotion ? 0 : Math.round(240 / Preferences.motionSpeed)
    readonly property int animSlow: reducedMotion ? 0 : Math.round(380 / Preferences.motionSpeed)
    readonly property int morphDuration: reducedMotion ? 0 : Preferences.motion === "gentle" ? Math.round(380 / Preferences.motionSpeed) : Math.round(300 / Preferences.motionSpeed)
    readonly property int collapseDuration: reducedMotion ? 0 : Preferences.motion === "gentle" ? Math.round(320 / Preferences.motionSpeed) : Math.round(250 / Preferences.motionSpeed)
}
