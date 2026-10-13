#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import tempfile
from qml import run as run_ui

ROOT = Path(__file__).resolve().parents[1]
STUBS = {
    'Preferences': 'property bool preview:false;property bool remindersEnabled:true',
    'Time': 'property date date:new Date()',
    'Session': 'property bool locked:false;function isLocked():bool {return locked;}',
    'IslandState': 'function openMenu(name):void {}',
    'Notifications': '''property var list:[];property int delivered:0
        function remind(id,title,body,open,complete):void {delivered++;list=list.concat([{reminderId:id,title,open,complete}]);}
        function close(notice):void {list=list.filter(n=>n!==notice);}''',
}
SOURCE = '''import QtQuick
import Quickshell
import qs.services
ShellRoot {
    property int phase:0
    property string ticket:""
    property string secondTicket:""
    property string monthly:""
    property string recurring:""
    property string deliveredKey:""
    property string nextDate:""
    property double deadline:Date.now()+12000
    function check(value,label):void {if(!value)throw new Error(label+" phase="+phase+" error="+Reminders.error);}
    function pending(command,operation):var {const result=Reminders.request(command,operation||"");check(result.ok,"Request refused");return result;}
    Timer {interval:30;running:true;repeat:true;onTriggered:{try {
        check(Date.now()<deadline,"Timed out");
        if(phase===0&&Reminders.loaded&&!Reminders.busy){
            check(Reminders.items.length===0,"Initial storage");
            const result=pending({kind:"create",title:"Monthly",date:"2099-01-31",time:"09:00",repeat:{kind:"monthly",anchorDay:31},zone:"UTC"},"monthly-create");monthly=result.id;ticket=result.ticket;phase=1;
        }else if(phase===1&&Reminders.receipt(ticket).status!=="pending"&&!Reminders.busy){
            check(Reminders.receipt(ticket).status==="persisted","Durable creation");
            Session.locked=true;check(!Reminders.read(monthly).ok&&!Reminders.request({kind:"remove",id:monthly}).ok,"Locked reads or mutations accepted");Session.locked=false;
            check(Reminders.acknowledgedRevision===Reminders.revision&&Reminders.revision>0,"Observed store revision");
            check(Reminders.hasDate("2099-02-28")&&Reminders.hasDate("2099-03-31"),"Recurring calendar dots");
            check(Reminders.forDate("2099-02-28")[0].date==="2099-02-28","Recurring agenda projection");
            const again=pending({zone:"UTC",repeat:{anchorDay:31,kind:"monthly"},time:"09:00",date:"2099-01-31",title:"Monthly",kind:"create"},"monthly-create");check(again.ticket===ticket,"Idempotent QML replay");
            check(!Reminders.request({kind:"create",title:"Different"},"monthly-create").ok,"Operation payload mismatch");
            ticket=pending({kind:"update",id:monthly,title:"First edit"}).ticket;
            secondTicket=pending({kind:"update",id:monthly,title:"Latest edit"}).ticket;phase=2;
        }else if(phase===2&&Reminders.receipt(secondTicket).status!=="pending"&&!Reminders.busy){
            check(Reminders.receipt(ticket).status==="persisted"&&Reminders.receipt(secondTicket).status==="persisted","Serialized write receipts");
            check(Reminders.read(monthly).reminder.title==="Latest edit","Acknowledgment replaced newer edit");
            const old=Reminders.read(monthly).revision;
            ticket=pending({kind:"update",id:monthly,title:"Winner",expectedRevision:old}).ticket;
            secondTicket=pending({kind:"update",id:monthly,title:"Stale",expectedRevision:old}).ticket;phase=3;
        }else if(phase===3&&Reminders.receipt(secondTicket).status!=="pending"&&!Reminders.busy){
            check(Reminders.receipt(ticket).status==="persisted"&&Reminders.receipt(secondTicket).status==="conflict","Revision conflict");
            check(Reminders.read(monthly).reminder.title==="Winner","Conflict overwrote reminder");
            const past=new Date(Date.now()-10*86400000).toISOString().slice(0,10);
            const result=pending({kind:"create",title:"Daily resume",date:past,time:"00:00",repeat:{kind:"daily"},zone:"UTC"});recurring=result.id;ticket=result.ticket;phase=4;
        }else if(phase===4&&Reminders.receipt(ticket).status!=="pending"&&!Reminders.busy){
            const entry=Reminders.read(recurring).reminder;
            check(Notifications.delivered===1,"Missed recurrence did not coalesce");
            check(entry.lastDeliveryKey&&entry.at>Date.now(),"Next occurrence not durable");
            deliveredKey=entry.lastDeliveryKey;nextDate=entry.date;
            Reminders.checkedMinute="";Reminders.check();
            Notifications.list.find(n=>n.reminderId===recurring).complete();
            const job=Reminders.queue.slice(-1)[0];
            check(job.command.expectedRevision===entry.revision,"Notification used revision before delivery");
            ticket=job.ticket;phase=5;
        }else if(phase===5&&Reminders.receipt(ticket).status!=="pending"&&!Reminders.busy){
            check(Notifications.delivered===1,"Replay repeated delivery");
            check(Reminders.read(recurring).reminder.date===nextDate,"Complete skipped next pending occurrence");
            check(Reminders.read(recurring).reminder.lastCompletionKey===deliveredKey,"Completion key missing");
            ticket=pending({kind:"complete",id:recurring,occurrenceKey:deliveredKey}).ticket;phase=6;
        }else if(phase===6&&Reminders.receipt(ticket).status!=="pending"&&!Reminders.busy){
            check(Reminders.read(recurring).reminder.date===nextDate,"Duplicate complete advanced series");
            ticket=pending({kind:"remove",id:monthly},"monthly-remove").ticket;phase=7;
        }else if(phase===7&&Reminders.receipt(ticket).status!=="pending"&&!Reminders.busy){
            check(!Reminders.read(monthly).ok&&!Reminders.forDate("2099-02-28").some(r=>r.id===monthly),"Remove left calendar series");
            console.log("PASS reminder QML persisted receipts, queued edits, conflict, calendar projection, resume, completion, removal");Qt.quit();
        }
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

with tempfile.TemporaryDirectory(prefix='modesty-reminders-qml-') as directory:
    workspace = Path(directory)
    services = workspace/'services'
    services.mkdir()
    for name in ('Reminders.qml', 'Calendar.js'):
        (services/name).symlink_to(ROOT/'services'/name)
    for name, body in STUBS.items():
        (services/f'{name}.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject {\n'+body+'\n}\n')
    (workspace/'scripts').symlink_to(ROOT/'scripts', target_is_directory=True)
    environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software', MODESTY_PREVIEW='1',
                       XDG_STATE_HOME=str(workspace/'state'), XDG_CACHE_HOME=str(workspace/'cache'), TZ='UTC')
    def run(source, marker):
        (workspace/'shell.qml').write_text(source)
        result = subprocess.run(['quickshell','--no-color','-p',str(workspace)],env=environment,capture_output=True,text=True,timeout=16)
        output = result.stdout+result.stderr
        assert result.returncode == 0 and marker in output and not any(value in output for value in ('ERROR:', 'ReferenceError', 'TypeError')), output
        print(marker)
    run(SOURCE, 'PASS reminder QML persisted receipts, queued edits, conflict, calendar projection, resume, completion, removal')
    path = workspace/'state/modesty/reminders.json'
    persisted = json.loads(path.read_text())
    assert len(persisted['items']) == 1 and persisted['items'][0]['lastCompletionKey'] == persisted['items'][0]['lastDeliveryKey']
    run('''import QtQuick
