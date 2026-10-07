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
    property string focusDate:""
    property bool drafting:false
    property bool calendarExpanded:false
    property bool calendarEditing:false
    function compose():void {focusDate=Dates.key(Time.date);drafting=true;IslandState.openMenu("calendar");}
    property string checkedMinute:""
    readonly property bool busy:writer.running||saveDelay.running
    readonly property string script:Qt.resolvedUrl("../scripts/reminders.py").toString().replace("file://","")
    readonly property real nextExact:items.filter(r=>!r.done&&r.at&&!r.delivered.includes(r.date)).reduce((next,r)=>Math.min(next,r.at),Infinity)
    function storeExact(title,at,id) {
        id=id||"";
        if(!Number.isFinite(at)||at<=Date.now())return "";
        if(id&&!items.some(r=>r.id===id&&!r.done))return "";
        const due=new Date(at);
        if(!store(id,title,Dates.key(due),Qt.formatDateTime(due,"HH:mm"),0,1))return "";
        const entry=items[items.length-1];
        items=items.map(r=>r.id===entry.id?Object.assign({},r,{at,delivered:[]}):r);save();return entry.id;
    }
    function forDate(day:string):var {return items.filter(r=>r.date===day).sort((a,b)=>Number(a.done)-Number(b.done)||a.time.localeCompare(b.time));}
    function hasDate(day:string):bool {return items.some(r=>r.date===day&&!r.done);}
    function schedule(entry):var {return Dates.schedule(entry);}
    function save():void {if(!Preferences.preview&&loaded)saveDelay.restart();}
    function store(id:string,title:string,day:string,time:string,lead:int,count:int):bool {
        if(!loaded||Preferences.preview||Session.isLocked())return false;
        title=title.trim();
        if(!title||title.length>160){error="Add a title of up to 160 characters.";return false;}
        if(!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(time)){error="Use a time such as 09:00 or 18:30.";return false;}
        if(!id&&day<Dates.key(Time.date)){error="Choose today or a future date.";return false;}
        if(!id&&items.length>=256){error="Remove an old reminder before adding another.";return false;}
        const old=items.find(r=>r.id===id);
        const same=old&&old.date===day&&old.time===time&&old.lead===lead&&old.count===count;
        const next={id:id||Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,9),title,date:day,time,lead:Math.max(0,Math.min(30,lead)),count:Math.max(1,Math.min(lead+1,count)),done:old?.done||false,delivered:same?old.delivered:[]};
        items=items.filter(r=>r.id!==next.id).concat([next]);if(old)for(const n of Notifications.list.filter(n=>n.reminderId===id))Notifications.close(n);error="";save();checkedMinute="";Qt.callLater(check);return true;
    }
    function complete(id:string,done:bool):void {if(!loaded||Preferences.preview||Session.isLocked())return;items=items.map(r=>r.id===id?Object.assign({},r,{done}):r);save();if(done)for(const n of Notifications.list.filter(n=>n.reminderId===id))Notifications.close(n);}
    function remove(id:string):void {if(!loaded||Preferences.preview||Session.isLocked())return;items=items.filter(r=>r.id!==id);save();for(const n of Notifications.list.filter(n=>n.reminderId===id))Notifications.close(n);}
    function open(entry):void {focusDate=entry.date;IslandState.openMenu("calendar");calendarExpanded=true;}
    function check():void {
        if(!loaded||Preferences.preview||!Preferences.remindersEnabled)return;
        const now=Date.now(),notify=[];
        const minute=Qt.formatDateTime(Time.date,"yyyy-MM-dd HH:mm");if(minute===checkedMinute&&nextExact>now)return;checkedMinute=minute;
        const next=items.map(r=>{
            if(r.done)return r;
            const due=Dates.schedule(r).filter(day=>(r.at&&day===r.date?r.at:Dates.timestamp(day,r.time))<=now&&!r.delivered.includes(day));
            if(!due.length)return r;
            notify.push(r);
            return Object.assign({},r,{delivered:r.delivered.concat(due)});
        });
        if(!notify.length)return;
        items=next;save();
        // After sleep/login, one current notice per reminder replaces missed repeats.
        for(const r of notify){const day=Dates.parse(r.date);Notifications.remind(r.id,r.title,Qt.formatDateTime(day,"ddd, d MMM yyyy"),()=>root.open(r),()=>root.complete(r.id,true));}
    }
    Connections {target:Time;function onDateChanged(){root.check();}}
    Timer {
        interval:{const minute=Time.date;return Math.max(1,Math.min(60000,root.nextExact-Date.now()));}
        repeat:true;running:root.loaded&&!Preferences.preview&&Preferences.remindersEnabled&&Number.isFinite(root.nextExact)
        onTriggered:root.check()
    }
    Connections {target:Preferences;function onRemindersEnabledChanged(){root.checkedMinute="";root.check();}}
    Timer {id:saveDelay;interval:100;onTriggered:{if(writer.running){restart();return;}writer.command=["python3",root.script,JSON.stringify({version:1,items:root.items})];writer.running=true;}}
    Process {id:writer;stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);root.error=d.ok?"":d.error;}catch(e){root.error="Could not save reminders.";}}}}
    Process {running:!Preferences.preview;command:["python3",root.script];stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);if(d.ok){root.items=d.items;root.loaded=true;root.check();}else root.error=d.error;}catch(e){root.error="Could not read reminders.";}}}}
}
