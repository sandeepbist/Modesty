import QtQuick
import Quickshell
import qs.services
pragma Singleton

Singleton {
    readonly property var installedFonts: Qt.fontFamilies()
    readonly property string font: resolveFont(Preferences.fontFamily)
    readonly property string clockFont: Preferences.clockFontFamily === "body" ? font : resolveFont(Preferences.clockFontFamily)
    readonly property var missingFonts: [...new Set([Preferences.fontFamily, Preferences.clockFontFamily]
        .filter(name => name !== "body" && name !== "Inter Variable" && !installedFonts.includes(name)))]

    function resolveFont(name: string): string {
        return name !== "Inter Variable" && installedFonts.includes(name) ? name : interFont.name;
    }

    function textSize(nominal: real): int {
        return Math.round(nominal + (Preferences.bodyFontSize - 9.75) * 4 / 3);
    }

    readonly property FontLoader
    interFont: FontLoader {
        source: Qt.resolvedUrl("../assets/fonts/InterVariable.ttf")
    }

    readonly property int textRenderType: Preferences.crispText ? Text.CurveRendering : Text.QtRendering
    readonly property int captionSize: textSize(11)
    readonly property int labelSize: textSize(13)
    readonly property int pillTextSize: textSize(14)
    readonly property int pillTextWeight: Font.Medium

    readonly property int readingSize:14
    readonly property real readingLeading:1.42
    readonly property int spacingUnit: Preferences.spacingUnit
    readonly property int surfaceRadius: Preferences.surfaceRadius
    readonly property int fieldRadius: Preferences.fieldRadius
    readonly property real titleTracking:-.25
    readonly property real borderAlpha:.08
    readonly property string iconFont: "Material Symbols Rounded"
    readonly property bool reducedMotion: Quickshell.env("MODESTY_REDUCED_MOTION") === "1" || Preferences.motion === "instant"
    readonly property bool modernLockMotion: !reducedMotion && Preferences.lockScreenStyle === "modern"
    readonly property int lockTransitionDuration: reducedMotion ? 0
        : modernLockMotion ? Math.round(Preferences.modernLockDuration / Preferences.motionSpeed) : Preferences.lockDuration
    readonly property int lockReturnLead: modernLockMotion ? Math.round(50 / Preferences.motionSpeed) : 0
    readonly property int lockReboundDuration: modernLockMotion && Preferences.lockRebound ? Math.round(90 / Preferences.motionSpeed) : 0
    readonly property int lockDesktopFade: modernLockMotion ? Math.round(90 / Preferences.motionSpeed) : 0
    readonly property int lockDepartureDuration: lockReturnLead + lockTransitionDuration + lockReboundDuration + lockDesktopFade
    readonly property real panelSpringFrequency: 4.1
    readonly property real panelDepthFrequency: 3.65
    readonly property real panelSpringDamping: Preferences.motion === "gentle" ? .81 : .77
    function smoothStep(progress: real): real {
        const t = Math.max(0, Math.min(1, progress));
        return t * t * (3 - 2 * t);
    }
    function panelExtent(value: real, minimum: real, maximum: real, elastic: bool): real {
        if (value >= minimum) return Math.min(maximum, value);
        const travel = Math.min(6, minimum * .07);
        const compression = minimum - value;
        return Math.min(maximum, elastic ? minimum - travel * compression / (travel + compression) : minimum);
    }
    readonly property int animFast: reducedMotion ? 0 : Math.round(140 / Preferences.motionSpeed)
    readonly property int animMedium: reducedMotion ? 0 : Math.round(240 / Preferences.motionSpeed)
    readonly property int animSlow: reducedMotion ? 0 : Math.round(380 / Preferences.motionSpeed)
    readonly property int morphDuration: reducedMotion ? 0 : Preferences.motion === "gentle" ? Math.round(380 / Preferences.motionSpeed) : Math.round(300 / Preferences.motionSpeed)
    readonly property int collapseDuration: reducedMotion ? 0 : Preferences.motion === "gentle" ? Math.round(320 / Preferences.motionSpeed) : Math.round(250 / Preferences.motionSpeed)
}