import Quickshell
import qs.services
ShellRoot {
    property int phase:0
    property string guardedId:""
    property string ticket:""
    property string secondTicket:""
    property string thirdTicket:""
    property int capturedRevision:0
    property double deadline:Date.now()+12000
    function check(ok,label):void {if(!ok)throw new Error(label+" phase="+phase+" error="+Reminders.error);}
    function lastTicket():string {return Reminders.queue.slice(-1)[0].ticket;}
    Timer {interval:30;running:true;repeat:true;onTriggered:{try {
        check(Date.now()<deadline,"Snapshot mutation timeout");
        if(!Reminders.loaded||Reminders.busy)return;
        if(phase===0){
            const created=Reminders.request({kind:"create",title:"Original",date:"2099-05-01",time:"09:00",zone:"UTC"});
            guardedId=created.id;ticket=created.ticket;phase=1;
        }else if(phase===1){
            capturedRevision=Reminders.read(guardedId).revision;
            ticket=Reminders.request({kind:"update",id:guardedId,title:"Winner",expectedRevision:capturedRevision}).ticket;
            Reminders.complete(guardedId,true);secondTicket=lastTicket();phase=2;
        }else if(phase===2){
            check(Reminders.receipt(ticket).status==="persisted"&&Reminders.receipt(secondTicket).status==="conflict","Stale completion accepted");
            check(Reminders.read(guardedId).reminder.title==="Winner"&&!Reminders.read(guardedId).reminder.done,"Stale completion changed winner");
            Reminders.complete(guardedId,true,undefined,capturedRevision);ticket=lastTicket();phase=3;
        }else if(phase===3){
            check(Reminders.receipt(ticket).status==="conflict"&&!Reminders.read(guardedId).reminder.done,"Captured calendar revision replaced with newer snapshot");
            Reminders.complete(guardedId,true);ticket=lastTicket();phase=4;
        }else if(phase===4){
            check(Reminders.receipt(ticket).status==="persisted"&&Reminders.read(guardedId).reminder.done,"Fresh completion refused");
            ticket=Reminders.request({kind:"update",id:guardedId,title:"Remove winner",expectedRevision:Reminders.read(guardedId).revision}).ticket;
            Reminders.remove(guardedId);secondTicket=lastTicket();phase=5;
        }else if(phase===5){
            check(Reminders.receipt(ticket).status==="persisted"&&Reminders.receipt(secondTicket).status==="conflict","Stale removal accepted");
            check(Reminders.read(guardedId).reminder.title==="Remove winner"&&Reminders.read(guardedId).reminder.done,"Stale removal deleted winner");
            ticket=Reminders.request({kind:"update",id:guardedId,title:"Helper winner",expectedRevision:Reminders.read(guardedId).revision}).ticket;
            check(Reminders.store(guardedId,"Unsafe store","2099-05-01","09:00",0,1),"Store helper refused request");secondTicket=lastTicket();
            check(Reminders.storeExact("Unsafe exact",new Date("2099-05-01T09:00:00Z").getTime(),guardedId),"Exact helper refused request");thirdTicket=lastTicket();phase=6;
        }else if(phase===6){
            check(Reminders.receipt(ticket).status==="persisted"&&Reminders.receipt(secondTicket).status==="conflict"&&Reminders.receipt(thirdTicket).status==="conflict","Stale helper update accepted");
            check(Reminders.read(guardedId).reminder.title==="Helper winner","Helper overwrote winner");
            Reminders.remove(guardedId);ticket=lastTicket();phase=7;
        }else {
            check(Reminders.receipt(ticket).status==="persisted"&&!Reminders.read(guardedId).ok,"Fresh removal refused");
            console.log("PASS reminder QML snapshot guards preserve concurrent winners and accept fresh actions");Qt.quit();
        }
    }catch(error){console.error(error);Qt.exit(1);}}}
}''', 'PASS reminder QML snapshot guards preserve concurrent winners and accept fresh actions')
    persisted = json.loads(path.read_text())
    run('''import QtQuick
