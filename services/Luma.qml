pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.theme

Singleton {
    id: root
    readonly property string backend: Qt.resolvedUrl("../scripts/luma-assistant.py").toString().replace("file://", "")
    property var messages: []
    property var conversations: []
    property string conversationId: ""
    property bool purgeCache: false
    property string streamId: ""
    property string streamedText: ""
    property var proposals: []
    property var citations: []
    property var fileResults: []
    property bool liveMetrics:false
    property var attachments: []
    property string sharedText: ""
    property var currentWindow: null
    property string phase: "idle"
    property string status: ""
    property string error: ""
    property real retryAt:0
    property real retryNow:Date.now()
    readonly property int retrySeconds:Math.max(0,Math.ceil(retryAt-retryNow/1000))
    property string router: ""
    property string intent: "auto"
    property string answerModel: ""
    property string memory: ""
    property string memoryError: ""
    property bool loaded: Preferences.preview
    property bool previewActive:false
    readonly property bool busy: worker.running||previewActive
    property string pendingPayload: ""
    property string pendingSave: ""
    property string pendingMemory: ""
    property bool clearing: false
    property bool cancelPending: false
    readonly property bool savingMemory: memoryWriter.running
    property bool received: false
    property int sequence: 0
    property var pendingTask:null
    property real taskExpires:0
    property var recentTasks:[]
    property string proposalBatch:""
    property bool autoLocal:false
    property var execution:[]
    property string taskToken:""
    property int requestCount:0
    property var usage:({})
    function refreshUsage():void {if(!usageReader.running)usageReader.running=true;}
    function turn(role: string,text: string,hidden: bool,presentation:var,sources:var): var {return {id:Date.now().toString(36)+"-"+(++sequence),role,text,hidden:!!hidden,presentation:presentation||{},citations:sources||[],execution:[]};}
    signal answered()

    IpcHandler {
        target:"luma"
        function ask(query: string): bool {return root.send(query,"auto");}
        function clear(): void {root.clear();}
        function snapshot():string {return JSON.stringify(root.context());}
        function execute(value:string):string {
            if(Preferences.preview||Session.isLocked()||!Preferences.lumaDesktop||!Preferences.lumaSystem)return JSON.stringify({ok:false,error:"System execution unavailable"});
            try{const action=JSON.parse(value);const ok=root.perform(action,-1);return JSON.stringify({ok,status:ok?"requested":"failed",services:root.context()});}
            catch(e){return JSON.stringify({ok:false,error:"Invalid native operation"});}
        }
        function status(): string {return JSON.stringify({busy:root.busy,phase:root.phase,messages:root.messages.length,proposals:root.proposals.length,actions:root.proposals.map(p=>({name:p.name,status:p.status})),error:root.error,router:root.router,intent:root.intent,model:root.answerModel,requests:root.requestCount,access:Preferences.lumaAccess,appearance:Theme.light?"light":"dark",awake:KeepAwake.active,awakeUntil:KeepAwake.until});}
    }
    function receipts(entries:var):var {
        return (entries||[]).slice(-24).map(e=>({at:e.at||Date.now()/1000,tool:{name:e.tool?.name||"",purpose:e.tool?.purpose||"",path:e.tool?.path||"",argv:e.tool?.argv||[],uri:e.tool?.uri||"",action_name:e.tool?.action_name||"",action_args:e.tool?.action_args||"",id:e.tool?.id||"",operation:e.tool?.operation||""},result:{ok:e.result?.ok===true,status:e.result?.status||"",error:e.result?.error||"",path:e.result?.path||"",exitCode:e.result?.exitCode??null,stdout:(e.result?.stdout||"").slice(0,2000),stderr:(e.result?.stderr||"").slice(0,2000),note:e.result?.note||""}}));
    }
    function context(): var {
        return {volume:Math.round(Audio.volume*100),muted:Audio.muted,brightness:Math.round(SystemInfo.brightness*100),
            appearance:Theme.light?"light":"dark",awake:KeepAwake.active,awakeUntil:KeepAwake.until,reminders:Reminders.items.filter(r=>!r.done).slice(-12).map(r=>({id:r.id,title:r.title,date:r.date,time:r.time,dueAt:r.at||0})),peace:Notifications.dnd,nightlight:Display.nightLight,
            media:{title:Media.title,artist:Media.artist,playing:Media.playing,hasSession:Media.hasSession,identity:Media.active?.identity||"",id:Media.active?.dbusName||"",canPlay:Media.active?.canPlay||false,canPause:Media.active?.canPause||false,
                players:Media.players.map(p=>({id:p.dbusName,identity:p.identity,title:p.trackTitle,playing:p.isPlaying,canPlay:p.canPlay,canPause:p.canPause}))},focus:{phase:FocusTimer.phase,duration:FocusTimer.duration,remaining:FocusTimer.remaining},
            agents:AgentWork.tasks.map(t=>({provider:t.provider,state:t.waiting?"waiting":"working"}))};
    }
    function send(query: string,requestIntent: string): bool {
        query=query.trim().slice(0,6000);
        if(!query||busy||cancelPending||!loaded||Preferences.preview||Session.isLocked())return false;
        error="";currentWindow=null;proposals=[];citations=[];fileResults=[];liveMetrics=false;execution=[];taskToken="";router="";intent="auto";answerModel="";received=false;autoLocal=false;requestCount=0;streamId="";streamedText="";
        pendingPayload=JSON.stringify({query,intent:requestIntent||"auto",applications:Preferences.lumaDesktop?Apps.apps.map(a=>({id:a.id,name:a.name})):[],history:messages,attachments,sharedText,model:Preferences.searchAiModel,
            useJev:Preferences.lumaJev,systemAccess:Preferences.lumaSystem,accessMode:Preferences.lumaAccess,localFiles:Preferences.lumaLocalFiles,web:Preferences.lumaWeb,desktop:Preferences.lumaDesktop,context:Preferences.lumaDesktop?context():{},taskContext:Preferences.lumaDesktop?{recentTasks,pendingTask,taskExpires}:{},pendingTask:Preferences.lumaDesktop&&Date.now()<taskExpires?pendingTask:null,aiEnabled:Preferences.searchAiEnabled,currentWindowAllowed:Preferences.lumaWindowContext});
        messages=messages.concat([turn("user",query)]).slice(-16);
        proposalBatch=messages[messages.length-1].id;
        phase="routing";status="Understanding";
        worker.command=["python3",backend,"chat"];worker.running=true;
        return true;
    }
    signal cancelPreview()
    function beginPreview(query:string):bool {
        if(busy||Preferences.preview||Session.isLocked()||attachments.length||sharedText)return false;
        previewActive=true;received=false;autoLocal=false;requestCount=0;proposals=[];citations=[];fileResults=[];liveMetrics=false;error="";streamId="";streamedText="";
        messages=messages.concat([turn("user",query)]).slice(-16);phase="composing";status="Finishing answer";return true;
    }
    function finishPreview():void {
        previewActive=false;
        if(!received)recordFailure("Assistant stopped before answering.");
        status="";refreshUsage();save();
    }
    function usePreview(query:string,answer:var):bool {
        if(busy||!loaded||Preferences.preview||Session.isLocked()||attachments.length||sharedText||!answer?.text||!["research","writing","conversation"].includes(answer.intent))return false;
        messages=messages.concat([turn("user",query),turn("assistant",answer.text,false,answer.presentation,answer.citations)]).slice(-16);
        streamFlush.stop();streamId="";streamedText="";currentWindow=null;proposals=[];fileResults=[];liveMetrics=false;citations=answer.citations||[];error="";status="";
        router=answer.router||"";intent=answer.intent;answerModel=answer.model||"";phase="idle";received=true;retryAt=0;
        save();answered();return true;
    }
    function cancel(): void {
        if(!busy)return;
        if(previewActive){previewActive=false;cancelPreview();}else{cancelPending=true;worker.running=false;}phase="idle";status="";received=true;
        streamFlush.stop();flushStream();streamedText="";
        messages=messages.concat([turn("assistant","Stopped.")]).slice(-16);save();
    }
    function retry(): bool {
        if(taskToken&&!busy&&!Preferences.preview&&!Session.isLocked()&&Preferences.lumaSystem){
            error="";received=false;streamId="";streamedText="";phase="reading";status="Continuing task";
            pendingPayload=JSON.stringify({token:taskToken,context:context(),accessMode:Preferences.lumaAccess});worker.command=["python3",backend,"continue"];worker.running=true;return true;
        }
        const index=messages.map(m=>m.role).lastIndexOf("user"),last=messages[index];
        if(!last||busy)return false;
        const previous=messages;messages=messages.slice(0,index);
        const started=send(last.text,"auto");
        if(!started)messages=previous;
        return started;
    }
    function save(): void {
        if(!loaded||Preferences.preview)return;
        if(Preferences.lumaRemember){clearing=false;storeConversation();pendingSave=JSON.stringify({active:conversationId,threads:conversations,purgeCache});purgeCache=false;}
        else {pendingSave="";clearing=true;}
        saveDelay.restart();
    }
    function clear(): void {
        if(busy)cancel();
        messages=[];proposals=[];citations=[];fileResults=[];liveMetrics=false;execution=[];taskToken="";attachments=[];sharedText="";currentWindow=null;error="";phase="idle";status="";router="";intent="auto";answerModel="";
        pendingSave="";clearing=true;saveDelay.restart();
        pendingTask=null;taskExpires=0;recentTasks=[];proposalBatch="";
        conversations=[];conversationId="";streamId="";streamedText="";streamFlush.stop();
    }
    function storeConversation():void {
        if(!conversationId)conversationId=Date.now().toString(36)+"-"+(++sequence);
        const first=messages.find(m=>m.role==="user");
        const record={id:conversationId,title:(first?.text||"New conversation").slice(0,72),updatedAt:Date.now(),messages,citations,taskContext:{recentTasks,pendingTask,taskExpires,systemRun:taskToken}};
        conversations=conversations.filter(t=>t.id!==conversationId).concat([record]).slice(-32);
    }
    function resetConversation():void {
        messages=[];proposals=[];citations=[];fileResults=[];liveMetrics=false;execution=[];taskToken="";attachments=[];sharedText="";currentWindow=null;error="";status="";phase="idle";pendingTask=null;taskExpires=0;recentTasks=[];proposalBatch="";streamId="";streamedText="";router="";intent="auto";answerModel="";
    }
    function restoreTasks(value:var):void {
        recentTasks=value?.recentTasks||[];
        taskToken=typeof value?.systemRun==="string"&&/^[a-f0-9]{32}$/.test(value.systemRun)?value.systemRun:"";
        taskExpires=value?.taskExpires||0;pendingTask=taskExpires>Date.now()?value?.pendingTask||null:null;
    }
    function newConversation():void {
        if(busy||!loaded)return;
        storeConversation();resetConversation();conversationId=Date.now().toString(36)+"-"+(++sequence);save();
    }
    function selectConversation(id:string):void {
        if(busy||!loaded||id===conversationId)return;
        storeConversation();const record=conversations.find(t=>t.id===id);if(!record)return;
        resetConversation();conversationId=id;messages=record.messages;citations=record.citations||[];restoreTasks(record.taskContext);save();
    }
    function deleteConversation(id:string):void {
        if(busy||!loaded)return;
        conversations=conversations.filter(t=>t.id!==id);purgeCache=true;
        if(id===conversationId){resetConversation();const next=conversations[conversations.length-1];conversationId=next?.id||Date.now().toString(36)+"-"+(++sequence);messages=next?.messages||[];citations=next?.citations||[];restoreTasks(next?.taskContext);}
        save();
    }
    function flushStream():void {
        if(!streamedText)return;
        if(!streamId){const message=turn("assistant",streamedText);streamId=message.id;messages=messages.concat([message]).slice(-16);}
        else messages=messages.map(m=>m.id===streamId?Object.assign({},m,{text:streamedText}):m);
    }
    function recordFailure(text:string):void {
        error=text;phase="error";
        const last=messages[messages.length-1];
        if(!last?.failed||last.text!==text)messages=messages.concat([Object.assign(turn("assistant",text),{failed:true})]).slice(-16);
    }
    function saveMemory(value: string): void {
        if(Preferences.preview||memoryWriter.running)return;
        memoryError="";memory=value.slice(0,6000);pendingMemory=memory;memoryWriter.running=true;
    }
    function attach(path: string): void {if(attachments.length<3&&!attachments.includes(path))attachments=attachments.concat([path]);}
    function detach(index: int): void {attachments=attachments.filter((_,i)=>i!==index);}
    function shareClipboard(): void {if(!clipboard.running)clipboard.running=true;}
    function mark(index: int,status: string): void {
        proposals=proposals.map((p,i)=>i===index?Object.assign({},p,{status}):p);
        recentTasks=recentTasks.map(t=>t.key===proposalBatch+":"+index?Object.assign({},t,{status}):t);
        save();
    }
    function rememberTask(index:int):void {
        const action=proposals[index],key=proposalBatch+":"+index;
        recentTasks=recentTasks.filter(t=>t.key!==key).concat([{key,batch:proposalBatch,name:action.name,args:action.args,status:action.status,at:Date.now(),reminderId:action.reminderId||"",expectedUntil:action.expectedUntil||0}]).slice(-8);
    }
    function dismiss(index: int): void {if(proposals[index]?.status==="pending")mark(index,"dismissed");}
    function adjust(index:int,value:real):bool {
        const action=proposals[index];
        if(!action||action.status!=="pending"||busy||!Number.isFinite(value)||!["volume","brightness","focus"].includes(action.name))return false;
        const focus=action.name==="focus",amount=Math.round(Math.max(focus?1:0,Math.min(focus?120:100,value)));
        const args=Object.assign({},action.args,{[focus?"minutes":"level"]:amount});
        const label=(focus?"Focus":action.name==="volume"?"Volume":"Brightness")+" · "+amount+(focus?" minutes":"%");
        const next=proposals.slice();next[index]=Object.assign({},action,{args,label});proposals=next;return true;
    }
    function apply(index: int): void {
        if(Preferences.preview||Session.isLocked()||busy)return;
        const action=proposals[index];
        if(!action||action.status!=="pending")return;
        if(action.name==="system_step"){
            if(!Preferences.lumaSystem||typeof action.args?.id!=="string"||!/^[a-f0-9]{32}$/.test(action.args.id))return;
            mark(index,"requested");received=false;error="";autoLocal=false;streamId="";streamedText="";phase="reading";status="Continuing task";
            pendingPayload=JSON.stringify({token:action.args.id,context:context(),accessMode:Preferences.lumaAccess});worker.command=["python3",backend,"resume"];worker.running=true;return;
        }
        const succeeded=perform(action,index);
        mark(index,succeeded?(["reminder","reminder_update"].includes(action.name)?"scheduled":["appearance","awake","peace","reminder_remove"].includes(action.name)?"done":"requested"):"failed");
        rememberTask(index);
        const receipt={at:Date.now()/1000,tool:{name:"desktop_action",purpose:action.label,action_name:action.name,action_args:JSON.stringify(action.args)},result:{ok:succeeded,status:proposals[index].status}};
        execution=execution.concat([receipt]);
        let target=-1;for(let i=messages.length-1;i>=0;i--)if(messages[i].role==="assistant"&&!messages[i].hidden){target=i;break;}
        if(target>=0)messages=messages.map((m,i)=>i===target?Object.assign({},m,{execution:receipts((m.execution||[]).concat([receipt]))}):m);
        else {const answer=turn("assistant",action.label);answer.execution=receipts([receipt]);messages=messages.concat([answer]).slice(-16);}

        if(!proposals.some(p=>p.status==="pending"))phase=proposals.some(p=>p.status==="failed")?"error":"ready";
        messages=messages.concat([turn("assistant",(succeeded?"User approved and requested: ":"Could not request: ")+action.label+". Recheck current desktop state before claiming completion.",true)]).slice(-16);save();
    }
    function perform(action:var,index:int):bool {
        if(Preferences.preview||Session.isLocked()||!action||typeof action.args!=="object")return false;
        const a=action.args;let succeeded=true;
        if(action.name==="appearance"||action.name==="awake"){
            const undo=action.name==="appearance"?{mode:Theme.light?"light":"dark"}:{active:KeepAwake.active,until:KeepAwake.until};
            proposals=proposals.map((p,i)=>i===index?Object.assign({},p,{undo}):p);
        }
        // Proposals are validated in Python. Recheck numeric ranges at the execution boundary.
        if(action.name==="volume"&&typeof a.level==="number"&&a.level>=0&&a.level<=100){succeeded=!!Audio.sink?.audio;if(succeeded)Audio.setVolume(a.level/100);}
        else if(action.name==="brightness"&&typeof a.level==="number"&&a.level>=0&&a.level<=100){succeeded=SystemInfo.brightnessAvailable;if(succeeded)SystemInfo.setBrightness(a.level/100);}
        else if(action.name==="focus"&&Number.isInteger(a.minutes)&&a.minutes>=1&&a.minutes<=120){succeeded=FocusTimer.loaded;if(succeeded)FocusTimer.start(a.minutes,false);}
        else if(action.name==="focus_pause"){succeeded=FocusTimer.loaded&&["running","paused"].includes(FocusTimer.phase);if(succeeded&&(typeof a.paused!=="boolean"||(FocusTimer.phase==="paused")!==a.paused))FocusTimer.pause();}
        else if(action.name==="focus_cancel"){succeeded=FocusTimer.loaded;if(succeeded)FocusTimer.cancel();}
        else if(action.name==="appearance"&&["light","dark"].includes(a.mode)){if(Theme.light!==(a.mode==="light"))Theme.toggleMode();}
        else if(action.name==="awake"&&typeof a.enabled==="boolean"){
            if(a.enabled&&a.seconds)succeeded=KeepAwake.setFor(a.seconds);else KeepAwake.setActive(a.enabled);
            proposals=proposals.map((p,i)=>i===index?Object.assign({},p,{expectedUntil:KeepAwake.until}):p);
        }
        else if(action.name==="peace"&&typeof a.enabled==="boolean")Notifications.dnd=a.enabled;
        else if(action.name==="nightlight"&&typeof a.enabled==="boolean")Display.setNightLight(a.enabled);
        else if(action.name==="media_pause"||action.name==="media_play"){
            const player=a.id?Media.players.find(p=>p.dbusName===a.id):Media.active;
            succeeded=!!player&&(action.name==="media_play"?Media.play(player):Media.pause(player));
        }
        else if(action.name==="media_next"||action.name==="media_previous"){
            const player=a.id?Media.players.find(p=>p.dbusName===a.id):Media.active;
            succeeded=!!player&&(action.name==="media_next"?player.canGoNext:player.canGoPrevious);
            if(succeeded){if(action.name==="media_next")player.next();else player.previous();}
        }
        else if(action.name==="open_app"&&typeof a.id==="string"){const app=Apps.apps.find(app=>app.id===a.id);succeeded=!!app&&!Apps.launching;if(succeeded){CanvasState.close();Apps.launch(app);}}
        else if(action.name==="close_app"&&typeof a.id==="string"){const app=Apps.apps.find(app=>app.id===a.id);succeeded=!!app&&Apps.close(app);}
        else if(action.name==="file_action"&&["compress","merge","export"].includes(a.operation)&&Array.isArray(a.paths)&&a.paths.length>=1&&a.paths.length<=3&&a.paths.every(p=>typeof p==="string")){succeeded=IslandDrop.perform(a.paths,a.operation,a);}
        else if(action.name==="reminder"||action.name==="reminder_update"){
            succeeded=Preferences.remindersEnabled&&Reminders.loaded;
            if(succeeded&&action.name==="reminder_update")succeeded=typeof a.id==="string"&&typeof a.title==="string"&&Number.isFinite(a.dueAt)&&a.dueAt<=Date.now()+365*86400000&&!!Reminders.storeExact(a.title,a.dueAt,a.id);
            else if(succeeded)succeeded=a.dueAt?!!Reminders.storeExact(a.title,a.dueAt):Reminders.store("",a.title,a.date,a.time,a.lead,a.count);
            if(succeeded){const id=Reminders.items[Reminders.items.length-1].id;proposals=proposals.map((p,i)=>i===index?Object.assign({},p,{reminderId:id}):p);}
        }
        else if(action.name==="reminder_remove"){
            succeeded=Reminders.loaded&&typeof a.id==="string"&&Reminders.items.some(r=>r.id===a.id&&!r.done);
            if(succeeded)Reminders.remove(a.id);
        }
        else if(action.name==="open_panel"&&["settings","quicksettings","calendar","themes","wallpapers","wifi","bluetooth","display","sound","media","notifhistory","focus","performance"].includes(a.panel)){CanvasState.close();IslandState.openMenu(a.panel);}
        else succeeded=false;
        return succeeded;
    }
    function undoReminder(index:int):void {const p=proposals[index];if(p?.name!=="reminder"||!p.reminderId||p.status!=="scheduled"||Preferences.preview||Session.isLocked())return;Reminders.remove(p.reminderId);mark(index,"dismissed");}
    function canUndo(index:int):bool {
        const p=proposals[index];if(!p)return false;
        if(p.reminderId)return p.name==="reminder"&&p.status==="scheduled"&&Reminders.items.some(r=>r.id===p.reminderId&&!r.done&&!r.delivered.length);
        if(p.name==="appearance")return p.status==="done"&&!!p.undo&&Theme.light===(p.args.mode==="light");
        if(p.name==="awake")return p.status==="done"&&!!p.undo&&KeepAwake.active===p.args.enabled&&KeepAwake.until===p.expectedUntil;
        return false;
    }
    function undoAction(index:int):void {
        const p=proposals[index];if(!canUndo(index)||Preferences.preview||Session.isLocked()||busy)return;
        if(p.reminderId){undoReminder(index);return;}
        if(p.name==="appearance"&&p.status==="done"&&p.undo&&Theme.light===(p.args.mode==="light")){Theme.setMode(p.undo.mode);mark(index,"undone");}
        else if(p.name==="awake"&&p.status==="done"&&p.undo&&KeepAwake.active===p.args.enabled&&KeepAwake.until===p.expectedUntil){if(p.undo.active&&p.undo.until>Date.now())KeepAwake.setFor((p.undo.until-Date.now())/1000);else KeepAwake.setActive(p.undo.active&&!p.undo.until);mark(index,"undone");}
    }
    function receive(data:var):void {
        if(data.event==="text"){root.streamedText=data.text||"";root.phase="composing";root.status="Writing";if(!streamFlush.running)streamFlush.start();}
        else if(data.event==="window_context"){root.currentWindow=data.window;}
        else if(data.event==="phase"){root.phase=data.phase;root.status=data.text;}
        else if(data.event==="usage"){root.requestCount=data.requests||0;}
        else if(data.event==="intent"){root.intent=data.intent||"auto";}
        else if(data.event==="task"){root.taskToken=data.token||"";root.save();}
        else if(data.event==="execution"){
            root.execution=data.execution||[];
            if(data.token)root.taskToken=data.token;
            const last=root.execution.slice(-1)[0];
            if(last){
                const summary="Observed task steps: "+JSON.stringify(root.receipts(root.execution).map(e=>({tool:e.tool.name,purpose:e.tool.purpose,ok:e.result.ok,status:e.result.status,error:e.result.error,path:e.result.path,exitCode:e.result.exitCode})));
                const index=root.messages.findIndex(m=>m.receiptBatch===root.taskToken&&m.hidden);
                const receipt=root.turn("assistant",summary,true);receipt.receiptBatch=root.taskToken;
                root.messages=index>=0?root.messages.map((m,i)=>i===index?receipt:m):root.messages.concat([receipt]).slice(-16);root.save();
            }
        }
        else if(data.event==="answer"){
            streamFlush.stop();root.received=true;root.requestCount=data.cached?0:data.requests??root.requestCount;
            if(root.streamId)root.messages=root.messages.map(m=>m.id===root.streamId?Object.assign({},m,{text:data.text,presentation:data.presentation||{},citations:data.citations||[],execution:root.receipts(data.execution||root.execution)}):m);
            else if(data.text){const answer=root.turn("assistant",data.text,data.localTask===true,data.presentation,data.citations);answer.execution=root.receipts(data.execution||root.execution);root.messages=root.messages.concat([answer]).slice(-16);}
            root.streamedText="";if(data.model)root.retryAt=0;
            root.proposals=data.actions||[];root.citations=data.citations||[];root.fileResults=data.files||[];root.liveMetrics=data.liveMetrics===true;if(data.execution)root.execution=data.execution;root.router=data.router||"";root.intent=data.intent||root.intent;root.answerModel=data.model??Preferences.searchAiModel;
            root.pendingTask=data.pendingTask||null;root.taskExpires=root.pendingTask?Date.now()+120000:0;
            root.autoLocal=(data.localTask===true||Preferences.lumaAccess==="full")&&root.proposals.length>0&&root.proposals.length<=4&&root.proposals.every(p=>["reminder","reminder_update","reminder_remove","appearance","awake","peace","nightlight","volume","brightness","focus","focus_pause","focus_cancel","media_pause","media_play","media_next","media_previous","open_app","close_app","open_panel"].includes(p.name));
            root.phase=root.proposals.length?"review":"ready";root.status="";root.save();root.answered();
            if(!CanvasState.opened&&!Session.isLocked())Context.show("luma","Luma ready","luma",0);
        } else if(data.event==="error"){streamFlush.stop();root.flushStream();root.streamedText="";root.received=true;root.recordFailure(data.text||"Could not complete request");root.retryAt=data.retryAt||0;root.status="";root.save();}
    }
    Process {
        id: worker;command:["python3",root.backend,"chat"];stdinEnabled:true
        onStarted:{write(root.pendingPayload+"\n");root.pendingPayload="";}
        stdout:SplitParser {onRead:line=>{
            if(root.cancelPending)return;
            try{root.receive(JSON.parse(line));}catch(e){root.error="Could not read assistant response";root.phase="error";}
        }}
        onExited:code=>{root.cancelPending=false;if(!root.received){streamFlush.stop();root.flushStream();root.streamedText="";root.recordFailure("Assistant stopped before answering.");root.save();}root.status="";
            if(root.autoLocal){const expected=root.proposals[0];Qt.callLater(()=>{
                if(root.proposals[0]!==expected){root.autoLocal=false;return;}
                for(let i=0;i<root.proposals.length;i++)root.apply(i);root.autoLocal=false;
                if(root.proposals.some(p=>p.status==="failed")){root.error=Reminders.error||"Couldn’t apply part of this request. Check the device or feature availability.";root.phase="error";}
            });}
            root.refreshUsage();}
    }
    Timer {id:streamFlush;interval:70;onTriggered:root.flushStream()}
    onRetryAtChanged:retryNow=Date.now()
    Timer {interval:1000;repeat:true;running:root.retryAt>root.retryNow/1000;onTriggered:root.retryNow=Date.now()}
    Timer {interval:8000;repeat:true;running:root.busy&&!CanvasState.opened&&!Session.isLocked()&&!IslandState.menuOpen&&!IslandState.settingsOpen;onTriggered:Context.show("luma","Luma","luma",0)}
    Timer {id:saveDelay;interval:80;onTriggered:{if(saver.running){restart();return;}saver.command=["python3",root.backend,root.clearing?"clear":"save"];saver.payload=root.pendingSave;root.pendingSave="";root.clearing=false;saver.running=true;}}
    Process {id:saver;property string payload:"";stdinEnabled:true;onExited:code=>{if(code!==0)root.error="Could not save conversation on this PC.";}onStarted:if(command[2]==="save"){write(payload+"\n");payload="";}}
    Process {id:memoryWriter;onExited:code=>{if(code!==0)root.memoryError="Could not save personal notes on this PC.";}command:["python3",root.backend,"memory"];stdinEnabled:true;onStarted:{write(JSON.stringify(root.pendingMemory)+"\n");root.pendingMemory="";}}
    Process {id:clipboard;command:["python3","-c","import subprocess,sys; p=subprocess.run(['wl-paste','--type','text','--no-newline'],capture_output=True,timeout=3); sys.stdout.buffer.write(p.stdout[:16000])"]
        stdout:StdioCollector {onStreamFinished:root.sharedText=text}
    }
    Process {id:usageReader;command:["python3",root.backend,"usage"];running:!Preferences.preview;stdout:StdioCollector {onStreamFinished:{try{root.usage=JSON.parse(text);}catch(e){}}}}
    Process {command:["python3",root.backend,"state"];running:!Preferences.preview
        stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);root.messages=Preferences.lumaRemember?d.messages||[]:[];root.conversations=Preferences.lumaRemember?d.threads||[]:[];root.conversationId=d.active||"";root.citations=Preferences.lumaRemember?d.citations||[]:[];if(Preferences.lumaRemember)root.restoreTasks(d.taskContext);root.memory=d.memory||"";}catch(e){root.error="Could not restore conversation";}root.loaded=true;}}
    }
    Connections {target:Preferences;function onLumaRememberChanged(){if(!Preferences.lumaRemember){root.clearing=true;root.pendingSave="";saveDelay.restart();}}}
    Connections {target:KeepAwake;function onErrorChanged(){if(KeepAwake.error&&root.proposals.some(p=>p.name==="awake"&&p.status==="done")){root.proposals=root.proposals.map(p=>p.name==="awake"?Object.assign({},p,{status:"failed"}):p);root.error=KeepAwake.error;root.phase="error";}}}
    Connections {target:Reminders;function onErrorChanged(){if(Reminders.error&&root.proposals.some(p=>p.name==="reminder"&&p.status==="scheduled")){root.error="Reminder is active, but could not be saved: "+Reminders.error;root.phase="error";}}}
    Connections {target:Session;function onLockedChanged(){if(Session.locked&&root.busy)root.cancel();}}
    Connections {target:Apps;function onClosed(appId:string,succeeded:bool,status:string){
        const index=root.proposals.findIndex(p=>p.name==="close_app"&&p.args?.id===appId&&p.status==="requested");
        if(index>=0){root.mark(index,!succeeded?"failed":status==="closed"?"done":"requested");if(!succeeded)root.recordFailure(Apps.error||"No matching application window");}
    }}
}
