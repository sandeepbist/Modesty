pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "Calendar.js" as Dates
Singleton {
    id:root
    property var items:[]
    property bool loaded:Preferences.preview
    property string error:""
    property int revision:0
    readonly property int acknowledgedRevision:revision
    property string zone:"UTC"
    property var receipts:({})
    property var operations:({})
    property var queue:[]
    property var current:null
    property var result:null
    property string focusDate:""
    property bool drafting:false
    property bool calendarExpanded:false
    property bool calendarEditing:false
    property string checkedMinute:""
    readonly property bool busy:writer.running||current!==null||queue.length>0
    readonly property string script:Qt.resolvedUrl("../scripts/reminders.py").toString().replace("file://","")
    readonly property real nextExact:items.filter(r=>!r.done&&r.at&&(r.repeat?.kind!=="none"||!r.delivered.includes(r.date))).reduce((next,r)=>Math.min(next,r.at),Infinity)
    function compose():void {focusDate=Dates.key(Time.date);drafting=true;IslandState.openMenu("calendar");}
    function read(id:string):var {
        if(Session.isLocked())return {ok:false,reminder:null,revision:0,error:"Unlock before reading reminders."};
        const reminder=items.find(r=>r.id===id);
        return {ok:loaded&&!!reminder,reminder:reminder||null,revision:reminder?.revision||0,error:!loaded?error:reminder?"":"Reminder no longer exists."};
    }
    function receipt(ticket:string):var {return receipts[ticket]||{status:"refused",error:"Unknown reminder request."};}
    function remember(ticket,value):void {const updated=Object.assign({},receipts);updated[ticket]=value;receipts=updated;const keys=Object.keys(receipts);if(keys.length>128){const next=Object.assign({},receipts);delete next[keys[0]];receipts=next;}}
    function canonical(value):string {
        if(Array.isArray(value))return "["+value.map(canonical).join(",")+"]";
        if(value&&typeof value==="object")return "{"+Object.keys(value).sort().map(key=>JSON.stringify(key)+":"+canonical(value[key])).join(",")+"}";
        return JSON.stringify(value);
    }
    function request(command,operationId):var {
        operationId=operationId||"";
        if(typeof operationId!=="string"||operationId.length>160)return {ok:false,status:"refused",error:"Invalid operation id."};
        if(!loaded||Preferences.preview||Session.isLocked())return {ok:false,status:"refused",error:Session.isLocked()?"Unlock before changing reminders.":error||"Reminders are unavailable."};
        const signature=canonical(command);
        if(operationId&&Object.prototype.hasOwnProperty.call(operations,operationId)){const previous=operations[operationId];if(previous.signature!==signature)return {ok:false,status:"refused",error:"Operation id already used for a different reminder command."};return Object.assign({ok:true,ticket:previous.ticket},receipt(previous.ticket));}
        if(!command||!["create","update","complete","remove"].includes(command.kind))return {ok:false,status:"refused",error:"Invalid reminder command."};
        command=Object.assign({},command);
        if(command.kind!=="create"&&!operationId&&!items.some(r=>r.id===command.id))return {ok:false,status:"refused",error:"Reminder no longer exists."};
        if(["create","update"].includes(command.kind)){
            if(command.title!==undefined&&(typeof command.title!=="string"||!command.title.trim()||command.title.trim().length>160)){error="Add a title of up to 160 characters.";return {ok:false,status:"refused",error};}
            if(command.dueAt!==undefined&&(!Number.isFinite(command.dueAt)||command.dueAt<=0||(!operationId&&command.dueAt<=Date.now()))){error="Choose a future time.";return {ok:false,status:"refused",error};}
            if(command.time!==undefined&&!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(command.time)){error="Use a time such as 09:00 or 18:30.";return {ok:false,status:"refused",error};}
            if(command.date!==undefined&&(!/^\d{4}-\d{2}-\d{2}$/.test(command.date)||Dates.key(Dates.parse(command.date))!==command.date)){error="Choose a valid date.";return {ok:false,status:"refused",error};}
        }
        const id=command.id||Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,9);
        if(command.kind==="create"&&!command.id){command.id=id;command.generatedId=true;}
        const ticket="reminder-"+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,9);
        command.operationId=operationId||ticket;
        const value={status:"pending",id,revision:0,error:""};
        remember(ticket,value);if(operationId){const updated=Object.assign(Object.create(null),operations);updated[operationId]={ticket,signature};operations=updated;}
        error="";queue=queue.concat([{ticket,command}]);Qt.callLater(pump);
        return Object.assign({ok:true,ticket},value);
    }
    function storeExact(title,at,id,repeat,requestedZone) {
        id=id||"";
        const command={kind:id?"update":"create",id,title,dueAt:at};if(repeat)command.repeat=repeat;if(requestedZone)command.zone=requestedZone;
        if(id)command.expectedRevision=read(id).revision;
        const value=request(command);
        return value.ok?value.id:"";
    }
    function store(id,title,day,time,lead,count,repeat,requestedZone):bool {
        if(!id&&day<Dates.key(Time.date)){error="Choose today or a future date.";return false;}
        const command={kind:id?"update":"create",id,title,date:day,time,lead:Math.max(0,Math.min(30,lead)),count:Math.max(1,Math.min(lead+1,count))};if(repeat)command.repeat=repeat;if(requestedZone)command.zone=requestedZone;
        if(id)command.expectedRevision=read(id).revision;
        const value=request(command);
        return value.ok;
    }
    function complete(id,done,occurrenceKey,expectedRevision):void {const command={kind:"complete",id,done,expectedRevision:expectedRevision??read(id).revision};if(occurrenceKey)command.occurrenceKey=occurrenceKey;request(command);}
    function remove(id:string,expectedRevision:var):void {request({kind:"remove",id,expectedRevision:expectedRevision??read(id).revision});}
    function forDate(day:string):var {return items.filter(r=>Dates.occurs(r,day)).map(r=>r.date===day?r:Object.assign({},r,{date:day,at:0,projected:true})).sort((a,b)=>Number(a.done)-Number(b.done)||a.time.localeCompare(b.time));}
    function hasDate(day:string):bool {return items.some(r=>!r.done&&Dates.occurs(r,day));}
    function schedule(entry):var {return Dates.schedule(entry);}
    function open(entry):void {focusDate=items.find(r=>r.id===entry.id)?.date||entry.date;IslandState.openMenu("calendar");calendarExpanded=true;}
    function pump():void {
        if(writer.running||current!==null||!queue.length)return;
        current=queue[0];queue=queue.slice(1);result=null;writer.running=true;
    }
    function adopt(data):void {
        items=data.items;revision=data.revision||0;zone=data.zone||zone;loaded=true;
        if(current?.ticket)remember(current.ticket,data.receipt||{status:"persisted",id:current.command.id||"",revision,error:""});
        if(["update","complete","remove"].includes(current?.command.kind))for(const n of Notifications.list.filter(n=>n.reminderId===current.command.id))Notifications.close(n);
        for(const notice of data.notices||[]){const entry=notice;Notifications.remind(entry.id,entry.title,Qt.formatDateTime(Dates.parse(entry.date),"ddd, d MMM yyyy"),()=>root.open(entry),()=>root.complete(entry.id,true,entry.occurrenceKey));}
    }
    function check():void {
        if(!loaded||Preferences.preview||!Preferences.remindersEnabled||queue.some(job=>job.command.kind==="check")||current?.command.kind==="check")return;
        const minute=Qt.formatDateTime(Time.date,"yyyy-MM-dd HH:mm");
        if(minute===checkedMinute&&nextExact>Date.now())return;
        checkedMinute=minute;queue=queue.concat([{ticket:"",command:{kind:"check"}}]);Qt.callLater(pump);
    }
    function retry():void {if(!loaded){queue=queue.concat([{ticket:"",command:{kind:"load"}}]);Qt.callLater(pump);}else error="";}
    Connections {target:Time;function onDateChanged(){root.check();}}
    Connections {target:Preferences;function onRemindersEnabledChanged(){root.checkedMinute="";root.check();}}
    Timer {interval:Math.max(1000,Math.min(60000,root.nextExact-Date.now()));repeat:true;running:root.loaded&&!Preferences.preview&&Preferences.remindersEnabled&&Number.isFinite(root.nextExact);onTriggered:root.check()}
    Process {
        id:writer;command:["python3",root.script,"--stdin"];stdinEnabled:true
        onStarted:write(JSON.stringify(root.current.command)+"\n")
        stdout:StdioCollector {onStreamFinished:{try{root.result=JSON.parse(text);}catch(e){root.result={ok:false,status:"failed",error:"Could not read reminder response."};}}}
        onExited:code=>{
            const kind=root.current?.command.kind;
            const data=root.result||{ok:false,status:"failed",error:"Could not save reminders."};
            if(data.ok){root.error="";root.adopt(data);}else{root.error=data.error||"Could not save reminders.";if(root.current?.ticket)root.remember(root.current.ticket,data.receipt||{status:data.status||"failed",id:root.current.command.id||"",revision:data.revision||0,error:root.error});if(data.items){root.items=data.items;root.revision=data.revision||0;}}
            root.current=null;root.result=null;Qt.callLater(root.pump);
            if(data.ok&&kind!=="check"){root.checkedMinute="";Qt.callLater(root.check);}
        }
    }
    IpcHandler {
        target:"reminders"
        function read(id:string):string {return JSON.stringify(Session.isLocked()?{ok:false,error:"Unlock before reading reminders."}:root.read(id));}
        function receipt(ticket:string):string {return JSON.stringify(Session.isLocked()?{status:"refused",error:"Unlock before reading reminder receipts."}:root.receipt(ticket));}
        function status():string {return JSON.stringify({loaded:root.loaded,busy:root.busy,revision:root.revision,acknowledgedRevision:root.acknowledgedRevision,error:root.error,count:Session.isLocked()?0:root.items.length});}
        function request(command:string,operationId:string):string {try{return JSON.stringify(root.request(JSON.parse(command),operationId));}catch(e){return JSON.stringify({ok:false,status:"refused",error:"Invalid reminder command."});}}
    }
    Component.onCompleted:if(!Preferences.preview){queue=[{ticket:"",command:{kind:"load"}}];Qt.callLater(pump);}
}
