import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import Quickshell.Widgets
import qs.services
import qs.components
import qs.theme
import "../../services/vendor/fuzzysort.js" as Fuzzy
import "../../services/ModelDiff.js" as ModelDiff

PanelWindow {
    id: window
    screen: Quickshell.screens.find(s => s.name === Hyprland.focusedMonitor?.name) ?? Quickshell.screens[0]
    implicitWidth: screen?.width ?? 1920
    implicitHeight: screen?.height ?? 1080
    color: "transparent"
    visible: CanvasState.opened || card.opacity > 0 || travelPhase !== ""
    WlrLayershell.namespace: "modesty-command-canvas"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: !CanvasState.opened ? WlrKeyboardFocus.None : window.acquireFocus ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.OnDemand
    anchors { top: true; left: true }
    mask: Region {
        item: CanvasState.opened ? card : null
        radius: surface.radius
        Region { item: CanvasState.opened && scopeMenu.opened ? scopeMenu.contentItem : null; radius: 10 }
    }
    property bool acquireFocus: false
    HyprlandFocusGrab {
        active: CanvasState.opened
        windows: [window]
        onCleared: { window.acquireFocus = false; if(CanvasState.opened)CanvasState.close(); }
    }
    property Item originItem: null
    property string originScreenName: ""
    property bool originAvailable: false
    property real originX: 0
    property real originY: 0
    property real travelProgress: 0
    property string travelPhase: ""
    function segment(value: real,begin: real,end: real): real {
        const t=Math.max(0,Math.min(1,(value-begin)/(end-begin)));
        return t*t*t*(t*(t*6-15)+10);
    }
    readonly property bool travelling: travelPhase!==""
    readonly property real separationAmount:segment(travelProgress,.03,.2)
    readonly property real orbSize:24*segment(travelProgress,0,.12)
    readonly property real fallAmount: segment(travelProgress,.08,.66)
    readonly property real widthAmount: segment(travelProgress,.50,.93)
    readonly property real heightAmount: segment(travelProgress,.62,.96)
    readonly property real headerAmount: travelling?segment(travelProgress,.78,.98):1
    readonly property real contentAmount: travelling?segment(travelProgress,.90,1):1


    readonly property string backend: Qt.resolvedUrl("../../scripts/command-canvas.py").toString().replace("file://", "")
    readonly property string calculator: Qt.resolvedUrl("../../scripts/calculator.py").toString().replace("file://", "")
    property string selectedScope: "all"
    property string pendingScope: ""
    property real scopeExposure: 1
    readonly property var prefix: matchPrefix(input.text)
    readonly property string query: prefix ? input.text.slice(prefix.length) : input.text
    readonly property string scope: prefix ? prefix.scope : selectedScope
    property string provider: "web"
    property int selected: 0
    property string selectedKey: ""
    property bool selectionPinned: false
    property bool syncingResults:false
    property var fileRows: []
    property string fileQuery: ""
    property var contentRows: []
    property string contentQuery: ""
    property var webRows: []
    property string webQuery: ""
    property var onlineRows: []
    property string onlineQuery: ""
    property string onlineError: ""
    property var quickAnswer: null
    property var heldAnswer:null
    property string answerQuery: ""
    property bool answerExpanded: false
    property bool answerRevealed: false
    property bool sourceSettled: false
    property string answerStatus: "Understanding"
    property string answerError: ""
    property real answerRetryAt: 0
    property real lastAnswerStarted:0
    property string queuedAsk:""
    property string semanticPerformanceQuery:""
    property string voiceDraft:""
    property string displayedVoiceText:""
    property string displayedVoiceStatus:"Listening"
    property string displayedVoiceError:""
    function retainVoice():void {
        if(Voice.active){displayedVoiceText=input.text;displayedVoiceStatus=!Voice.ready?"Preparing voice":Voice.phase==="finishing"?"Finishing":Voice.phase==="starting"?"Connecting":"Listening";}
        if(Voice.error)displayedVoiceError=Voice.error;
    }
    property int promptIndex:0
    readonly property var prompts:["What’s on your mind?", "Let’s find that thing.", "A question, an idea, a plan…", "What can I help with?"]
    readonly property string prompt:scope==="ask"?(Luma.messages.length?"Where shall we go next?":"What’s on your mind?"):scope==="all"?prompts[promptIndex]:({files:"Find that file…",content:"Find a line you remember…",actions:"What would you like to change?",clipboard:"Find something you copied…",web:provider==="web"?"What’s out there?":"Explore "+provider.charAt(0).toUpperCase()+provider.slice(1)+"…"})[scope]||"What’s on your mind?"
    readonly property color searchSurface:Theme.bgSolid
    readonly property bool actionQuery:scope==="all"&&!!query.trim()&&Fuzzy.go(query.trim(),actions,{key:"search",threshold:.85}).length>0
    readonly property string requestText:query.trim().replace(/^(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?/i,"")
    // Conservative typing hint only; Jev resolves meaning on submitted requests.
    readonly property bool diagnosticQuery:/\b(?:slow(?:er|ing|down|ness)?|sluggish|lags?|laggy|lagg?ing|stutters?|stuttering|freezing|frozen|unresponsive|performance|cpu usage|ram usage|memory usage|resource usage|disk usage|system load)\b/i.test(requestText)||!!semanticPerformanceQuery&&semanticPerformanceQuery===query.trim()
    readonly property bool commandQuery:diagnosticQuery||/^(?:remind\s+me\b|(?:set|add|create|schedule)\b|(?:change|switch|turn|adjust)\b|(?:stay|keep)\b|(?:open|launch|start|pause|resume|cancel|stop)\b|(?:play\s+music|next\s+track|skip\s+song|previous\s+track)\b)/i.test(requestText)
    readonly property bool currentQuery:/\b(?:latest|news|today|current|recent|breaking|this week|this month|updates?)\b/i.test(query)
    readonly property bool onlineEligible:!Voice.active&&(scope==="web"&&provider==="web"||scope==="all"&&currentQuery&&!commandQuery)
    readonly property bool autoQueryReady:query.trim().length>=6&&!/\b(?:is|are|was|were|the|a|an|of|for|to|in|on|from|and|with|my|please|me)$/i.test(query.trim())
    readonly property bool answerEligible:!Voice.active&&!Voice.error&&(scope==="all"&&Preferences.searchAiEnabled&&!actionQuery&&!commandQuery||scope==="web"&&provider==="web")&&!calculating
    readonly property bool answerHasText:answerEligible&&answerQuery===query.trim()&&!!quickAnswer
    readonly property bool answerVisible:answerEligible&&query.trim().length>=4&&answerRevealed&&!previewPath&&(Preferences.lumaAutoAnswer||answerHasText)
    readonly property bool answerPending:answerVisible&&!sourceSettled
    property var clipboardRows: []
    property string calculation: ""
    property string calculationError: ""
    property string previewPath: ""
    property string previewText: ""
    property bool actionBar: false
    property int actionIndex: 0
    property bool indexed: false
    property bool confirmClear: false
    property string fileError: ""
    property bool suppressResize: false
    readonly property bool calculating: scope==="all"&&query.trim().startsWith("=")
    readonly property var modes: [
        {id:"all", title:"Auto", icon:"search"},
        {id:"files", title:"Files", icon:"folder"},
        {id:"content", title:"Inside files", icon:"article"},
        {id:"actions", title:"Actions", icon:"bolt"},
        {id:"clipboard", title:"Clipboard", icon:"content_paste"},
        {id:"web", title:"Web", icon:"language"},
        {id:"ask", title:"Conversation", icon:"luma"}
    ]
    readonly property var actionIcons: ({settings:"settings",quicksettings:"tune",calendar:"calendar_today",themes:"palette",wallpapers:"wallpaper",wifi:"wifi",bluetooth:"bluetooth",display:"monitor",sound:"volume_up",reminder:"add_task",focus:"timer",recorder:"videocam",appearance:"contrast",awake:"coffee",peace:"do_not_disturb_on",nightlight:"nightlight",lock:"lock",power:"power_settings_new",media:"music_note",notifhistory:"notifications",playpause:"play_arrow",next:"skip_next",previous:"skip_previous"})
    readonly property var actions: Bindings.actions.filter(a => !!actionIcons[a.id]).map(a => ({key:"action:"+a.id, kind:"action", id:a.id, title:a.label, subtitle:"", icon:actionIcons[a.id], search:Fuzzy.prepare(a.label+" "+a.id)}))
    readonly property var results: composeResults()
    function matchPrefix(value: string): var {
        const match=/^\s*([a-z][a-z0-9_-]{0,19}):\s*/i.exec(value);
        if(!match)return null;
        const word=match[1].toLowerCase();
        if(word===Preferences.searchWebPrefix)return {scope:"web",length:match[0].length};
        if(word===Preferences.searchFilePrefix)return {scope:"files",length:match[0].length};
        return null;
    }
    function search(value: string): void { Qt.callLater(()=>{window.acquireFocus=true;input.text=value;input.forceActiveFocus();}); }
    function diagnostics(): var { return {open:CanvasState.opened,query,scope,calculating,calculation,calculationError,calculatorRunning:calculatorWorker.running,calculatorPending:calcDelay.running,prefix:prefix?.scope??"",selected,listIndex:list.currentIndex,actionBar,actionIndex,previewPath,count:results.length,results:results.slice(0,12).map(r=>({kind:r.kind,title:r.title})),answer:answerHasText?quickAnswer.title:"",answerKind:answerHasText?quickAnswer.label??"Source":"",answerPending,answerQuery,answerEligible,answerRunning:answerWorker.running,aiRunning:Luma.busy,indexed,attachmentPicker:conversation.pickerOpen,inputFocused:input.activeFocus,windowFocused:input.Window.active,keyboardAcquired:window.acquireFocus,x:card.x,y:card.y,width:card.width,height:card.height,originX,originY,travelPhase,travelProgress}; }
    function capture(path: string): void { if(CanvasState.opened) card.grabToImage(result => result.saveToFile(path)); }
    function moveDrop(opening: bool): void {
        travel.stop();
        const source=originItem&&originAvailable&&originScreenName===screen?.name
            ? originItem.mapToItem(null,originItem.width/2,originItem.height-3) : null;
        if (!source || !Number.isFinite(source.x) || !Number.isFinite(source.y) || Tokens.reducedMotion || Preferences.searchTravelDuration===0) {
            travelPhase="";travelProgress=opening?1:0;return;
        }
        if(opening&&travelProgress<.001){originX=source.x;originY=source.y;}
        travelPhase=opening?"open":"close";
        travel.from=travelProgress;travel.to=opening?1:0;
        travel.duration=Math.max(1,Math.round(Preferences.searchTravelDuration*Math.abs(travel.to-travel.from)));
        travel.start();
    }

    function composeResults(): var {
        if(scope==="ask"||Voice.active)return [];
        const value = query.trim();
        const output = [];
        if (calculating) {
            if (value.length>1) output.push({key:"calculation",kind:calculation?"calculation":calculationError?"error":"pending",title:calculation||calculationError||"Calculating…",subtitle:calculation?"Copy result":"Calculator",icon:"calculate"});
            return output;
        }
        if (scope === "all" || scope === "actions") {
            const matches = value ? Fuzzy.go(value, actions, {key:"search", threshold:.16}).map(r => r.obj) : scope === "actions" ? actions : [];
            output.push(...matches.slice(0, scope === "actions" ? 18 : 5));
        }
        const relatedFiles = value.toLowerCase().startsWith(fileQuery.toLowerCase()) || fileQuery.toLowerCase().startsWith(value.toLowerCase());
        if ((scope === "all" || scope === "files") && value.length >= 2 && relatedFiles)
            output.push(...fileRows.map(f => ({key:"file:"+f.path,kind:"file",title:f.title,subtitle:f.subtitle,icon:f.kind==="folder"?"folder":"draft",path:f.path,sourceQuery:fileQuery})));
        const relatedContent = value.toLowerCase().startsWith(contentQuery.toLowerCase()) || contentQuery.toLowerCase().startsWith(value.toLowerCase());
        if (scope === "content" && value.length >= 3 && relatedContent)
            output.push(...contentRows.map(f => ({key:"content:"+f.path+":"+(f.page||0)+":"+(f.part||0),kind:"file",title:f.title,subtitle:f.excerpt?((f.page?"Page "+f.page+" · ":"")+(f.match||f.excerpt).replace(/\s+/g," ")):f.subtitle,icon:"article",path:f.path,url:f.url||"",excerpt:f.excerpt||"",sourceQuery:contentQuery})));
        if (scope === "clipboard") {
            const found = value ? clipboardRows.filter(c => c.title.toLowerCase().includes(value.toLowerCase())) : clipboardRows;
            output.push(...found.slice(0,30).map(c => ({key:"clip:"+c.id,kind:"clipboard",title:c.title,subtitle:"",icon:"content_paste",id:c.id})));
        }
        if(onlineEligible&&value.length>=3&&onlineQuery===value)
            output.push(...onlineRows.map(page=>({key:"online:"+page.url,kind:"online",title:page.title,subtitle:page.subtitle,icon:"public",url:page.url,sourceQuery:onlineQuery})));
        if ((scope === "all" || scope === "web" && provider === "web") && value.length >= 2 && webQuery===value && (!(answerHasText||answerPending)||scope==="web"))
            output.push(...webRows.filter(page=>!output.some(row=>row.url===page.url)).slice(0,4).map(page => ({key:"page:"+page.url,kind:"webpage",title:page.title,subtitle:(page.kind==="bookmark"?"Bookmark":"History")+" · "+page.subtitle,icon:page.kind==="bookmark"?"bookmark":"public",url:page.url,sourceQuery:webQuery})));
        if (scope === "web") {
            if(Preferences.searchAiEnabled&&provider==="web"&&value)
                output.push({key:"assistant",kind:"assistant",title:"Ask Luma",subtitle:"",icon:"luma"});
            const sites = [{id:"web",title:"Search web",icon:"language"},{id:"youtube",title:"YouTube",icon:"play_circle"},{id:"github",title:"GitHub",icon:"code"},{id:"wikipedia",title:"Wikipedia",icon:"menu_book"}];
            const choices = value ? sites.filter(s => s.id === provider) : sites;
            const googleHint=onlineQuery===value&&onlineError?"Live results unavailable · Open Google":"Google · Open in browser";
            output.push(...choices.map(s => ({key:"site:"+s.id,kind:value?"web":"site",id:s.id,title:value?(s.id==="web"?"Search Google":"Search "+s.title)+" for “"+value+"”":s.title,subtitle:value?(s.id==="web"?googleHint:"Open in browser"):"Search site",icon:s.icon})));
        } else if (scope === "all" && value){
            const assistant=Preferences.searchAiEnabled||commandQuery
                ?{key:"assistant",kind:"assistant",title:"Ask Luma",subtitle:"",icon:"luma"}
                :{key:"site:web",kind:"web",id:"web",title:"Search web",subtitle:"Google",icon:"language"};
            if(commandQuery||currentQuery||/^(?:what|who|where|when|why|how|explain|tell|give|show|can|could|help)\b/i.test(value))output.unshift(assistant);else output.push(assistant);
        }
        return output;
    }
    function setScope(value: string): void {
        if(value===scope&&!scopeMotion.running){input.forceActiveFocus();return;}
        pendingScope=value;
        if(Tokens.reducedMotion||travelling||!CanvasState.opened){commitScope(value);scopeExposure=1;return;}
        scopeMotion.restart();
    }
    function commitScope(value: string): void {
        selectedScope = value; if(prefix)input.text=query;
        provider="web"; selected = 0; selectedKey = ""; selectionPinned=false; actionBar = false; previewPath = ""; answerExpanded=false; confirmClear=false;
        if (value === "clipboard") refreshClipboard();
        if (value === "files") refreshFiles();
        if (value === "content") refreshContent();
        if (value === "web") refreshWeb();
        input.forceActiveFocus();
    }
    function refreshFiles(): void {
        if(Voice.active)return;
        if (query.trim().length < 2 || (scope !== "all" && scope !== "files")) return;
        if (files.running) return;
        files.requestedQuery = query.trim();
        files.command = ["python3", backend, "files", query.trim()]; files.running = true;
    }
    function refreshClipboard(): void {
        if (clipboard.running) return;
        clipboard.command = ["python3", backend, "clipboard"]; clipboard.running = true;
    }
    function refreshContent(): void {
        if(Voice.active)return;
        if (scope !== "content" || query.trim().length < 3) return;
        if (contents.running) return;
        contents.requestedQuery = query.trim();
        contents.command = ["python3", backend, "contents", query.trim()]; contents.running = true;
    }
    function refreshWeb(): void {
        if(Voice.active)return;
        if ((scope!=="all"&&scope!=="web")||query.trim().length<2||browser.running) return;
        browser.requestedQuery=query.trim();
        browser.command=["python3",backend,"browser",query.trim()];browser.running=true;
    }
    function refreshOnline(): void {
        if(!onlineEligible||query.trim().length<3||online.running)return;
        online.requestedQuery=query.trim();
        online.command=["python3",backend,"online",query.trim()];online.running=true;
    }
    function refreshAnswer(force:bool): void {
        if(!CanvasState.opened||!answerEligible||(!force&&(!Preferences.lumaAutoAnswer||!autoQueryReady))||answerWorker.running||Luma.busy||answerHasText||answerRetryAt*1000>Date.now())return;
        if(!force&&Date.now()-lastAnswerStarted<8000){answerDelay.restart();return;}
        lastAnswerStarted=Date.now();
        answerWorker.requestedQuery=query.trim();
        answerWorker.received=false;
        if(Preferences.searchAiEnabled){
            answerWorker.payload=JSON.stringify({query:query.trim(),model:Preferences.searchAiModel,intent:scope==="web"?"research":"auto",history:Luma.messages,useJev:Preferences.lumaJev,web:Preferences.lumaWeb,localFiles:false,desktop:Preferences.lumaDesktop,context:Preferences.lumaDesktop?Luma.context():{}});
            answerWorker.command=["python3",Luma.backend,"preview"];
        }else answerWorker.command=["python3",backend,"answer",query.trim()];
        answerWorker.running=true;
    }
    function submit(modifiers:int):void {
        if(Voice.active)return;
        if(modifiers&Qt.ControlModifier){ask();return;}
        if(actionBar){performQuick(actionIndex);return;}
        if(scope==="ask"){ask();return;}
        if(answerHasText&&(answerExpanded||!results.length)){answerExpanded=!answerExpanded;return;}
        activate(results[selected]);
    }
    function ask(): void {
        if(Voice.active)return;
        const value=query.trim();
        const intent=scope==="web"?"research":scope==="files"||scope==="content"?"local":"auto";
        if(!value||Luma.busy)return;
        if(!commandQuery&&answerWorker.running&&answerWorker.requestedQuery===value&&Luma.beginPreview(value)){
            queuedAsk=value;scopeMotion.stop();scopeExposure=1;commitScope("ask");input.clear();return;
        }
        const ready=answerHasText?quickAnswer:null;
        scopeMotion.stop();scopeExposure=1;commitScope("ask");
        // Stop obsolete preview work; one request now owns the answer.
        answerDelay.stop();answerRevealDelay.stop();
        answerWorker.running=false;
        if(ready&&Luma.usePreview(value,ready)||Luma.send(value,intent))input.clear();
    }
    function retryAnswer(): void {
        if(answerWorker.running||answerRetryAt*1000>Date.now())return;
        sourceSettled=false;quickAnswer=null;answerQuery="";answerError="";answerStatus="Understanding";
        refreshAnswer(true);
        input.forceActiveFocus();
    }
    function step(delta: int): void {
        if (!results.length) return;
        selected = Math.max(0,Math.min(results.length-1,selected+delta));
        selectedKey = results[selected]?.key ?? "";
        selectionPinned = true;
        list.currentIndex=selected;
        list.positionViewAtIndex(selected,ListView.Contain);
    }
    function scrollAnswer(delta: real): void {
        answerPanel.scroll(delta);
    }
    function webUrl(site: string, value: string): string {
        const q = encodeURIComponent(value);
        if (site === "youtube") return "https://www.youtube.com/results?search_query="+q;
        if (site === "github") return "https://github.com/search?q="+q;
        if (site === "wikipedia") return "https://en.wikipedia.org/w/index.php?search="+q;
        return "https://www.google.com/search?q="+q;
    }
    function activate(row): void {
        if (!row) return;
        if(row.kind==="assistant"){ask();return;}
        if (row.kind === "file" && row.sourceQuery !== query.trim()) return;
        if (["webpage","online"].includes(row.kind) && row.sourceQuery !== query.trim()) return;
        if (row.kind === "site") { provider = row.id; selectedKey=row.key; input.forceActiveFocus(); return; }
        if (row.kind === "action") {
            CanvasState.close();
            pendingAction.action = row.id; pendingAction.restart();
        } else if (row.kind === "file") {
            CanvasState.close(); Quickshell.execDetached(["xdg-open",row.url||row.path]);
        } else if (row.kind === "web") {
            CanvasState.close(); Quickshell.execDetached(["xdg-open",webUrl(row.id,query.trim())]);
        } else if (row.kind === "webpage" || row.kind === "online") {
            CanvasState.close(); Quickshell.execDetached(["xdg-open",row.url]);
        } else if (row.kind === "clipboard") {
            CanvasState.close(); Quickshell.execDetached(["python3",backend,"copy",row.id]);
        } else if (row.kind === "calculation") {
            Quickshell.clipboardText = calculation; CanvasState.close();
        }
    }
    function showPreview(): void {
        const row = results[selected];
        if (!row || row.kind !== "file" || row.sourceQuery !== query.trim()) return;
        actionBar = false; previewPath = row.path; previewText = row.excerpt||"";
        if(row.excerpt)return;
        if (!previewer.running) { previewer.requestedPath = row.path; previewer.command = ["python3",backend,"preview",row.path]; previewer.running = true; }
    }
    function performQuick(index: int): void {
        const row = results[selected];
        if (!row) return;
        if (index === 0) { activate(row); return; }
        if (row.kind !== "file") return;
        if (index === 1) showPreview();
        else if (index === 2) { Quickshell.clipboardText = row.path; CanvasState.close(); }
        else if (index === 3) { CanvasState.close(); Quickshell.execDetached(["xdg-open",row.path.substring(0,row.path.lastIndexOf("/"))]); }
        else if(index===5){IslandDrop.accept([row.path]);}
        else if (index === 4) { Luma.attach(row.path); scopeMotion.stop();scopeExposure=1;commitScope("ask"); input.clear(); }
    }
    function closeOne(): void {
        if(Voice.active){Voice.cancel();input.forceActiveFocus();}
        else if(Voice.error){Voice.error="";input.forceActiveFocus();}
        else if (conversation.pickerOpen) conversation.closeAttachments();
        else if (previewPath) {previewPath=""; input.forceActiveFocus();}
        else if (answerExpanded) answerExpanded=false;
        else if (actionBar) actionBar=false;
        else CanvasState.close();
    }
    ListModel {id:resultModel}
    function scheduleCalculation(): void {
        // Scope and expression bindings can settle after query change handlers.
        if(CanvasState.opened&&!Voice.active&&calculating)calcDelay.restart();else calcDelay.stop();
    }
    function syncResults(): void {
        // Coalesce synchronous query changes before touching visible delegates.
        const rows=results.map(row=>({key:row.key,kind:row.kind,id:String(row.id??""),title:row.title??"",subtitle:row.subtitle??"",icon:row.icon??"",path:row.path??"",url:row.url??"",sourceQuery:row.sourceQuery??""}));
        syncingResults=true;
        ModelDiff.reconcile(resultModel,rows,"key");
        const position = selectionPinned ? results.findIndex(r => r.key === selectedKey) : -1;
        selected = position >= 0 ? position : 0;
        selectedKey = results[selected]?.key ?? "";
        // Qt preserves the current delegate across inserts, which can move it
        // to the bottom. Restore our selection even when selected remains 0.
        list.currentIndex=results.length?selected:-1;
        if(!selectionPinned)list.positionViewAtBeginning();
        syncingResults=false;
    }
    onSelectedChanged:if(!syncingResults)list.currentIndex=results.length?selected:-1
    onResultsChanged:Qt.callLater(syncResults)
    Component.onCompleted:syncResults()
    onQueryChanged: {
        semanticPerformanceQuery="";
        if(!Voice.active)Voice.error="";
        if(!Luma.previewActive&&query.trim()!==queuedAsk)queuedAsk="";
        selectionPinned=false; selected=0; selectedKey=""; previewPath=""; actionBar=false;
        if(quickAnswer)heldAnswer=quickAnswer;
        if(query.trim().length<4)heldAnswer=null;
        answerExpanded=!!heldAnswer&&answerExpanded;quickAnswer=null;answerQuery="";answerRevealed=answerRevealed&&answerEligible&&query.trim().length>=4;sourceSettled=false;answerStatus=heldAnswer?"Refining":"Understanding";answerError="";
        list.positionViewAtBeginning();
        calculation=""; calculationError="";
        if(Voice.active)return;
        if ((scope==="all"||scope==="files") && query.trim().length>=2) fileDelay.restart();
        else fileDelay.stop();
        Qt.callLater(scheduleCalculation);
        if (scope==="content" && query.trim().length>=3) contentDelay.restart(); else contentDelay.stop();
        if ((scope==="all"||scope==="web")&&query.trim().length>=2) webDelay.restart(); else webDelay.stop();
        if (onlineEligible&&query.trim().length>=3) onlineDelay.restart(); else onlineDelay.stop();
        if (answerEligible&&query.trim().length>=4) answerDelay.restart(); else answerDelay.stop();
        if (answerEligible&&query.trim().length>=4) answerRevealDelay.restart(); else answerRevealDelay.stop();
    }
    onAnswerExpandedChanged:if(answerExpanded)actionBar=false
    onScopeChanged: {
        if(!CanvasState.opened||Voice.active)return;
        if(scope==="clipboard")refreshClipboard();
        Qt.callLater(scheduleCalculation);
        if((scope==="all"||scope==="files")&&query.trim().length>=2)fileDelay.restart();else fileDelay.stop();
        if(scope==="content"&&query.trim().length>=3)contentDelay.restart();else contentDelay.stop();
        if((scope==="all"||scope==="web")&&query.trim().length>=2)webDelay.restart();else webDelay.stop();
        if(onlineEligible&&query.trim().length>=3)onlineDelay.restart();else onlineDelay.stop();
        if(answerEligible&&query.trim().length>=4)answerDelay.restart();else answerDelay.stop();
    }
    onAnswerEligibleChanged:{if(answerEligible&&query.trim().length>=4){answerRevealDelay.restart();answerDelay.restart();}else{answerRevealDelay.stop();answerRevealed=false;answerExpanded=false;answerDelay.stop();if(!Luma.previewActive)answerWorker.running=false;}}
    onProviderChanged:if(scope==="web"&&query.trim().length>=3){if(provider==="web"){onlineDelay.restart();answerDelay.restart();}else{onlineDelay.stop();answerDelay.stop();}}
    Connections {target:Luma;function onCancelPreview(){window.queuedAsk="";answerWorker.running=false;}}
    Connections {target:CanvasState;function onConversationRequested(){window.acquireFocus=true;scopeMotion.stop();window.scopeExposure=1;commitScope("ask");input.clear();input.forceActiveFocus();}function onOpenedChanged() {
        if (CanvasState.opened) {
            window.acquireFocus=true;
            closeCleanup.stop();scopeMotion.stop();window.scopeExposure=1;window.pendingScope="";window.suppressResize=true;
            window.promptIndex=0;
            window.selectedScope=Luma.busy?"ask":"all"; window.provider="web"; input.clear();
            window.fileRows=[]; window.previewPath=""; window.actionBar=false;
            input.forceActiveFocus();
            indexDelay.restart();
            resetDone.restart();
            window.moveDrop(true);
        } else {
            window.acquireFocus=false;
            indexDelay.stop();
            calcDelay.stop();calculatorWorker.running=false;
            answerDelay.stop();answerRevealDelay.stop();if(!Luma.previewActive)answerWorker.running=false;
            closeCleanup.restart();
            scopeMenu.close();window.moveDrop(false);
        }
    }}
    Connections {
        target:Voice
        function onStarted(){
            window.voiceDraft=input.text;window.displayedVoiceText=input.text;window.displayedVoiceError="";window.retainVoice();
            answerDelay.stop();answerRevealDelay.stop();answerWorker.running=false;
            fileDelay.stop();contentDelay.stop();webDelay.stop();onlineDelay.stop();calcDelay.stop();
            files.running=false;contents.running=false;browser.running=false;online.running=false;
            scopeMenu.close();scopeMotion.stop();window.scopeExposure=1;
            window.previewPath="";window.actionBar=false;
            input.forceActiveFocus();
        }
        function onTranscriptChanged(){if(Voice.active){input.text=[window.voiceDraft.trim(),Voice.transcript].filter(Boolean).join(" ");window.retainVoice();}}
        function onPhaseChanged(){window.retainVoice();}
        function onReadyChanged(){window.retainVoice();}
        function onErrorChanged(){window.retainVoice();}
        function onCancelled(){input.text=window.voiceDraft;input.forceActiveFocus();}
        function onSubmitted(text){
            input.text=[window.voiceDraft.trim(),text].filter(Boolean).join(" ");
            window.voiceDraft="";window.selectedScope="all";
            // One finalized utterance owns one request; no partial calls or quota use.
            window.ask();input.forceActiveFocus();
        }
    }
    NumberAnimation {id:travel;target:window;property:"travelProgress";easing.type:Easing.Linear;onFinished:{if(Math.abs(window.travelProgress-to)<.001)window.travelPhase="";if(!CanvasState.opened)closeCleanup.restart();}}
    SequentialAnimation {
        id:scopeMotion
        NumberAnimation {target:window;property:"scopeExposure";to:0;duration:Tokens.animFast;easing.type:Easing.InCubic}
        ScriptAction {script:window.commitScope(window.pendingScope)}
        NumberAnimation {target:window;property:"scopeExposure";to:1;duration:Tokens.animMedium;easing.type:Easing.OutQuint}
    }
    Timer {id:closeCleanup;interval:Tokens.reducedMotion?0:80;onTriggered:{if(!CanvasState.opened&&(travel.running||card.opacity>.001)){restart();return;}if(!CanvasState.opened){window.suppressResize=true;input.clear();window.fileRows=[];window.previewPath="";window.actionBar=false;window.selectedScope="all";resetDone.restart();}}}
    Timer {id:resetDone;interval:0;onTriggered:window.suppressResize=false}
    Timer {interval:5800;repeat:true;running:CanvasState.opened&&input.activeFocus&&!input.text&&window.scope==="all"&&window.travelPhase==="";onTriggered:window.promptIndex=(window.promptIndex+1)%window.prompts.length}
    Timer {id:indexDelay;interval:420;onTriggered:if(!indexer.running){indexer.command=["python3",window.backend,"index"];indexer.running=true;}}
    Timer {id:fileDelay;interval:75;onTriggered:window.refreshFiles()}
    Timer {id:contentDelay;interval:170;onTriggered:window.refreshContent()}
    Timer {id:webDelay;interval:110;onTriggered:window.refreshWeb()}
    Timer {id:onlineDelay;interval:450;onTriggered:window.refreshOnline()}
    Timer {id:answerDelay;interval:Math.max(Preferences.lumaAnswerDelay,8000-(Date.now()-window.lastAnswerStarted));onTriggered:window.refreshAnswer()}
    Timer {id:answerRevealDelay;interval:300;onTriggered:window.answerRevealed=true}
    Timer {id:calcDelay;interval:100;onTriggered:if(!calculatorWorker.running){calculatorWorker.command=["python3",window.calculator,window.query];calculatorWorker.running=true;}else restart()}
    Timer {id:pendingAction;property string action:"";interval:145;onTriggered:Bindings.trigger(action)}
    Timer {id:clearReset;interval:3500;onTriggered:window.confirmClear=false}
    Process {id:indexer;stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);window.indexed=!!data.indexed;if(window.query.length>=2)window.refreshFiles();}catch(e){}}}}
    Process {
        id:files
        property string requestedQuery: ""
        stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.query===window.query.trim()){window.fileQuery=data.query;window.fileRows=data.rows||[];window.indexed=!!data.indexed;window.fileError=data.error||"";}}catch(e){window.fileError="File search unavailable";}}}
        onExited:if(window.query.trim()!==requestedQuery && window.query.trim().length>=2)fileDelay.restart()
    }
    Process {id:clipboard;stdout:StdioCollector {onStreamFinished:{try{window.clipboardRows=JSON.parse(text).rows||[];}catch(e){window.clipboardRows=[];}}}}
    Process {id:clipboardWipe;stdout:StdioCollector {onStreamFinished:{try{if(JSON.parse(text).ok){window.clipboardRows=[];window.confirmClear=false;}}catch(e){}}}}
    Process {
        id:contents
        property string requestedQuery: ""
        stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.query===window.query.trim()){window.contentQuery=data.query;window.contentRows=data.rows||[];}}catch(e){window.contentRows=[];}}}
        onExited:if(window.scope==="content"&&window.query.trim()!==requestedQuery&&window.query.trim().length>=3)contentDelay.restart()
    }
    Process {
        id:browser
        property string requestedQuery: ""
        stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.query===window.query.trim()){window.webQuery=data.query;window.webRows=data.rows||[];}}catch(e){window.webRows=[];}}}
        onExited:if(window.query.trim()!==requestedQuery&&window.query.trim().length>=2)webDelay.restart()
    }
    Process {
        id:online
        property string requestedQuery: ""
        stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.query===window.query.trim()){window.onlineQuery=data.query;window.onlineRows=data.rows||[];window.onlineError=data.error||"";}}catch(e){window.onlineError="Live results unavailable";}}}
        onExited:if(window.onlineEligible&&window.query.trim()!==requestedQuery&&window.query.trim().length>=3)onlineDelay.restart()
    }
    Process {
        id:answerWorker
        property string requestedQuery: ""
        property string payload: ""
        property bool received: false
        stdinEnabled:true
        onStarted:if(payload){write(payload+"\n");payload="";}
        stdout:SplitParser {onRead:line=>{
            try {
                const data=JSON.parse(line);
                if(window.queuedAsk&&Luma.previewActive){
                    Luma.receive(Object.assign({},data,{localTask:false,actions:[]}));answerWorker.received=Luma.received;return;
                }
                if(data.query===window.query.trim()){
                    window.sourceSettled=true;
                    answerWorker.received=true;window.answerQuery=data.query;window.quickAnswer=data.answer||null;
                    if(!data.answer)window.answerError="No live source overview. Ask Luma for a full answer.";
                }else if(answerWorker.requestedQuery===window.query.trim()){
                    if(data.event==="text"){
                        window.answerQuery=answerWorker.requestedQuery;
                        window.quickAnswer={text:data.text,presentation:{},title:"Luma",label:"Writing",citations:[],streaming:true};
                        window.heldAnswer=window.quickAnswer;
                    }
                    else if(data.event==="phase")window.answerStatus=data.text||"Thinking";
                    else if(data.event==="answer"){
                        answerWorker.received=true;window.sourceSettled=true;window.answerQuery=answerWorker.requestedQuery;window.answerError="";window.answerRetryAt=0;
                        if(data.liveMetrics===true){window.semanticPerformanceQuery=answerWorker.requestedQuery;window.quickAnswer=null;window.heldAnswer=null;return;}
                        const sources=(data.citations||[]).map(source=>({title:source.title,url:source.url,snippet:source.snippet||"",published:source.published||"",publisher:source.publisher||"",headlineOnly:!!source.headlineOnly,host:source.url.replace(/^https?:\/\//,"").split("/")[0].replace(/^www\./,"")}));
                        window.quickAnswer={text:data.text,presentation:data.presentation||{},title:"Luma",label:sources.length?"Sourced answer":data.intent==="research"?"General answer":"Answer",citations:sources,source:sources[0]?.url??"",sourceName:sources[0]?.host??"",router:data.router,intent:data.intent,model:data.model,cached:!!data.cached};
                        window.heldAnswer=window.quickAnswer;
                    }else if(data.event==="error"){
                        answerWorker.received=true;window.sourceSettled=true;window.answerError=data.text||"Could not complete this answer.";window.answerRetryAt=data.retryAt||0;
                    }
                }
            } catch(e) {if(answerWorker.requestedQuery===window.query.trim()){window.sourceSettled=true;window.answerError="Could not read the answer. Retry when ready.";}}
        }}
        onExited:{
            Luma.refreshUsage();
            if(window.queuedAsk&&Luma.previewActive){window.queuedAsk="";Luma.finishPreview();return;}
            if(!CanvasState.opened||!window.answerEligible)return;
            if(window.query.trim()!==requestedQuery&&window.query.trim().length>=4)answerDelay.restart();
            else if(!received){window.sourceSettled=true;window.answerError="Connection interrupted. Try again.";}
        }
    }
    Process {id:calculatorWorker;stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.query===window.query){window.calculation=data.result||"";window.calculationError=data.error||"";}}catch(e){window.calculationError="Calculator unavailable";}}}}
    Process {
        id:previewer
        property string requestedPath:""
        stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.path===window.previewPath)window.previewText=data.text||"";}catch(e){}}}
        onExited:if(window.previewPath&&window.previewPath!==requestedPath)window.showPreview()
    }

    // A brief connection at the clock's lower edge makes the round surface
    // detach from its source. Reversing the same path joins it on close.
    Rectangle {
        objectName:"lumaConnection"
        visible:window.travelling&&window.travelProgress<.18
        width:10*window.segment(window.travelProgress,0,.07)*(1-window.segment(window.travelProgress,.10,.18))
        height:Math.max(0,card.y+card.height/2-window.originY)
        x:window.originX-width/2;y:window.originY+1;radius:width/2
        color:window.searchSurface
    }
    Item {
        id:card;objectName:"lumaSurface"
        readonly property real finalWidth:Math.min(Preferences.searchWidth,window.width-24)
        readonly property real finalX:Math.max(12,Math.min((window.width-finalWidth)*Preferences.searchX/100,window.width-finalWidth-12))
        readonly property real finalY:Math.max(12,Math.min((window.height-Preferences.searchBarHeight)*Preferences.searchY/100,window.height-Preferences.searchBarHeight-38-104-17-16))
        readonly property bool voiceStatus:Voice.active||!!Voice.error
        readonly property bool expanded:voiceStatus||window.query.trim().length>0||window.scope!=="all"||!!window.previewPath
        readonly property int listTop:Preferences.searchBarHeight+12
        readonly property int answerSpace:window.answerVisible?Math.ceil(answerPanel.preferredHeight)+12:0
        readonly property int footerSpace:window.actionBar?48:window.scope==="clipboard"&&window.clipboardRows.length?45:16
        readonly property real heightLimit:Math.min(window.height-finalY-16,Math.max(Preferences.searchMaxHeight,listTop+68+footerSpace))
        readonly property int rowsShown:window.answerExpanded?0:Math.min(resultModel.count,Preferences.searchRows,Math.max(answerSpace?0:1,Math.floor((heightLimit-listTop-answerSpace-footerSpace-8)/52)))
        readonly property bool emptyMessage:!rowsShown&&((window.scope==="files"&&window.query.trim().length>=2)||(window.scope==="content"&&window.query.trim().length>=3)||(window.scope==="actions"&&window.query.trim().length>0)||window.scope==="clipboard")
        readonly property int baseHeight:Preferences.searchBarHeight
        readonly property int footerHeight:(window.actionBar?50:0)+(window.scope==="clipboard"&&window.clipboardRows.length?36:0)
        readonly property real targetHeight:voiceStatus?Math.min(heightLimit,Voice.error?Math.max(156,voiceError.implicitHeight+100):voiceViewport.y+voiceViewport.height+32):window.scope==="ask"?Math.min(heightLimit,listTop+conversation.preferredHeight+22):rowsShown&&!window.previewPath?Math.min(heightLimit,listTop+answerSpace+rowsShown*52+8+footerSpace):Math.min(heightLimit,(window.answerVisible?listTop+answerSpace+footerSpace:baseHeight)+(window.previewPath?308:emptyMessage?52:0)+footerHeight)
        property real panelWidth:finalWidth
        property real bodyHeight:targetHeight
        width:window.travelling?window.orbSize+(panelWidth-window.orbSize)*window.widthAmount:panelWidth
        height:window.travelling?window.orbSize+(bodyHeight-window.orbSize)*window.heightAmount:bodyHeight
        x:window.travelling?window.originX+(finalX+panelWidth/2-window.originX)*window.fallAmount-width/2:finalX
        y:window.travelling?window.originY+22*window.separationAmount+(finalY+Preferences.searchBarHeight/2-window.originY-22)*window.fallAmount-Math.min(height,Preferences.searchBarHeight)/2:finalY
        opacity:window.travelling?(window.travelProgress>.001?1:0):CanvasState.opened?1:0
        transform:Translate {y:window.travelling||CanvasState.opened?0:8;Behavior on y {enabled:!window.travelling;NumberAnimation {id:panelLiftMotion;duration:Tokens.reducedMotion?0:Preferences.searchMotion;easing.type:Easing.OutQuint}}}
        visible:opacity>0
        Behavior on opacity {enabled:!window.travelling;NumberAnimation {duration:Tokens.reducedMotion?0:Math.round(Preferences.searchMotion*.65);easing.type:Easing.OutCubic}}
        Behavior on panelWidth {enabled:!window.travelling&&!Tokens.reducedMotion&&Preferences.searchMotion>0;SmoothedAnimation {id:widthMotion;velocity:-1;duration:Preferences.searchMotion;reversingMode:SmoothedAnimation.Immediate}}
        Behavior on bodyHeight {enabled:!window.suppressResize&&!window.travelling&&!Tokens.reducedMotion&&Preferences.searchMotion>0;SmoothedAnimation {id:resizeMotion;velocity:-1;duration:Math.round(Preferences.searchMotion*1.15);reversingMode:SmoothedAnimation.Immediate}}
        RectangularShadow {anchors.fill:surface;radius:surface.radius;blur:window.travelling?8+16*window.widthAmount:24;offset.y:window.travelling?3+7*window.widthAmount:10;color:Theme.light?"#18000000":"#40000000";cached:!window.travelling&&!resizeMotion.running&&!widthMotion.running;visible:Preferences.shadows}
        RectangularShadow {anchors.fill:surface;radius:surface.radius;blur:6;offset.y:2;color:"#14000000";cached:!window.travelling&&!resizeMotion.running&&!widthMotion.running;visible:Preferences.shadows}
        ClippingRectangle {
            id:surface;anchors.fill:parent;radius:Math.min(width/2,height/2,window.travelling?12+(Preferences.searchRadius-12)*window.widthAmount:Preferences.searchRadius);antialiasing:true
            color:window.searchSurface;border.width:1;border.color:Theme.withAlpha(Theme.text,.055*(window.travelling?window.segment(window.travelProgress,.12,.22):1))
            Behavior on color { ColorAnimation {duration:Tokens.animSlow} }
            LumaVoiceLight {
                anchors.fill:parent;edge:true;radius:surface.radius
                activity:Voice.error?"error":Voice.active?Voice.phase:Luma.busy?(Luma.phase==="acting"?"acting":"thinking"):answerWorker.running?"thinking":"idle";level:Voice.level
                active:Preferences.lumaEffects&&CanvasState.opened&&!window.travelling&&(Voice.active||!!Voice.error||Luma.busy||answerWorker.running)
                opacity:active?window.headerAmount*(Voice.active||Voice.error||Luma.busy||answerWorker.running?1:input.activeFocus?.24:.10):0;visible:opacity>.001
                Behavior on opacity {NumberAnimation {duration:Tokens.animSlow;easing.type:Easing.OutCubic}}
            }
            Rectangle {
                x:Preferences.searchRadius;y:0;width:Math.max(0,parent.width-x*2);height:1
                opacity:window.travelling?window.widthAmount:1
                gradient:Gradient {
                    orientation:Gradient.Horizontal
                    GradientStop {position:0;color:"transparent"}
                    GradientStop {position:.5;color:Theme.withAlpha(Theme.accent,.26)}
                    GradientStop {position:1;color:"transparent"}
                }
            }
            MouseArea {anchors.fill:parent}
            SurfaceLighting {id:assistantLight;anchors.fill:parent;radius:surface.radius;active:CanvasState.opened&&!window.travelling&&!Voice.active;focused:input.activeFocus;working:answerWorker.running||Luma.busy;opacity:strength*window.headerAmount}
            Item {
                id:content;width:card.panelWidth;height:card.bodyHeight;x:(parent.width-width)/2
            Item {
                id:searchBar;visible:opacity>.001&&!card.voiceStatus;enabled:!card.voiceStatus&&!conversation.pickerOpen;onVisibleChanged:if(visible&&CanvasState.opened&&window.acquireFocus&&!Voice.active)input.forceActiveFocus();opacity:window.headerAmount*(1-voicePane.exposure);x:24;y:10;width:parent.width-48;height:card.baseHeight-20
                IconButton {
                    x:-8;anchors.verticalCenter:parent.verticalCenter;size:22
                    visible:!card.voiceStatus&&window.scope!=="ask"
                    icon:window.calculating?"calculate":window.modes.find(mode=>mode.id===window.scope)?.icon??"search"
                    color:window.scope==="all"?Theme.subtext:Theme.accent
                    label:"Filter · "+(window.modes.find(mode=>mode.id===window.scope)?.title??"Auto")
                    onClicked:scopeMenu.open()
                }
                Menu {
                    id:scopeMenu;objectName:"lumaFilters"
                    x:-4;y:searchBar.height+12;width:196;padding:6
                    closePolicy:Popup.CloseOnEscape|Popup.CloseOnPressOutside
                    onClosed:if(CanvasState.opened)input.forceActiveFocus()
                    background:Rectangle {radius:16;color:Theme.bgSolid;border.width:1;border.color:Theme.withAlpha(Theme.text,.12)}
                    transformOrigin:Popup.TopLeft
                    enter:Transition {ParallelAnimation {NumberAnimation {property:"opacity";from:0;to:1;duration:Tokens.animFast;easing.type:Easing.OutCubic}NumberAnimation {property:"scale";from:.985;to:1;duration:Tokens.animMedium;easing.type:Easing.OutQuint}}}
                    exit:Transition {NumberAnimation {property:"opacity";from:1;to:0;duration:Tokens.animFast;easing.type:Easing.InCubic}}
                    Repeater {model:window.modes
                        MenuItem {
                            id:filter;required property var modelData
                            implicitHeight:39;text:modelData.title
                            onTriggered:window.setScope(modelData.id)
                            background:Rectangle {radius:10;color:filter.highlighted?Theme.withAlpha(Theme.text,.065):"transparent";Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                            contentItem:Item {
                                Icon {x:10;anchors.verticalCenter:parent.verticalCenter;icon:filter.modelData.icon;size:18;color:Theme.subtext}
                                PanelText {x:38;anchors.verticalCenter:parent.verticalCenter;text:filter.text;font.pixelSize:13;font.weight:window.scope===filter.modelData.id?Font.DemiBold:Font.Normal}
                                Icon {anchors.right:parent.right;anchors.rightMargin:9;anchors.verticalCenter:parent.verticalCenter;icon:"check";size:14;color:Theme.accent;visible:window.scope===filter.modelData.id}
                            }
                        }
                    }
                }
                TextInput {
                    id:input;objectName:"commandCanvasSearch"
                    x:window.scope==="ask"?0:44;width:parent.width-x-(Preferences.searchAiEnabled?76:34);height:parent.height
                    verticalAlignment:TextInput.AlignVCenter
                    focus:true;clip:true;selectByMouse:true;maximumLength:6000
                    readOnly:Voice.active
                    visible:!Voice.active
                    color:Theme.text;selectionColor:Theme.accent;selectedTextColor:Theme.accentText
                    font.family:Tokens.font;font.pixelSize:card.panelWidth<560?18:20;font.weight:Font.Medium
                    font.variableAxes:({wght:450,opsz:24});font.letterSpacing:-.35
                    font.kerning:true;font.preferTypoLineMetrics:true
                    font.hintingPreference:Font.PreferVerticalHinting;renderType:Tokens.textRenderType
                    Accessible.name:"Ask Luma"
                    cursorDelegate:Rectangle {width:1.5;height:input.font.pixelSize+3;y:(input.height-height)/2;radius:.75;color:Theme.accent;opacity:input.activeFocus&&input.cursorVisible&&input.text.length?1:0;Behavior on opacity {NumberAnimation {duration:Tokens.reducedMotion?0:90}}}
                    Keys.onDownPressed:window.scope==="ask"?conversation.scroll(36):window.answerExpanded?window.scrollAnswer(36):window.step(1)
                    Keys.onUpPressed:window.scope==="ask"?conversation.scroll(-36):window.answerExpanded?window.scrollAnswer(-36):window.step(-1)
                    Keys.onEscapePressed:if(window.scope==="ask"&&conversation.historyOpen)conversation.historyOpen=false;else window.closeOne()
                    Keys.onTabPressed:event=>{if(!window.answerExpanded&&window.results[window.selected]?.kind==="file"){window.actionIndex=window.actionBar?(window.actionIndex+1)%6:0;window.actionBar=true;window.previewPath="";}event.accepted=true;}
                    Keys.onBacktabPressed:event=>{if(window.actionBar)window.actionIndex=(window.actionIndex+5)%6;event.accepted=true;}
                    Keys.onPressed:event=>{
                        if(event.key===Qt.Key_Return||event.key===Qt.Key_Enter){if(window.scope==="ask"&&conversation.historyOpen)conversation.openSelectedConversation();else window.submit(event.modifiers);event.accepted=true;}
                        else if(event.key===Qt.Key_Space&&event.modifiers===Qt.ControlModifier){if(window.answerExpanded&&window.answerHasText)window.answerExpanded=false;else if(window.results[window.selected]?.kind==="file")window.showPreview();else if(window.answerHasText)window.answerExpanded=true;event.accepted=true;}
                        else if(window.scope==="ask"&&(event.key===Qt.Key_PageDown||event.key===Qt.Key_PageUp)){conversation.scroll(conversation.height*.8*(event.key===Qt.Key_PageDown?1:-1));event.accepted=true;}
                        else if(window.answerExpanded&&(event.key===Qt.Key_PageDown||event.key===Qt.Key_PageUp)){window.scrollAnswer(answerPanel.readingHeight*.8*(event.key===Qt.Key_PageDown?1:-1));event.accepted=true;}
                        else if(event.key>=Qt.Key_1&&event.key<=Qt.Key_7&&event.modifiers===Qt.ControlModifier){window.setScope(window.modes[event.key-Qt.Key_1].id);event.accepted=true;}
                    }
                    RollingText {anchors.fill:parent;visible:!input.text;text:Voice.active?(Voice.held?"I’m listening…":"One moment…"):window.prompt;color:Theme.withAlpha(Theme.text,input.activeFocus?.7:.5);font:input.font;horizontalAlignment:Text.AlignLeft;verticalAlignment:Text.AlignVCenter;Behavior on color {ColorAnimation {duration:Tokens.animMedium}}}
                }
                IconButton {anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter;icon:"close";size:16;label:"Close Luma";visible:!conversation.pickerOpen;onClicked:CanvasState.close()}
                IconButton {
                    id:sendButton;anchors.right:parent.right;anchors.rightMargin:38;anchors.verticalCenter:parent.verticalCenter
                    icon:"arrow_forward";rotation:-90;size:18;label:"Ask Luma · Ctrl+Enter";color:Theme.accent
                    opacity:Preferences.searchAiEnabled&&input.text.trim()?(Luma.busy?.35:1):0
                    enabled:!!input.text.trim()&&!Luma.busy&&!Voice.active;visible:!Voice.active&&opacity>0;onClicked:window.ask()
                    Behavior on opacity {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                }
            }
            Rectangle {x:24;y:card.baseHeight;width:parent.width-48;height:1;color:Theme.withAlpha(Theme.text,.065);opacity:card.expanded&&!card.voiceStatus?window.contentAmount:0;Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}}
            Item {
                id:voicePane
                anchors.fill:parent
                property real exposure:card.voiceStatus?1:0
                visible:exposure>.001;opacity:exposure*window.headerAmount
                enabled:card.voiceStatus&&CanvasState.opened
                Behavior on exposure {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
                transform:Translate {y:6*(1-voicePane.exposure)}
                Row {
                    x:28;y:22;spacing:0
                    RollingText {width:card.panelWidth-96;height:18;text:window.displayedVoiceError?"Voice unavailable":window.displayedVoiceStatus;color:Theme.subtext;font.family:Tokens.font;font.pixelSize:12;font.weight:Font.Medium;horizontalAlignment:Text.AlignLeft;verticalAlignment:Text.AlignVCenter}
                }
                IconButton {x:parent.width-width-20;y:17;icon:"close";size:16;label:Voice.active?"Cancel voice":"Dismiss voice error";onClicked:{if(Voice.active)Voice.cancel();else Voice.error="";}}
                Flickable {
                    id:voiceViewport
                    x:32;y:142;width:parent.width-64
                    height:Math.ceil(voiceTranscript.implicitHeight/Math.max(1,voiceTranscript.lineCount)*Math.min(3,voiceTranscript.lineCount))
                    visible:!window.displayedVoiceError;clip:true;interactive:false
                    contentWidth:width;contentHeight:voiceTranscript.implicitHeight
                    contentY:Math.max(0,contentHeight-height)
                    Behavior on contentY {SmoothedAnimation {velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}}
                    VoiceTranscript {
                        id:voiceTranscript;width:parent.width
                        text:window.displayedVoiceText||"I’m listening"
                        font.pixelSize:card.panelWidth<560?18:20;font.weight:Font.Normal;font.letterSpacing:-.2
                        lineHeight:1.28;color:window.displayedVoiceText?Theme.text:Theme.withAlpha(Theme.text,.62)
                        animate:CanvasState.opened&&!window.travelling&&Voice.active
                    }
                }
                LumaVoiceLight {
                    anchors.horizontalCenter:parent.horizontalCenter;y:54
                    width:240;height:76
                    activity:Voice.phase;level:Voice.level;active:Preferences.lumaEffects&&Voice.active&&CanvasState.opened&&!window.travelling
                    visible:!window.displayedVoiceError
                }
                PanelText {
                    id:voiceError;x:28;y:64;width:parent.width-56
                    visible:!!window.displayedVoiceError;text:window.displayedVoiceError
                    wrapMode:Text.Wrap;elide:Text.ElideNone;font.pixelSize:14;lineHeight:1.4;color:Theme.text
                }
            }
            Item {
                id:bodyOutlet;width:parent.width;height:parent.height
                visible:opacity>.001
                opacity:window.contentAmount*window.scopeExposure*(1-voicePane.exposure)
                enabled:CanvasState.opened&&!Voice.active&&voicePane.exposure<.15&&window.scopeExposure>.85
                transform:Translate {y:5*(1-window.scopeExposure)}
            LumaConversation {
                id:conversation;x:28;y:card.listTop+16;width:parent.width-56;height:Math.max(0,parent.height-y-16)
                visible:window.scope==="ask";onFocusInput:input.forceActiveFocus()
                onFollowupRequested:query=>window.search(query)
                onWebRequested:query=>{window.setScope("web");input.text=query;}
            }
            AbstractButton {
                id:clearClipboard;x:22;y:card.bodyHeight-36;width:parent.width-44;height:27
                visible:window.scope==="clipboard"&&window.clipboardRows.length>0
                hoverEnabled:true;focusPolicy:Qt.NoFocus
                Accessible.name:window.confirmClear?"Confirm clearing clipboard history":"Clear clipboard history"
                onClicked:{if(!window.confirmClear){window.confirmClear=true;clearReset.restart();}else if(!clipboardWipe.running){clipboardWipe.command=["python3",window.backend,"wipe"];clipboardWipe.running=true;}}
                background:Rectangle {radius:8;color:clearClipboard.hovered?Theme.withAlpha(Theme.text,.06):"transparent"}
                contentItem:PanelText {text:window.confirmClear?"Clear all clipboard history?":"Clear history";font.pixelSize:11;color:window.confirmClear?Theme.red:Theme.subtext;horizontalAlignment:Text.AlignRight;verticalAlignment:Text.AlignVCenter}
            }
            LumaAnswer {
                id:answerPanel;x:20;y:card.listTop;width:parent.width-40
                visible:window.answerVisible
                answer:window.answerHasText?window.quickAnswer:window.answerPending?window.heldAnswer:null;pending:window.answerPending
                working:answerWorker.running
                status:window.answerStatus;error:window.answerError;retryAt:window.answerRetryAt
                expanded:window.answerExpanded;animate:CanvasState.opened&&!window.travelling
                availableHeight:Math.max(100,card.heightLimit-card.listTop-card.footerSpace-8)
                onToggleExpanded:window.answerExpanded=!window.answerExpanded
                onContinueConversation:window.ask()
                onRetry:window.retryAnswer()
                onWebResults:window.setScope("web")
                onSourceRequested:url=>{CanvasState.close();Quickshell.execDetached(["xdg-open",url]);}
                onFollowupRequested:query=>{window.ask();window.search(query);}
            }
            Rectangle {id:listFrame;x:18;y:card.listTop+card.answerSpace;width:parent.width-36;height:list.height+12;radius:Math.max(14,Preferences.searchRadius-9);color:"transparent";visible:list.visible;opacity:list.opacity}
            ListView {
                id:list;x:listFrame.x+6;y:listFrame.y+6;width:listFrame.width-12;height:Math.max(0,Math.min(card.rowsShown*52-4,card.bodyHeight-card.listTop-card.answerSpace-card.footerSpace-8))
                objectName:"lumaResults"
                visible:window.scope!=="ask"&&opacity>0&&height>0;opacity:!window.previewPath&&resultModel.count>0?1:0;clip:true;spacing:4;model:resultModel;currentIndex:-1
                onHeightChanged:if(window.actionBar&&window.selected>=card.rowsShown)positionViewAtIndex(window.selected,ListView.Contain)
                Behavior on opacity {NumberAnimation {duration:Tokens.reducedMotion?0:135;easing.type:Easing.OutCubic}}
                keyNavigationEnabled:false;boundsBehavior:Flickable.StopAtBounds
                highlightFollowsCurrentItem:false
                highlight:Rectangle {width:list.width;height:48;radius:12;color:Theme.withAlpha(Theme.text,.025);border.width:1;border.color:Theme.withAlpha(Theme.accent,.65);y:list.currentItem?.y??0;Behavior on y {enabled:!window.syncingResults&&window.selectionPinned&&!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:145;reversingMode:SmoothedAnimation.Immediate}}}
                delegate:AbstractButton {
                    id:row;required property var model;required property int index
                    readonly property var modelData:model
                    width:list.width;height:48;hoverEnabled:true;focusPolicy:Qt.NoFocus
                    Accessible.name:modelData.title;Accessible.description:modelData.subtitle
                    onClicked:{
                        const position=window.results.findIndex(result=>result.key===modelData.key);
                        if(position<0)return;
                        window.selected=position;window.selectedKey=modelData.key;window.selectionPinned=true;
                        window.activate(window.results[position]);
                    }
                    background:Rectangle {radius:12;color:row.pressed?Theme.withAlpha(Theme.accent,.08):row.hovered&&window.selected!==index?Theme.withAlpha(Theme.text,.045):"transparent";Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                    contentItem:Item {
                        Rectangle {id:glyph;anchors.left:parent.left;anchors.leftMargin:12;anchors.verticalCenter:parent.verticalCenter;width:31;height:31;radius:10;color:"transparent";scale:row.pressed?.94:row.hovered?1.06:1
                            Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                            Behavior on scale {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                            Icon {anchors.centerIn:parent;icon:row.modelData.icon;size:20;color:window.selected===row.index?Theme.accent:Theme.subtext;Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                        }
                        Column {anchors.left:glyph.right;anchors.leftMargin:12;anchors.right:parent.right;anchors.rightMargin:38;anchors.verticalCenter:parent.verticalCenter;spacing:2
                            PanelText {width:parent.width;text:row.modelData.title;font.pixelSize:15;font.weight:Font.Medium;font.variableAxes:({wght:500,opsz:20});font.letterSpacing:-.15;elide:Text.ElideRight}
                            PanelText {width:parent.width;visible:!!row.modelData.subtitle;text:row.modelData.subtitle;font.pixelSize:12;font.variableAxes:({wght:420,opsz:16});color:Theme.subtext;elide:row.modelData.kind==="online"?Text.ElideRight:Text.ElideMiddle}
                        }
                        Icon {anchors.right:parent.right;anchors.rightMargin:14;anchors.verticalCenter:parent.verticalCenter;icon:"arrow_forward";rotation:row.modelData.kind==="assistant"?-90:["web","online","webpage"].includes(row.modelData.kind)?-45:0;size:16;color:Theme.subtext;opacity:window.selected===row.index?1:0;visible:opacity>0;transform:Translate {x:row.hovered?2:0;Behavior on x {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}}Behavior on opacity {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}}
                    }
                }
            }
            Item {
                x:25;y:Preferences.searchBarHeight+18;width:parent.width-50;height:card.bodyHeight-card.baseHeight-30
                visible:!!window.previewPath;clip:true
                readonly property bool imageFile:/\.(png|jpe?g|webp|gif|bmp)$/i.test(window.previewPath)
                Image {anchors.fill:parent;fillMode:Image.PreserveAspectFit;asynchronous:true;sourceSize:Qt.size(parent.width,parent.height);source:parent.imageFile?"file://"+window.previewPath:"";visible:parent.imageFile}
                Column {anchors.fill:parent;spacing:12;visible:!parent.imageFile
                    PanelText {width:parent.width;text:window.previewPath.split("/").pop();font.pixelSize:14;font.weight:Font.Medium}
                    Flickable {width:parent.width;height:parent.height-32;contentHeight:previewBody.implicitHeight;clip:true;boundsBehavior:Flickable.StopAtBounds
                        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
                        TextEdit {id:previewBody;width:parent.width;text:window.previewText||"No text preview";readOnly:true;selectByMouse:true;textFormat:TextEdit.PlainText;color:Theme.subtext;selectionColor:Theme.accent;selectedTextColor:Theme.accentText;font.family:Tokens.font;font.pixelSize:13;font.preferTypoLineMetrics:true;wrapMode:TextEdit.Wrap;renderType:Tokens.textRenderType}
                    }
                }
            }
            Row {
                x:24;y:card.bodyHeight-41;visible:window.actionBar&&!window.previewPath;spacing:4
                Repeater {model:[{icon:"open_in_new",label:"Open"},{icon:"visibility",label:"Preview"},{icon:"content_copy",label:"Copy path"},{icon:"folder_open",label:"Show folder"},{icon:"attach_file",label:"Share with Luma"},{icon:"more_horiz",label:"File actions"}]
                    AbstractButton {
                        id:quick;required property var modelData;required property int index
                        implicitWidth:34;implicitHeight:30
                        hoverEnabled:true;focusPolicy:Qt.NoFocus
                        Accessible.name:modelData.label
                        onClicked:window.performQuick(index)
                        onHoveredChanged:if(hovered)Hints.show(quick,modelData.label);else Hints.hide(quick)
                        onPressedChanged:if(pressed)Hints.hide(quick)
                        scale:quick.pressed?.97:1
                        Behavior on scale {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                        background:Rectangle {radius:9;color:quick.hovered?Theme.withAlpha(Theme.text,.07):"transparent";border.width:window.actionIndex===quick.index?1:0;border.color:Theme.withAlpha(Theme.accent,.7);Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                        contentItem:Item {Icon {anchors.centerIn:parent;icon:quick.modelData.icon;size:15;color:window.actionIndex===quick.index?Theme.accent:Theme.subtext}}
                        HoverHandler {cursorShape:Qt.PointingHandCursor}
                    }
                }
            }
            PanelText {anchors.horizontalCenter:parent.horizontalCenter;y:Preferences.searchBarHeight+60;visible:window.scope==="files"&&window.query.trim().length>=2&&!window.results.length;text:!window.indexed?"Indexing files…":window.fileError||"No files found";font.pixelSize:12;color:Theme.subtext}
            PanelText {anchors.horizontalCenter:parent.horizontalCenter;y:Preferences.searchBarHeight+60;visible:window.scope==="content"&&window.query.trim().length>=3&&!window.results.length;text:contents.running?"Searching content…":"No content found";font.pixelSize:12;color:Theme.subtext}
            PanelText {anchors.horizontalCenter:parent.horizontalCenter;y:Preferences.searchBarHeight+60;visible:window.scope==="clipboard"&&!window.results.length;text:window.clipboardRows.length?"No matching clips":"Clipboard empty";font.pixelSize:12;color:Theme.subtext}
            PanelText {anchors.horizontalCenter:parent.horizontalCenter;y:Preferences.searchBarHeight+60;visible:window.scope==="actions"&&window.query.trim().length>0&&!window.results.length;text:"No actions found";font.pixelSize:12;color:Theme.subtext}
            }
            }

        }

    }
}
