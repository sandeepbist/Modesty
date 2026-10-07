.pragma library
// One catalog drives navigation, page content and individual-setting search.
function toggle(key,label,description,extra) { return Object.assign({kind:"toggle",key:key,label:label,description:description||""},extra||{}); }
function slider(key,label,min,max,step,unit,extra) { return Object.assign({kind:"slider",key:key,label:label,min:min,max:max,step:step,unit:unit||""},extra||{}); }
function choice(key,label,options,extra) { return Object.assign({kind:"choice",key:key,label:label,options:options.map(o=>typeof o==="object"?o:{value:o,label:String(o)})},extra||{}); }
function textInput(key,label,description) { return {kind:"text",key:key,label:label,description:description||""}; }
function action(id,label,keywords) { return {kind:"action",key:id,label:label,keywords:keywords||""}; }
function block(id,title,items,custom,keywords) { return {id:id,title:title,items:items||[],custom:custom||"",keywords:keywords||""}; }
var groups=[{id:"island",title:"Island",icon:"web_asset"},{id:"personal",title:"Personalization",icon:"palette"},{id:"assistant",title:"Luma",icon:"luma"},{id:"apps",title:"Apps & workflow",icon:"apps"},{id:"system",title:"System",icon:"computer"}];
var fonts=["Instrument Sans","Inter Variable","Adwaita Sans"];
var pages=[
 {id:"layout",group:"island",title:"Layout & spacing",icon:"web_asset",blocks:[
  block("pill","Pills",[slider("barHeight","Pill height",28,44,1," px"),slider("collapsedWidth","Clock width",72,150,1," px"),slider("clusterGap","Space between pills",6,28,1," px"),toggle("showAlbum","Media pill"),toggle("showStatus","Status pill")]),
  block("spacing","Screen & windows",[slider("topMargin","Gap from screen edge",0,32,1," px"),slider("windowGap","Window gap adjustment",-32,40,1," px")]),
  block("panels","Panel proportions",[slider("innerPadding","Inner padding",6,16,1," px"),slider("expandedRadius","Corner radius",16,36,1," px"),slider("mediaWidth","Player width",300,440,5," px"),slider("controlsWidth","Control center width",340,440,5," px"),slider("calendarWidth","Calendar width",280,400,5," px")])]},
 {id:"clock",group:"island",title:"Clock & calendar",icon:"schedule",blocks:[
  block("time","Time",[toggle("use24Hour","24-hour clock"),toggle("showSeconds","Show seconds"),choice("clockFontFamily","Clock font",fonts)]),
  block("calendar","Calendar",[toggle("remindersEnabled","Calendar reminders"),action("calendar","Open calendar","dates year reminder advance")])]},
 {id:"music",group:"island",title:"Music",icon:"music_note",blocks:[
  block("capsule","Music capsule",[toggle("mediaAutoHide","Hide when unused","Appears for media playback. Paused tracks remain accessible."),choice("musicMode","Content",[{value:"art",label:"Artwork"},{value:"visualizer",label:"Visualizer"},{value:"lyrics",label:"Lyrics"},{value:"both",label:"Both"}]),toggle("compactMissingLyrics","Compact when lyrics are unavailable","Hover to reveal the track title.")])]},
 {id:"status",group:"island",title:"Status & activities",icon:"info",blocks:[
  block("feedback","System feedback",[toggle("contextEvents","Show status in pills"),toggle("contextWorkspace","Workspace names","Show the application name, or a number for an empty workspace."),toggle("contextVolume","Volume changes"),toggle("contextBrightness","Brightness changes"),toggle("contextDevices","Connection changes"),toggle("contextBattery","Battery & charging"),toggle("deviceIndicator","Earbud battery ring","Show connected earbuds and their charge in the status pill."),slider("contextDuration","Status duration",800,4000,100," ms"),toggle("welcomeAtLogin","Welcome at login"),action("hello","Replay Welcome")]),
  block("agents","Coding agents",[toggle("agentActivity","Agent activity"),toggle("agentFeedback","Completion & attention"),slider("agentActivityInterval","Time between updates",5,30,1," s")]),
  block("privacy","Privacy",[toggle("privacyRadar","Capture activity","Show microphone and video use in the left pill.")])]},
 {id:"controls",group:"island",title:"Control center",icon:"tune",blocks:[
  block("editor","Tile layout",[],"controls","drag drop resize reorder tiles controls"),
  block("style","Tile appearance",[slider("controlGap","Space between tiles",4,16,1," px"),slider("controlRadius","Corner radius",8,24,1," px"),slider("controlIconSize","Icon size",18,30,1," px"),slider("sliderThickness","Slider thickness",4,14,1," px")]),
  block("footer","Footer & tray",[toggle("footerVisible","Show footer"),toggle("footerTray","Application tray"),toggle("footerPerformance","Performance shortcut"),toggle("footerThemes","Themes shortcut"),toggle("footerWallpapers","Wallpaper shortcut"),toggle("footerPower","Power shortcut"),toggle("footerSettings","Settings shortcut"),slider("trayIconSize","Tray icon size",16,24,1," px"),slider("traySpacing","Tray icon spacing",0,12,1," px")])]},
 {id:"appearance",group:"personal",title:"Colors & typography",icon:"palette",blocks:[
  block("interface","Interface",[choice("themeMode","Color mode",[{value:"light",label:"Light"},{value:"dark",label:"Dark"}]),choice("fontFamily","Interface font",fonts),slider("uiScale","Interface scale",.85,1.25,.05,"×"),toggle("crispText","Precise text rendering"),toggle("shadows","Soft shadows"),action("themes","Choose theme")]),
  block("palette","Wallpaper palette",[toggle("wallpaperColors","Colors from wallpaper"),toggle("matugenAutomatic","Automatic palette","Faithful wallpaper tones with balanced contrast."),choice("matugenScheme","Color scheme",["tonal-spot","content","expressive","fidelity","fruit-salad","monochrome","neutral","rainbow","vibrant","smart"].map(s=>({value:"scheme-"+s,label:s.replace(/-/g," ")})),{when:"matugenAutomatic",values:[false],hideUnavailable:true}),slider("matugenContrast","Contrast",-1,1,.1,"",{when:"matugenAutomatic",values:[false],hideUnavailable:true}),choice("matugenSource","Source color",[0,1,2,3,4].map(n=>({value:n,label:n?"Color "+(n+1):"Recommended"})),{when:"matugenAutomatic",values:[false],hideUnavailable:true})]),
  block("applications","Application colors",[toggle("themeGtk","GTK applications"),toggle("themeQt","Qt applications"),toggle("themeFoot","Foot terminal"),toggle("themeSpotify","Spotify")])]},
 {id:"wallpaper",group:"personal",title:"Wallpaper",icon:"wallpaper",blocks:[
  block("image","Wallpaper",[action("wallpapers","Choose wallpaper")]),
  block("transition","Transitions",[choice("wallpaperTransition","Effect",[{value:"fade",label:"Crossfade"},{value:"none",label:"Instant"}]),slider("wallpaperDuration","Duration",.2,.7,.05," s",{when:"wallpaperTransition",values:["fade"]})]) ]},
 {id:"motion",group:"personal",title:"Motion",icon:"motion_photos_on",blocks:[
  block("animation","Animation",[choice("motion","Style",[{value:"fluid",label:"Fluid"},{value:"gentle",label:"Gentle"},{value:"instant",label:"Reduced motion"}]),slider("motionSpeed","Animation speed",.65,1.5,.05,"×"),slider("hoverLift","Hover movement",0,10,1," px"),slider("tooltipDelay","Tooltip delay",150,1000,50," ms")])]},
 {id:"companion",group:"personal",title:"Window companion",icon:"person",blocks:[
  block("character","Companion",[toggle("companionEnabled","Show companion","Follows supported window edges. Hidden while Luma is open."),choice("companionSide","Window corner",[{value:"left",label:"Left"},{value:"right",label:"Right"}]),slider("companionInset","Distance from corner",0,160,2," px"),slider("companionSize","Size",40,90,2," px")]),
  block("windows","Supported windows",[toggle("companionZen","Zen browser"),toggle("companionTerminal","Terminals")],"","anime swordsman character position left right pet") ]},
 {id:"launcher",group:"apps",title:"Launcher",icon:"search",blocks:[
  block("search","Search & results",[toggle("fuzzyApps","Fuzzy search","Match abbreviated names and application keywords."),toggle("rememberApps","Learn frequent applications"),toggle("launcherCalculator","Calculator","Start with = for calculations and unit conversions."),choice("terminal","Terminal applications",["foot","kitty","alacritty","wezterm"])]),
  block("layout","Layout",[slider("launcherWidth","Width",420,680,10," px"),slider("launcherVisibleRows","Visible applications",3,8,1,""),action("launcher","Open launcher")])]},
 {id:"search",group:"assistant",title:"Assistant",icon:"luma",blocks:[
  block("answers","Answers",[toggle("searchAiEnabled","AI answers"),toggle("lumaJev","Jev decisions","Understand intent and choose tools for submitted requests."),toggle("lumaAutoAnswer","Answer while typing"),slider("lumaAnswerDelay","Typing pause",700,3000,100," ms",{when:"lumaAutoAnswer",values:[true],hideUnavailable:true}),choice("searchAiModel","Answer model",[{value:"gemini-3.5-flash-lite",label:"3.5 Flash-Lite"},{value:"gemini-3.8-flash",label:"3.8 Flash"},{value:"gemini-3.1-flash-lite",label:"3.1 Flash-Lite"},{value:"gemini-2.5-flash-lite",label:"2.5 Flash-Lite"}])]),
  block("conversation","Conversations",[toggle("lumaRemember","Save conversations"),toggle("lumaActionDetails","Expand action details"),slider("lumaTextSize","Reply text size",12,18,1," px"),action("canvas","Open Luma")])]},
 {id:"luma-access",group:"assistant",title:"Access & tools",icon:"shield",blocks:[
  block("execution","Execution",[toggle("lumaSystem","System tools","Files, commands and supported application interfaces."),choice("lumaAccess","Access mode",[{value:"review",label:"Review commands"},{value:"full",label:"Full access"}],{when:"lumaSystem",values:[true],description:"Full access automatically applies requested steps, including commands that change files or use the network/session. It can delete or alter your data if asked. Administrator commands still require system authentication. Action history records each step."})]),
  block("context","Context & research",[toggle("lumaDesktop","Desktop context","Application names, controls, media and live system readings."),toggle("lumaWindowContext","Read current window","Capture the active application only when your request needs it."),toggle("lumaWeb","Internet research"),toggle("lumaLocalFiles","Local file search")])]},
 {id:"luma-voice",group:"assistant",title:"Voice",icon:"mic",blocks:[
  block("installation","Local model",[],"voice","Moonshine speech STT download install microphone local model"),
  block("voice","Hold to speak",[toggle("lumaVoice","Voice input","Hold Ctrl + backtick; release to submit. Change the key under Keyboard shortcuts."),toggle("lumaVoiceWarm","Preload at login","Keep the local model ready. Uses RAM. No microphone capture until the key is held.",{when:"lumaVoice",values:[true],hideUnavailable:true})]),
  block("appearance","Feedback",[toggle("lumaEffects","Living light","Palette light responds to listening, thinking and actions. Motion pauses when idle or hidden.")])]},
 {id:"luma-layout",group:"assistant",title:"Appearance & layout",icon:"tune",blocks:[
  block("size","Proportions",[slider("searchWidth","Width",420,960,5," px"),slider("searchBarHeight","Input height",64,104,1," px"),slider("searchMaxHeight","Maximum height",240,720,5," px"),slider("searchRows","Result rows",2,10,1," rows"),slider("searchRadius","Corner radius",14,34,1," px")]),
  block("position","Position",[slider("searchX","Horizontal",0,100,.1," %"),slider("searchY","Vertical",0,100,.1," %")]),
  block("motion","Motion",[slider("searchMotion","Panel transition",0,400,10," ms"),slider("searchTravelDuration","Pill morph",0,1200,10," ms"),action("searchReset","Reset layout")]),
  block("prefixes","Typed shortcuts",[textInput("searchWebPrefix","Web prefix","Type prefix: followed by a query."),textInput("searchFilePrefix","File prefix","Type prefix: followed by a filename.")])]},
 {id:"luma-knowledge",group:"assistant",title:"Knowledge",icon:"description",blocks:[block("knowledge","Indexed folders",[],"knowledge","PDF notes documents folder index passages")]},
 {id:"luma-providers",group:"assistant",title:"Models & memory",icon:"key",blocks:[block("providers","Providers & personal notes",[],"searchAi","API key Gemini Jev TypeSafe memory notes quota") ]},
 {id:"media",group:"apps",title:"Media",icon:"music_note",blocks:[
  block("pill","Media pill",[toggle("mediaAutoHide","Hide when inactive"),toggle("liveMedia","Expand during playback"),toggle("mediaVisualizer","Visualizer"),toggle("mediaLyrics","Synced lyrics"),toggle("compactMissingLyrics","Compact without lyrics","Hover to reveal the track title when synced lyrics are unavailable.")])]},
 {id:"notifications",group:"apps",title:"Notifications",icon:"notifications",blocks:[
  block("notifications","Notifications",[toggle("peace","Peace","Keep notification history without popups."),toggle("notificationBody","Message previews"),slider("notificationDuration","Popup duration",2000,12000,500," ms")])]},
 {id:"shortcuts",group:"apps",title:"Keyboard shortcuts",icon:"keyboard",blocks:[block("shortcuts","Shortcuts",[],"shortcuts","keybind keybinding keyboard super zen terminal spotify themes wallpaper applications workspaces media system pill")]},
 {id:"terminal",group:"apps",title:"Terminal artwork",icon:"terminal",blocks:[block("artwork","Artwork & rotation",[],"terminal","foot greeting image ascii illustration portrait legends collection favorites hidden size monochrome palette rotation")]},
 {id:"focus",group:"apps",title:"Focus timer",icon:"timer",blocks:[block("focus","Sessions",[toggle("focusQuiet","Peace during focus","Silence popups during focus, then restore your previous setting. Manual changes take priority."),slider("focusMinutes","Default focus",1,120,1," min"),slider("breakMinutes","Break duration",1,60,1," min"),action("focus","Open focus timer")])]},
 {id:"connections",group:"system",title:"Devices & display",icon:"computer",blocks:[
  block("devices","Devices",[action("wifi","Wi-Fi"),action("bluetooth","Bluetooth"),action("display","Displays"),action("sound","Sound")]),
  block("comfort","Comfort & power",[toggle("awake","Keep awake","Prevent automatic locking, blanking and idle sleep."),toggle("nightLight","Night light"),slider("temperature","Color temperature",2000,6500,25," K",{when:"nightLight",values:[true],description:"Enable night light to adjust."}),action("power","Power menu")])]},
 {id:"lock",group:"system",title:"Lock screen & profile",icon:"lock",blocks:[
  block("profile","Profile picture",[],"profile","avatar account image picture"),
  block("lock","Lock screen",[slider("lockDuration","Transition duration",250,900,10," ms"),slider("lockBlur","Wallpaper blur",0,1,.05,""),slider("lockDim","Wallpaper dimming",0,.7,.05,""),choice("lockClockStyle","Clock style",[{value:"soft",label:"Soft"},{value:"sculpted",label:"Sculpted"},{value:"classic",label:"Classic"}]),slider("lockClockSize","Clock size",80,160,2," px")]),
  block("security","Authentication",[action("unlockcheck","Verify unlock password","pam authentication"),action("locknow","Lock now")])]},
 {id:"recording",group:"system",title:"Screen recording",icon:"videocam",blocks:[block("recording","Recording",[slider("recordCountdown","Countdown",0,5,1," s"),choice("recordFps","Frame rate",[30,60].map(n=>({value:n,label:n+" fps"}))),toggle("recordCursor","Include pointer"),action("recorder","Open recorder")])]},
 {id:"updates",group:"system",title:"Updates",icon:"download",blocks:[block("updates","Modesty updates",[],"updates","ota download install reload restart rollback version dependencies compatibility qt hyprland quickshell")]}];
var legacy=["layout","clock","appearance","motion","launcher","notifications","controls","lock","connections","shortcuts"];
function page(id) { return pages.find(p=>p.id===id)||pages[0]; }
function search(query) {
 var words=query.toLowerCase().trim().split(/\s+/).filter(Boolean);
 if(!words.length)return [];
 var results=[];
 pages.forEach(p=>p.blocks.forEach(b=>{
  var entries=b.items.length?b.items:[{key:b.id,label:b.title,keywords:b.keywords}];
  entries.forEach(s=>{
   var own=(s.label+" "+(s.description||"")+" "+(s.key||"")+" "+(s.keywords||"")+" "+(s.options||[]).map(o=>o.label).join(" ")).toLowerCase();
   var haystack=own+" "+p.title.toLowerCase()+" "+b.title.toLowerCase()+" "+b.keywords.toLowerCase();
   if(words.every(w=>haystack.includes(w)))results.push({page:p.id,block:b.id,key:s.key,label:s.label,path:p.title+" · "+b.title,icon:p.icon,score:words.every(w=>own.includes(w))?0:1});
  });
 }));
 return results.sort((a,b)=>a.score-b.score);
}
