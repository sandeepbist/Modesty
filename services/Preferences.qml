pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Singleton {
    id: root
    property bool remindersEnabled:true
    property bool deviceIndicator:true
    property int focusMinutes:25
    property int breakMinutes:5
    property int recordCountdown:3
    property int recordFps:60
    property bool recordCursor:true
    property bool contextDevices:true
    property bool contextBattery:true
    property bool compactMissingLyrics: true
    property bool launcherCalculator: true
    property bool launcherDescriptions: false
    property bool matugenAutomatic: true
    property string matugenScheme: "scheme-tonal-spot"
    property real matugenContrast: 0
    property int matugenSource: 0
    property bool themeGtk: true
    property bool themeFolders: false
    property bool themeQt: true
    property bool themeFoot: true
    property bool themeSpotify: true
    property bool footerTray:true
    property bool footerVisible: true
    property bool footerThemes: true
    property bool footerWallpapers: true
    property bool footerPower: true
    property bool footerSettings: true
    property string wallpaperTransition: "fade"
    property real wallpaperDuration: .35
    property int windowGap: 0
    property int trayIconSize: 20
    property int traySpacing: 5
    property bool crispText: true
    property int controlGap: 9
    property int controlRadius: 16
    property int controlIconSize: 24
    property int sliderThickness: 8
    property int lockDuration: 520
    property real lockBlur: .6
    property real lockDim: .36
    property int lockClockSize: 124
    property string fontFamily:"Inter Variable"
    property string clockFontFamily:"Inter Variable"
    property string profileImage:""
    property bool liveMedia:true
    property bool mediaAutoHide:true
    property bool focusQuiet:true
    property bool footerPerformance:true
    property string lockClockStyle:"soft"
    property bool mediaVisualizer:true
    property bool mediaLyrics:true
    property bool fuzzyApps: true
    property bool rememberApps: true
    property string terminal: "foot"
    property bool terminalGreeting:true
    property string terminalArtFormat:"image"
    property string terminalArtMode:"original"
    property string terminalArtCollection:"portraits"
    property string terminalArtPinned:""
    property var terminalArtFavorites:[]
    property var terminalArtHidden:[]
    property bool terminalArtFavoritesOnly:false
    property bool terminalArtMinimal:false
    property int terminalArtSize:36
    property int launcherVisibleRows: 5
    property bool companionEnabled:true
    property bool companionZen:true
    property bool companionTerminal:true
    property int companionSize:64
    property string companionSide:"right"
    property int companionInset:36
    property bool agentFeedback:true
    property bool privacyRadar:true
    property int privacyIndicatorGap:25
    property int privacyIndicatorRightPadding:19
    property bool agentActivity:true
    property int agentActivityInterval:5
    property bool contextWorkspace: true
    property bool contextVolume: true
    property bool contextBrightness: true
    property int contextDuration: 1500
    property int tooltipDelay: 500
    property int hoverLift: 5
    property real motionSpeed: 1.0
    property int notificationDuration: 6000
    property bool notificationBody: true
    property bool welcomeAtLogin: true
    property bool contextEvents: true
    property bool wallpaperColors: true
    property bool use24Hour: true
    property bool showSeconds: false
    property string motion: "fluid"
    property real uiScale: 1
    property int topMargin: 11
    property int barHeight: 33
    property int collapsedWidth: 90
    property int clusterGap: 14
    property int expandedRadius: 28
    property int innerPadding: 10
    property bool showAlbum: true
    property bool showStatus: true
    property bool shadows: true
    property int mediaWidth: 360
    property int controlsWidth: 370
    property int launcherWidth: 550
    property int searchWidth: 700
    property int searchBarHeight: 80
    property int searchMaxHeight: 560
    property int searchRows: 5
    property real searchX: 50
    property real searchY: 50
    property int searchRadius: 24
    property int searchMotion: 210
    property int searchTravelDuration: 620
    property string searchWebPrefix: "web"
    property string searchFilePrefix: "file"
    property bool lumaJev: true
    property bool lumaVoice: true
    property bool lumaVoiceWarm: false
    property bool lumaLocalFiles: true
    property var lumaKnowledgeRoots: []
    property bool lumaWeb: true
    property bool lumaDesktop: true
    property bool lumaSystem: true
    property string lumaAccess: "review"
    property bool lumaEffects: true
    property bool lumaActionDetails: false
    property int lumaTextSize: 14
    property bool lumaWindowContext: true
    property bool lumaRemember: true
    property bool lumaAutoAnswer:true
    property int lumaAnswerDelay:1500
    property bool searchAiEnabled: true
    property string searchAiModel: "gemini-3.5-flash-lite"
    property int calendarWidth: 320
    property string saveError: ""
    readonly property bool preview: Quickshell.env("MODESTY_PREVIEW") === "1"
    readonly property string stateDir: (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/modesty"
    readonly property var defaults: ({companionSide:"right",companionInset:36,companionEnabled:true,companionZen:true,companionTerminal:true,companionSize:64,agentFeedback:true,privacyRadar:true,privacyIndicatorGap:25,privacyIndicatorRightPadding:19,remindersEnabled:true,deviceIndicator:true,focusMinutes:25,breakMinutes:5,recordCountdown:3,recordFps:60,recordCursor:true,contextDevices:true,contextBattery:true,footerTray:true,compactMissingLyrics:true,launcherCalculator:true,launcherDescriptions:false,matugenAutomatic:true,matugenScheme:"scheme-tonal-spot",matugenContrast:0,matugenSource:0,themeGtk:true,themeFolders:false,themeQt:true,themeFoot:true,themeSpotify:true,footerVisible:true,footerThemes:true,footerWallpapers:true,footerPower:true,footerSettings:true,wallpaperTransition:"fade",wallpaperDuration:.35,windowGap:0,trayIconSize:20,traySpacing:5,crispText:true,controlGap:9,controlRadius:16,controlIconSize:24,sliderThickness:8,lockDuration:520,lockBlur:.6,lockDim:.36,lockClockSize:124, fontFamily:"Inter Variable",clockFontFamily:"Inter Variable",profileImage:"",liveMedia:true,mediaAutoHide:true,focusQuiet:true,footerPerformance:true,lockClockStyle:"soft",mediaVisualizer:true,mediaLyrics:true,welcomeAtLogin: true, fuzzyApps: true, rememberApps: true, terminal: "foot", terminalGreeting:true, terminalArtFormat:"image", terminalArtMode:"original", terminalArtCollection:"portraits", terminalArtPinned:"", terminalArtFavorites:[], terminalArtHidden:[], terminalArtFavoritesOnly:false, terminalArtMinimal:false, terminalArtSize:36, launcherVisibleRows: 5, agentActivity:true, agentActivityInterval:5, contextWorkspace: true, contextVolume: true, contextBrightness: true, contextDuration: 1500, tooltipDelay: 500, hoverLift: 5, motionSpeed: 1.0, notificationDuration: 6000, notificationBody: true, wallpaperColors: true, contextEvents: true, use24Hour: true, showSeconds: false, motion: "fluid", uiScale: 1, topMargin: 11, barHeight: 33, collapsedWidth: 90, clusterGap: 14, expandedRadius: 28, innerPadding: 10, showAlbum: true, showStatus: true, shadows: true, mediaWidth: 360, controlsWidth: 370, launcherWidth: 550, searchWidth:700, searchBarHeight:80, searchMaxHeight:560, searchRows:5, searchX:50, searchY:50, searchRadius:24, searchMotion:210, searchTravelDuration:620, searchWebPrefix:"web", searchFilePrefix:"file", lumaJev:true,lumaVoice:true,lumaVoiceWarm:false,lumaLocalFiles:true,lumaKnowledgeRoots:[],lumaWeb:true,lumaDesktop:true,lumaSystem:true,lumaAccess:"review",lumaEffects:true,lumaActionDetails:false,lumaTextSize:14,lumaWindowContext:true,lumaRemember:true,lumaAutoAnswer:true,lumaAnswerDelay:1500,searchAiEnabled:true, searchAiModel:"gemini-3.5-flash-lite", calendarWidth: 320 })
    function set(key: string, value: var): void {
        if (!(key in defaults)) return;
        if (typeof defaults[key] === "boolean" && typeof value !== "boolean") return;
        if (key === "lumaAccess" && !["review", "full"].includes(value)) return;
        if (key === "lockClockStyle" && !["soft","sculpted","classic"].includes(value)) return;
        if (key === "companionSide" && !["left", "right"].includes(value)) return;
        if (key === "motion" && !["fluid", "gentle", "instant"].includes(value)) return;
        if (["uiScale", "topMargin"].includes(key)) {
            if (!Number.isFinite(value)) return;
            if (key === "uiScale") value = Math.round(Math.max(0.85, Math.min(1.25, value)) * 100) / 100;
            if (key === "topMargin") value = Math.round(Math.max(0, Math.min(32, value)));
        }
        const ranges = {barHeight:[28,44],collapsedWidth:[72,150],clusterGap:[6,28],expandedRadius:[16,36],innerPadding:[6,16],mediaWidth:[300,440],controlsWidth:[340,440],launcherWidth:[420,680],calendarWidth:[280,400]};
        if (ranges[key]) { if (!Number.isFinite(value)) return; value = Math.round(Math.max(ranges[key][0], Math.min(ranges[key][1], value))); }
        const extraRanges={lumaTextSize:[12,18],privacyIndicatorGap:[0,40],privacyIndicatorRightPadding:[0,40],companionInset:[0,160],companionSize:[40,90],agentActivityInterval:[5,30],terminalArtSize:[24,60],focusMinutes:[1,120],breakMinutes:[1,60],recordCountdown:[0,5],matugenContrast:[-1,1],matugenSource:[0,4],wallpaperDuration:[.2,.7],windowGap:[-32,40],trayIconSize:[16,24],traySpacing:[0,12],controlGap:[4,16],controlRadius:[8,24],controlIconSize:[18,30],sliderThickness:[4,14],lockDuration:[250,900],lockBlur:[0,1],lockDim:[0,.7],lockClockSize:[80,160],launcherVisibleRows:[3,8],searchWidth:[420,960],searchBarHeight:[64,104],searchMaxHeight:[240,720],searchRows:[2,10],searchX:[0,100],searchY:[0,100],searchRadius:[14,34],searchMotion:[0,400],searchTravelDuration:[0,1200],lumaAnswerDelay:[700,3000],contextDuration:[800,4000],tooltipDelay:[150,1000],hoverLift:[0,10],motionSpeed:[.65,1.5],notificationDuration:[2000,12000]};
        if(extraRanges[key]){if(!Number.isFinite(value))return;value=Math.max(extraRanges[key][0],Math.min(extraRanges[key][1],value));if(!["motionSpeed","lockBlur","lockDim","wallpaperDuration","matugenContrast","searchX","searchY"].includes(key))value=Math.round(value);}
        if(key==="profileImage"&&(typeof value!=="string"||!(value===""||value==="none"||value.startsWith("file://"))))return;
        if(["searchWebPrefix","searchFilePrefix"].includes(key)){
            if(typeof value!=="string"||!(/^[a-z][a-z0-9_-]{0,19}$/i).test(value.trim()))return;
            value=value.trim().toLowerCase();
            if(value===root[key==="searchWebPrefix"?"searchFilePrefix":"searchWebPrefix"])return;
        }
        if(key==="searchAiModel"&&!["gemini-3.5-flash-lite","gemini-3.8-flash","gemini-3.1-flash-lite","gemini-2.5-flash-lite"].includes(value))return;
        if(key==="terminalArtCollection"&&!["atelier","portraits","legends","all"].includes(value))return;
        if(key==="terminalArtPinned"&&(typeof value!=="string"||!/^$|^(atelier|portraits|legends)\/[a-z0-9-]+$/.test(value)))return;
        if(key==="lumaKnowledgeRoots"){
            const home=Quickshell.env("HOME");
            if(!Array.isArray(value))return;
            value=[...new Set(value.filter(p=>typeof p==="string"&&p.startsWith(home+"/")&&!p.split("/").some(part=>part.startsWith("."))))].slice(0,12);
        }
        if(["terminalArtFavorites","terminalArtHidden"].includes(key)){
            if(!Array.isArray(value))return;
            value=[...new Set(value.filter(v=>typeof v==="string"&&/^(atelier|portraits|legends)\/[a-z0-9-]+$/.test(v)))].slice(0,256);
        }
        if(key==="terminalArtMode"&&!["original","theme"].includes(value))return;
        if(key==="terminalArtFormat"&&!["image","ascii"].includes(value))return;
        if(key==="terminal"&&!["foot","kitty","alacritty","wezterm"].includes(value))return;
        if(["fontFamily","clockFontFamily"].includes(key)&&!["Instrument Sans","Inter Variable","Adwaita Sans"].includes(value))return;
        if(key==="wallpaperTransition"&&!["none","fade"].includes(value))return;
        if(key==="matugenScheme"&&!["scheme-content","scheme-expressive","scheme-fidelity","scheme-fruit-salad","scheme-monochrome","scheme-neutral","scheme-rainbow","scheme-tonal-spot","scheme-vibrant","scheme-smart"].includes(value))return;
        if(key==="recordFps"&&![30,60].includes(value))return;
        if (root[key] === value) return;
        root[key] = value;
        if (!preview) saveDelay.restart();
    }
    function reset(): void { for (const key of Object.keys(defaults)) set(key, defaults[key]); }
    function snapshot(): var { const data = {}; for (const key of Object.keys(defaults)) data[key] = root[key]; return data; }
    Timer { id: saveDelay; interval: 300; onTriggered: { if (writer.running) { restart(); return; } writer.command = ["python3", Qt.resolvedUrl("../scripts/preferences.py").toString().replace("file://", ""), JSON.stringify(root.snapshot())]; writer.running = true; } }
    Process { id: writer; onExited: code => root.saveError = code === 0 ? "" : "Couldn't save your preferences" }
    FileView {
        path: root.preview ? "" : root.stateDir + "/preferences.json"
        printErrors: false
        onLoaded: {
            try {
                const data = JSON.parse(text());
                const oldTransition = data.wallpaperTransition && !["fade", "none"].includes(data.wallpaperTransition);
                if (oldTransition) { data.wallpaperTransition = "fade"; data.wallpaperDuration = .35; }
                const oldDuration = data.wallpaperDuration > .7;
                for (const key of Object.keys(root.defaults)) if (key in data) root.set(key, data[key]);
                saveDelay.stop();
                if (oldTransition || oldDuration) saveDelay.restart();
            }
            catch (e) { root.saveError = "Couldn't read saved preferences. Using defaults."; }
        }
    }
}