import Quickshell
import qs.services
ShellRoot {
    property string ticket:""
    property int phase:0
    property string removedId:""
    Timer {interval:30;running:true;repeat:true;onTriggered:if(Reminders.loaded&&!Reminders.busy){
        if(Reminders.items.length!==1||Notifications.delivered!==0)Qt.exit(1);
        else if(!ticket){ticket=Reminders.request({kind:"create",title:"Monthly",date:"2099-01-31",time:"09:00",repeat:{kind:"monthly",anchorDay:31},zone:"UTC"},"monthly-create").ticket;}
        else if(Reminders.receipt(ticket).status!=="pending"){
            if(Reminders.receipt(ticket).status!=="persisted"||Reminders.read(Reminders.receipt(ticket).id).ok)Qt.exit(1);
            else if(phase===0){removedId=Reminders.receipt(ticket).id;ticket=Reminders.request({kind:"remove",id:removedId},"monthly-remove").ticket;phase=1;}
            else {console.log("PASS reminder QML reload does not replay delivered occurrences");Qt.quit();}
        }
    }}
}''', 'PASS reminder QML reload does not replay delivered occurrences')
    path.with_suffix('.json.bak').unlink()
    path.with_suffix('.json.bak').mkdir()
    run('''import QtQuick
import Quickshell
import qs.services
ShellRoot {
    property string ticket:""
    Timer {interval:30;running:true;repeat:true;onTriggered:{
        if(Reminders.loaded&&!Reminders.busy&&!ticket){ticket=Reminders.request({kind:"update",id:Reminders.items[0].id,title:"Failed edit"}).ticket;}
        else if(ticket&&Reminders.receipt(ticket).status!=="pending"&&!Reminders.busy){
            if(Reminders.receipt(ticket).status!=="failed"||Reminders.items[0].title==="Failed edit"||!Reminders.error)Qt.exit(1);
            else {console.log("PASS reminder QML write failure remains failed and preserves durable data");Qt.quit();}
        }
    }}
}''', 'PASS reminder QML write failure remains failed and preserves durable data')
    assert json.loads(path.read_text()) == persisted

run_ui('''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
ShellRoot {
    property int phase:0
    property int ticks:0
    FloatingWindow {visible:true;implicitWidth:340;implicitHeight:460
        Island.CalendarMenu {id:calendar;x:10;y:10;width:320;height:440;selectedDate:"2099-02-28";year:2099;month:1}
    }
    TestCase {id:keyboard;when:false}
    function walk(item,test):var {let found=test(item)?[item]:[];for(const child of item.children||[])found=found.concat(walk(child,test));return found;}
    function check(ok,label):void {if(!ok)throw new Error(label);}
    function controlsFit(editor):void {
        for(const button of walk(editor,item=>item.visible&&item.primary!==undefined&&["Save reminder","Done"].includes(item.text))){
            const point=button.mapToItem(editor,0,0);
            check(button.height>=24&&point.y>=0&&point.y+button.height<=editor.height+.5,"Editor action outside compact bounds");
        }
    }
    Component.onCompleted:{
        Reminders.items=[{id:"monthly",title:"Month end",date:"2099-01-31",startsOn:"2099-01-31",time:"09:00",lead:0,count:1,done:false,delivered:[],revision:1,repeat:{kind:"monthly",interval:1,anchorDay:31},zone:"UTC"}];
        Reminders.calendarExpanded=true;
    }
    Timer {interval:100;running:true;repeat:true;onTriggered:{try {
        check(++ticks<50,"Calendar/editor timeout");
        if(phase===0){
            const buttons=walk(calendar,item=>item.label==="Future occurrence");
            if(!buttons.length)return;
            check(!buttons[0].enabled,"Future calendar occurrence can complete current occurrence");
            check(calendar.entries.length===1&&calendar.entries[0].date==="2099-02-28","Calendar agenda not projected");
            calendar.edit(calendar.entries[0]);phase=1;
        }else if(phase===1){
            const editor=walk(calendar,item=>item.repeatKind!==undefined)[0];if(!editor)return;
            check(editor.day==="2099-01-31"&&editor.anchorDay===31&&editor.repeatKind==="monthly","Projected edit changed cadence anchor");
            check(!editor.scheduling&&!editor.repeating,"Editor options cover main editor");
            controlsFit(editor);
            editor.repeating=true;phase=2;
        }else if(phase===2){
            const editor=walk(calendar,item=>item.repeatKind!==undefined)[0];
            controlsFit(editor);
            editor.forceActiveFocus();keyboard.keyClick(Qt.Key_Escape);phase=3;
        }else if(phase===3){
            const editor=walk(calendar,item=>item.repeatKind!==undefined)[0];
            check(!editor.repeating&&calendar.editing,"Escape did not return from Repeat to editor");
            editor.scheduling=true;phase=4;
        }else if(phase===4){
            const editor=walk(calendar,item=>item.repeatKind!==undefined)[0];
            controlsFit(editor);editor.forceActiveFocus();keyboard.keyClick(Qt.Key_Escape);phase=5;
        }else if(phase===5){
            const editor=walk(calendar,item=>item.repeatKind!==undefined)[0];
            check(!editor.scheduling&&calendar.editing,"Escape did not return from Advance notices to editor");
            console.log("PASS production reminder calendar projection, editor anchor, separate Repeat and Advance notices, keyboard return");Qt.quit();
        }
    }catch(error){console.error(error);Qt.exit(1);}}}
}''', 'PASS production reminder calendar projection, editor anchor, separate Repeat and Advance notices, keyboard return')
