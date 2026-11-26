pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import qs.services
import "Palette.js" as Palette

Singleton {
    id: root

    property string paletteName: "everblush"
    property string mode: "dark"
    readonly property bool light: mode === "light"
    property string syncError: ""
    property bool appearanceReady: Preferences.preview
    property string appearanceLoadError: ""
    property var customThemes: []
    readonly property bool customThemeActive: customThemes.some(theme => theme.id === paletteName)
    property var wallpaperVariants: ({})
    property var wallpaperData:null
    property var previewWallpaperVariants:null
    property bool previewSyncPending:false
    property bool restoringPreview:false
    readonly property int paletteMotion: Tokens.reducedMotion ? 0 : (previewWallpaperVariants || restoringPreview ? 120 : 320)
    function installWallpaperData(palette,data):void {wallpaperData=data;loadWallpaperPalette(palette);scheduleSync();}
    function showWallpaperPreview(palette):void {
        if (paletteName !== "wallpaper" || !validPalette(palette.dark) || !validPalette(palette.light)) return;
        const before = previewWallpaperVariants;
        if (before) {
            const sameColors = (a, b) => {
                const keys = Object.keys(b);
                return Object.keys(a).length === keys.length
                    && keys.every(key => Object.prototype.hasOwnProperty.call(a, key) && a[key] === b[key]);
            };
            const keys = Object.keys(palette);
            if (Object.keys(before).length === keys.length
                && keys.every(key => Object.prototype.hasOwnProperty.call(before, key)
                    && (key === "dark" || key === "light" || before[key] === palette[key]))
                && sameColors(before.dark, palette.dark) && sameColors(before.light, palette.light)) return;
        }
        previewWallpaperVariants = palette;
    }
    function clearWallpaperPreview():void {
        if (!previewWallpaperVariants) return;
        restoringPreview = true;
        previewWallpaperVariants = null;
        if (previewSyncPending) { previewSyncPending = false; scheduleSync(); }
        Qt.callLater(() => restoringPreview = false);
    }
    readonly property var pal: previewWallpaperVariants?.[mode] ? Palette.refine(previewWallpaperVariants[mode]) : resolvePalette(paletteName)
    function resolvePalette(name): var {
        const saved = customThemes.find(theme => theme.id === name);
        if (saved?.variants) return Palette.refine(saved.variants[mode]);
        if (saved) name = saved.source;
        const base = palettes[name] ?? palettes.everblush;
        if (name === "wallpaper" && wallpaperVariants[mode]) return Palette.refine(wallpaperVariants[mode]);
        if (!light || name === "e-ink") return Palette.refine(base);
        return Palette.lightPalette(name) || Palette.refine(base);
    }
    function paletteLabel(name): string {
        if (name === "wallpaper") return "Wallpaper colors";
        if (name === "e-ink") return "E-Ink";
        return name.charAt(0).toUpperCase() + name.slice(1);
    }
    function snapshotSource(source): bool {
        return source === "wallpaper" || Palette.schemeOptions.some(option => option.value === source);
    }
    function validVariants(variants): bool {
        return !!variants && validPalette(variants.dark) && validPalette(variants.light);
    }
    function validThemeSource(source, variants): bool {
        return snapshotSource(source) ? validVariants(variants)
            : Object.prototype.hasOwnProperty.call(palettes, source) && !variants;
    }
    function themeNameError(id: string, name: string): string {
        const label = name.trim().toLowerCase();
        if (!label) return "Enter a theme name.";
        if (label === "wallpaper colors" || customThemes.some(theme => theme.id !== id && theme.label.toLowerCase() === label))
            return "That theme name is already in use.";
        return "";
    }
    function saveCustomTheme(id: string, name: string, source: string, variants): string {
        if (!appearanceReady) return appearanceLoadError || "Appearance is still loading.";
        const error = themeNameError(id, name);
        if (error) return error;
        if (!validThemeSource(source, variants)) return "Choose a valid palette.";
        if (id && !customThemes.some(theme => theme.id === id)) return "This theme was deleted.";
        if (!id) {
            let stamp = Date.now();
            while (customThemes.some(theme => theme.id === "custom-" + stamp)) stamp++;
            id = "custom-" + stamp;
        }
        const entry = {id, label: name.trim(), source, variants: variants || null};
        const index = customThemes.findIndex(theme => theme.id === id);
        const next = customThemes.slice();
        if (index < 0) next.push(entry);
        else next[index] = entry;
        customThemes = next;
        scheduleSync();
        return "";
    }
    function deleteCustomTheme(id: string): void {
        if (!appearanceReady) return;
        const next = customThemes.filter(theme => theme.id !== id);
        if (next.length === customThemes.length) return;
        if (paletteName === id) useWallpaperColors();
        customThemes = next;
        scheduleSync();
    }
    function useWallpaperColors(): void {
        if (!Preferences.wallpaperColors) Preferences.set("wallpaperColors", true);
        setPalette("wallpaper");
    }
    function setMode(value: string): void {
        if (!["dark", "light"].includes(value) || mode === value) return;
        mode = value;
        scheduleSync();
    }
    function toggleMode(): void { setMode(light ? "dark" : "light"); }
    property color accentText: pal.accentText ?? pal.bgSolid
    Behavior on accentText { ColorAnimation { duration: root.paletteMotion } }
    property color secondary: pal.secondary ?? pal.accent
    Behavior on secondary { ColorAnimation { duration: root.paletteMotion } }
    property color tertiary: pal.tertiary ?? pal.accent
    Behavior on tertiary { ColorAnimation { duration: root.paletteMotion } }
    readonly property color wallpaperText: wallpaperVariants.dark?.text ?? palettes.everblush.text
    readonly property color wallpaperScrim: wallpaperVariants.dark?.bgSolid ?? palettes.everblush.bgSolid
    property color accent: pal.accent
    Behavior on accent { ColorAnimation { duration: root.paletteMotion } }
    property var wallpaperPalette: ({bg: "#101516", bgSolid: "#101516", surface: "#202728", surfaceSolid: "#202728", text: "#e4eaeb", subtext: "#bdc8ca", accent: "#83cdd8", green: "#b3c5e9", yellow: "#b3cbd0", red: "#ffb4ab"})

    // ---- Palettes ----
    readonly property var palettes: {
        "wallpaper": root.wallpaperPalette,
        "everblush": {
            bg: "#080b0b", bgSolid: "#080b0b", surface: "#191e1f", surfaceSolid: "#191e1f",
            text: "#edf0ef", subtext: "#99a3a1", accent: "#67b7b5", green: "#8ccf7e", yellow: "#e5c76b", red: "#e57474"
        },
        "e-ink": {
            bg: "#e0e2e0", bgSolid: "#e0e2e0", surface: "#c7cbc8", surfaceSolid: "#c7cbc8",
            text: "#202624", subtext: "#626a66", accent: "#54675f", green: "#78877d", yellow: "#9a9680", red: "#8d7777"
        },
        "midnight": {
            bg: "#a1101013", bgSolid: "#101013", surface: "#b318181c", surfaceSolid: "#18181c",
            text: "#f2f2f4", subtext: "#b8b8c0",
            accent: "#89b4fa", green: "#a6e3a1", yellow: "#f9e2af", red: "#f38ba8"
        },
        "nord": {
            bg: "#a12e3440", bgSolid: "#2e3440", surface: "#b33b4252", surfaceSolid: "#3b4252",
            text: "#eceff4", subtext: "#d8dee9",
            accent: "#88c0d0", green: "#a3be8c", yellow: "#ebcb8b", red: "#bf616a"
        },
        "everforest": {
            bg: "#a12d353c", bgSolid: "#2d353c", surface: "#b3343f45", surfaceSolid: "#343f45",
            text: "#d3c6aa", subtext: "#9da9a0",
            accent: "#a7c080", green: "#a7c080", yellow: "#dbbc7f", red: "#e67e80"
        },
        "gruvbox": {
            bg: "#a1282828", bgSolid: "#282828", surface: "#b1323232", surfaceSolid: "#323232",
            text: "#ebdbb2", subtext: "#bdae93",
            accent: "#fabd2f", green: "#b8bb26", yellow: "#fabd2f", red: "#fb4934"
        },
        "rose": {
            bg: "#a11c1b21", bgSolid: "#1c1b21", surface: "#b3262430", surfaceSolid: "#262430",
            text: "#e0def4", subtext: "#908caa",
            accent: "#ebbcba", green: "#9ccfd8", yellow: "#f6c177", red: "#eb6f92"
        },
        "dracula": {
            bg: "#a1282a36", bgSolid: "#282a36", surface: "#b1343549", surfaceSolid: "#343549",
            text: "#f8f8f2", subtext: "#bfbfbf",
            accent: "#bd93f9", green: "#50fa7b", yellow: "#f1fa8c", red: "#ff5555"
        }
    }

    // ---- Resolved colors ----
    property color bg: pal.bg
    Behavior on bg { ColorAnimation { duration: root.paletteMotion } }
    property color bgSolid: pal.bgSolid
    Behavior on bgSolid { ColorAnimation { duration: root.paletteMotion } }
    property color surface: pal.surface
    Behavior on surface { ColorAnimation { duration: root.paletteMotion } }
    property color surfaceSolid: pal.surfaceSolid
    Behavior on surfaceSolid { ColorAnimation { duration: root.paletteMotion } }
    property color text: pal.text
    Behavior on text { ColorAnimation { duration: root.paletteMotion } }
    property color subtext: pal.subtext
    Behavior on subtext { ColorAnimation { duration: root.paletteMotion } }
    property color green: pal.green
    Behavior on green { ColorAnimation { duration: root.paletteMotion } }
    property color yellow: pal.yellow
    Behavior on yellow { ColorAnimation { duration: root.paletteMotion } }
    property color red: pal.red
    Behavior on red { ColorAnimation { duration: root.paletteMotion } }

    // accent at low alpha (chips, hover fills, progress tracks)
    property color accentLow: Qt.rgba(accent.r, accent.g, accent.b, 0.18)


    function withAlpha(c: color, a: real): color {
        return Qt.rgba(c.r, c.g, c.b, a);
    }

    readonly property string stateDir: (Quickshell.env("XDG_STATE_HOME") || (Quickshell.env("HOME") + "/.local/state")) + "/modesty"
    function validPalette(p): bool {
        return p && ["bg", "bgSolid", "surface", "surfaceSolid", "text", "subtext", "accent", "green", "yellow", "red"].every(k => /^#[0-9a-fA-F]{6}$/.test(p[k] || "")) && ["accentText","secondary","tertiary"].every(k=>p[k]===undefined||/^#[0-9a-fA-F]{6}$/.test(p[k]));
    }
    function loadWallpaperPalette(data): bool {
        if (validPalette(data.dark) && validPalette(data.light)) {
            wallpaperVariants = data;
            wallpaperPalette = data.dark;
            return true;
        }
        if (validPalette(data)) { wallpaperPalette = data; return true; }
        return false;
    }
    function scheduleSync(): void {
        if (!appearanceReady) return;
        if (previewWallpaperVariants) { previewSyncPending = true; return; }
        if (!Preferences.preview) syncDelay.restart();
    }
    Timer { id: syncDelay; interval: 150; onTriggered: {
        if (root.previewWallpaperVariants) { root.previewSyncPending = true; return; }
        if (syncProc.running) { restart(); return; }
        syncProc.payload = JSON.stringify({
            paletteName: root.paletteName, mode: root.mode, customThemes: root.customThemes,
            wallpaperData: root.wallpaperData, wallpaperVariants: root.wallpaperVariants,
            targets: {gtk: Preferences.themeGtk, folders: Preferences.themeFolders, qt: Preferences.themeQt,
                foot: Preferences.themeFoot, spotify: Preferences.themeSpotify},
            colors: {accent: String(root.pal.accent), accentText: String(root.pal.accentText ?? root.pal.bgSolid),
                subtext: String(root.pal.subtext), bg: String(root.pal.bgSolid), surface: String(root.pal.surfaceSolid),
                text: String(root.pal.text), green: String(root.pal.green), yellow: String(root.pal.yellow), red: String(root.pal.red)}
        });
        syncProc.running = true;
    } }
    Process {
        id: syncProc
        property string payload
        command: ["python3", Qt.resolvedUrl("../scripts/appearance.py").toString().replace("file://", ""), "--stdin"]
        stdinEnabled: true
        onStarted: { write(payload + "\n"); payload = ""; }
        stdout: StdioCollector { onStreamFinished: {
            try { root.syncError = JSON.parse(text).error || ""; }
            catch (e) { root.syncError = "Couldn't save appearance or synchronize desktop colors."; }
        } }
    }
    Connections {target:Preferences;function onThemeGtkChanged(){root.scheduleSync();}function onThemeFoldersChanged(){root.scheduleSync();}function onThemeQtChanged(){root.scheduleSync();}function onThemeFootChanged(){root.scheduleSync();}function onThemeSpotifyChanged(){root.scheduleSync();}}
    FileView {path:Quickshell.env("MODESTY_PREVIEW")==="1"?"":root.stateDir+"/wallpaper-data.json";printErrors:false;onLoaded:{try{root.wallpaperData=JSON.parse(text());root.scheduleSync();}catch(e){}}}
    onPalChanged: if (!previewWallpaperVariants && !restoringPreview) scheduleSync()
    Connections { target:Hyprland; function onRawEvent(event) { if(event.name === "configreloaded") root.scheduleSync(); } }
    FileView {
        path: Quickshell.env("MODESTY_PREVIEW") === "1" ? "" : root.stateDir + "/wallpaper-palette.json"
        printErrors: false
        onLoaded: { try { root.loadWallpaperPalette(JSON.parse(text())); } catch (e) {} }
    }
    function setPalette(name: string): void {
        if (!Object.prototype.hasOwnProperty.call(palettes, name) && !customThemes.some(theme => theme.id === name)) return;
        if(name!=="wallpaper")clearWallpaperPreview();
        paletteName = name;
        scheduleSync();
    }
    FileView {
        path: Quickshell.env("MODESTY_PREVIEW") === "1" ? "" : root.stateDir + "/appearance.json"
        printErrors: false
        onLoaded: {
            try {
                const data = JSON.parse(text());
                const saved = data.customThemes ?? [];
                const ids = new Set();
                if (!Array.isArray(saved)) throw new Error("Invalid theme list");
                for (const entry of saved) {
                    if (!entry || typeof entry.id !== "string" || !/^custom-\d+$/.test(entry.id) || ids.has(entry.id)
                        || typeof entry.label !== "string" || !entry.label.trim() || typeof entry.source !== "string"
                        || !root.validThemeSource(entry.source, entry.variants)) throw new Error("Invalid saved theme");
                    ids.add(entry.id);
                }
                root.customThemes = saved;
                root.setPalette(ids.has(data.paletteName) || Object.prototype.hasOwnProperty.call(root.palettes, data.paletteName)
                    ? data.paletteName : "wallpaper");
                if (["dark", "light"].includes(data.mode)) root.mode = data.mode;
                root.appearanceReady = true;
                root.scheduleSync();
            } catch (e) { root.appearanceLoadError = "Couldn't read saved appearance. Your file was kept."; }
        }
        onLoadFailed: error => {
            if (error !== FileViewError.FileNotFound) {
                root.appearanceLoadError = "Couldn't open saved appearance. Your file was kept.";
                return;
            }
            root.appearanceReady = true;
            root.scheduleSync();
        }
    }
}
