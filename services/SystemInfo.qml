pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.UPower
import qs.theme
Singleton {
    id: root
    readonly property bool preview: Quickshell.env("MODESTY_PREVIEW") === "1"

    readonly property bool wifiEnabled: Wireless.enabled

    property string backlightPath: ""
    property real maxBrightness: 1
    property real brightness: 0
    property bool brightnessAvailable: false
    property string wallpaper: ""
    property string wallpaperDisplay: ""
    property string previewWallpaperDisplay: ""
    readonly property string displayedWallpaper: previewWallpaperDisplay || wallpaperDisplay
    property string previewWallpaperPath: ""
    property string previewPaletteKey: ""
    property var previewPaletteCache: ({})
    property var pendingPreviewPalette: null
    function storePalette(result: var): void {
        const next = Object.assign({}, previewPaletteCache);
        delete next[result.key];
        next[result.key] = {palette: result.palette, raw: result.raw};
        const keys = Object.keys(next);
        if (keys.length > 32) delete next[keys[0]];
        previewPaletteCache = next;
    }
    property string lockWallpaper: ""
    property bool lockDesktopVisible:false
    property string wallpaperBackend: ""
    property bool matugenAvailable: false
    property string wallpaperWarning: ""
    property var wallpapers: []
    property string error: ""
    readonly property bool busy: actionProc.running
    readonly property bool hasBattery: UPower.displayDevice.isLaptopBattery
    readonly property real batteryPercent: hasBattery ? UPower.displayDevice.percentage * 100 : 0
    readonly property bool charging: hasBattery && !UPower.onBattery
    readonly property string script: Qt.resolvedUrl("../scripts/system.py").toString().replace("file://", "")
    property var queue: []
    function refresh(): void { if (!snapshotProc.running) snapshotProc.running = true; }
    function applyWallpaper(path: string): void {
        const selected = wallpapers.find(w => w.path === path);
        if (!selected || preview) return;
        paletteKey = ""; pendingPalette = null;
        wallpaperDisplay = selected.displayUrl || selected.url;
        wallpaperBackend = "native";
        wallpaper = path;
        clearWallpaperPreview();
        if(Preferences.wallpaperColors)Theme.setPalette("wallpaper");
        recolor();
        action("wallpaper", JSON.stringify({path}));
    }
    function paletteRequest(path: string): var {
        const image = wallpapers.find(w => w.path === path);
        return {path, revision:image?.displayUrl || "", automatic:Preferences.matugenAutomatic, scheme:Preferences.matugenScheme, contrast:Preferences.matugenContrast, source:Preferences.matugenSource};
    }
    function previewWallpaper(path: string): void {
        const selected = wallpapers.find(w => w.path === path);
        if (!selected) return;
        previewWallpaperPath = path;
        previewWallpaperDisplay = selected.displayUrl || selected.url;
        if (!Preferences.wallpaperColors || !matugenAvailable) {
            previewPaletteKey = ""; pendingPreviewPalette = null; previewDelay.stop(); Theme.clearWallpaperPreview();
            return;
        }
        const request = paletteRequest(path);
        previewPaletteKey = JSON.stringify(request);
        const cached = previewPaletteCache[previewPaletteKey];
        if (cached) { pendingPreviewPalette = null; previewDelay.stop(); Theme.showWallpaperPreview(cached.palette); return; }
        request.key = previewPaletteKey;
        pendingPreviewPalette = request;
        previewDelay.restart();
    }
    function clearWallpaperPreview(): void {
        previewWallpaperPath = ""; previewWallpaperDisplay = ""; previewPaletteKey = "";
        pendingPreviewPalette = null; previewDelay.stop(); Theme.clearWallpaperPreview();
    }
    onWallpaperChanged:Qt.callLater(recolor)
    property string paletteKey:""
    property var pendingPalette:null
    function recolor():void {
        if(preview||!wallpaper||!Preferences.wallpaperColors||!matugenAvailable)return;
        const request = paletteRequest(wallpaper);
        const key = JSON.stringify(request);
        if (paletteKey === key && (pendingPalette || paletteProc.running)) return;
        paletteKey = key;
        const cached = previewPaletteCache[paletteKey];
        if (cached) {
            pendingPalette = null; paletteDelay.stop();
            if (Theme.wallpaperData !== cached.raw) Theme.installWallpaperData(cached.palette, cached.raw);
            return;
        }
        request.key=paletteKey;pendingPalette=request;paletteDelay.restart();
    }
    Timer {id:paletteDelay;interval:80;onTriggered:{if(!root.pendingPalette||paletteProc.running)return;paletteProc.command=["python3",root.script,"palette",JSON.stringify(root.pendingPalette)];root.pendingPalette=null;paletteProc.running=true;}}
    Process {id:paletteProc;stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);if(d.ok)root.storePalette(d);if(d.key===root.paletteKey&&d.path===root.wallpaper&&Preferences.wallpaperColors){if(d.ok){Theme.installWallpaperData(d.palette,d.raw);root.wallpaperWarning="";}else root.wallpaperWarning=d.error||"Couldn't generate wallpaper colors";}}catch(e){root.wallpaperWarning="Couldn't read wallpaper colors";}}} onExited:if(root.pendingPalette)paletteDelay.restart()}
    Timer {id:previewDelay;interval:80;onTriggered:{if(!root.pendingPreviewPalette)return;if(previewProc.running)return;previewProc.command=["python3",root.script,"palette",JSON.stringify(root.pendingPreviewPalette)];root.pendingPreviewPalette=null;previewProc.running=true;}}
    Process {id:previewProc;stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);if(!d.ok)return;root.storePalette(d);if(d.key===root.previewPaletteKey&&d.path===root.previewWallpaperPath&&Preferences.wallpaperColors)Theme.showWallpaperPreview(d.palette);}catch(e){}}} onExited:if(root.pendingPreviewPalette)previewDelay.restart()}
    Connections {target:Preferences;function onMatugenAutomaticChanged(){root.recolor();if(root.previewWallpaperPath)root.previewWallpaper(root.previewWallpaperPath);}function onMatugenSchemeChanged(){root.recolor();if(root.previewWallpaperPath)root.previewWallpaper(root.previewWallpaperPath);}function onMatugenContrastChanged(){root.recolor();if(root.previewWallpaperPath)root.previewWallpaper(root.previewWallpaperPath);}function onMatugenSourceChanged(){root.recolor();if(root.previewWallpaperPath)root.previewWallpaper(root.previewWallpaperPath);}function onWallpaperColorsChanged(){if(Preferences.wallpaperColors){Theme.setPalette("wallpaper");root.recolor();if(root.previewWallpaperPath)root.previewWallpaper(root.previewWallpaperPath);}else{root.previewPaletteKey="";root.pendingPreviewPalette=null;previewDelay.stop();Theme.clearWallpaperPreview();}}}
    function scanWallpapers(): void {
        if (wallProc.running) return;
        wallProc.command = ["python3", script, "wallpapers", JSON.stringify({automatic:Preferences.matugenAutomatic,scheme:Preferences.matugenScheme,contrast:Preferences.matugenContrast,source:Preferences.matugenSource})];
        wallProc.running = true;
    }
    function action(name: string, value: string): void {
        if (preview) { error = "Preview — system controls are disabled"; return; }
        queue = queue.filter(a => a[0] !== name).concat([[name, value]]);
        nextAction();
    }
    function nextAction(): void {
        if (actionProc.running || !queue.length) return;
        const next = queue[0]; queue = queue.slice(1);
        error = "";
        actionProc.command = ["python3", script, next[0], next[1]];
        actionProc.running = true;
    }
    property real pendingBrightness: brightness
    property bool brightnessDirty: false
    property bool brightnessInFlight: false
    property int brightnessSequence: 0
    onBrightnessChanged: if (!brightnessProc.running) pendingBrightness = brightness
    FileView {
        id: brightnessFile
        path: root.backlightPath ? root.backlightPath + "/brightness" : ""
        printErrors: false
        onLoaded: {
            const value = Number(text().trim());
            if (Number.isFinite(value) && root.maxBrightness > 0 && !root.brightnessDirty && !root.brightnessInFlight) root.brightness = value / root.maxBrightness;
        }
    }
    // Sysfs read only: no subprocess, no D-Bus roundtrip. Covers external laptop Fn keys.
    Timer { interval: 250; repeat: true; running: root.backlightPath.length > 0; onTriggered: brightnessFile.reload() }
    Connections { target: IslandState; function onMenuChanged() { if (IslandState.menu === "quicksettings") root.refresh(); } }
    function setBrightness(value: real): void {
        if (preview || !brightnessAvailable || !Number.isFinite(value)) return;
        pendingBrightness = Math.max(0.01, Math.min(1, value));
        brightness = pendingBrightness;
        brightnessDirty = true;
        brightnessIdle.restart();
        if (!brightnessProc.running) { error = ""; brightnessProc.running = true; }
        else if (!brightnessTimer.running) brightnessTimer.start();
    }
    function flushBrightness(): void {
        if (!brightnessProc.running || brightnessInFlight || !brightnessDirty) return;
        brightnessDirty = false;
        brightnessInFlight = true;
        brightnessProc.write(JSON.stringify({sequence: ++brightnessSequence, value: Math.round(pendingBrightness * maxBrightness)}) + "\n");
    }
    // A throttle, not a debounce: hardware updates continue throughout a drag.
    Timer { id: brightnessTimer; interval: 33; onTriggered: root.flushBrightness() }
    Timer { id: brightnessIdle; interval: 500; onTriggered: {
        if (root.brightnessDirty || root.brightnessInFlight) restart();
        else brightnessProc.running = false;
    } }
    Process {
        id: brightnessProc
        command: ["python3", Qt.resolvedUrl("../scripts/brightness-stream.py").toString().replace("file://", ""), root.backlightPath.split("/").pop()]
        stdinEnabled: true
        onStarted: root.flushBrightness()
        stdout: SplitParser { onRead: data => {
            try {
                const result = JSON.parse(data);
                root.brightnessInFlight = false;
                if (!result.ok) { root.error = result.error || "Couldn't change brightness"; root.brightnessDirty = false; }
                else if (root.brightnessDirty && !brightnessTimer.running) brightnessTimer.start();
            } catch (e) { root.error = "Couldn't read the brightness response"; root.brightnessInFlight = false; }
        } }
        onExited: {
            root.brightnessInFlight = false;
            root.brightnessDirty = false;
            brightnessTimer.stop();
            brightnessFile.reload();
        }
    }
    Process {
        id: snapshotProc
        command: ["python3", root.script, "snapshot"]
        stdout: StdioCollector {
            onStreamFinished: {
                try { const data = JSON.parse(text); for (const k of Object.keys(data)) if (k in root && !(k === "brightness" && brightnessProc.running)) root[k] = data[k]; }
                catch (e) { console.warn("System snapshot:", e); }
            }
        }
    }
    Process {
        id: wallProc
        stdout: StdioCollector { onStreamFinished: { try {
            const next = JSON.parse(text);
            if (next.length !== root.wallpapers.length || next.some((wall, index) => wall.path !== root.wallpapers[index].path || wall.thumbnailUrl !== root.wallpapers[index].thumbnailUrl || wall.displayUrl !== root.wallpapers[index].displayUrl)) root.wallpapers = next;
            const options = JSON.parse(wallProc.command[3]);
            for (const wall of next) {
                if (!wall.paletteData) continue;
                const key = JSON.stringify({path:wall.path,revision:wall.displayUrl || "",automatic:options.automatic,scheme:options.scheme,contrast:options.contrast,source:options.source});
                root.storePalette({key, palette:wall.palette, raw:wall.paletteData});
            }
            const cached = root.previewPaletteCache[root.previewPaletteKey];
            if (cached) { root.pendingPreviewPalette = null; previewDelay.stop(); Theme.showWallpaperPreview(cached.palette); }
        } catch (e) { root.wallpapers = []; } } }
    }
    Process {
        id: actionProc
        stdout: StdioCollector { onStreamFinished: { try { const data = JSON.parse(text); if (!data.ok) root.error = data.error;
                    else if (data.wallpaper) {
                        root.wallpaperDisplay = data.wallpaperDisplay;
                        root.wallpaperBackend = data.wallpaperBackend;
                        root.wallpaper = data.wallpaper;
                        root.wallpaperWarning = data.warning || "";
                        root.recolor();
                    } } catch (e) { root.error = "The command did not complete"; } } }
        onExited: { root.refresh(); Qt.callLater(root.nextAction); }
    }
    Timer { interval: 15000; repeat: true; running: !root.preview && IslandState.menu === "quicksettings"; triggeredOnStart: true; onTriggered: root.refresh() }
    Component.onCompleted: { refresh(); scanWallpapers(); }
}
