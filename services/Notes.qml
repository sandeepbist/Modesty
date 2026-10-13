pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root
    property var items: []
    property string activeId: ""
    property var draft: ({id:"",title:"",body:"",cursor:0,scroll:0,baseRevision:0,generation:0,savedGeneration:0,dirty:false})
    property bool loaded: Preferences.preview
    property string error: ""
    property string failureStatus: ""
    property bool libraryOpen: false
    property string exportPath: ""
    property var undo: null
    readonly property bool dirty: Object.values(drafts).some(value => value.dirty)
    readonly property bool saving: writer.running || queue.length > 0 || flight !== null
    readonly property string saveState: !loaded ? (error ? "Failed" : "Loading") : error ? (failureStatus === "conflict" ? "Conflict" : "Failed") : saving ? "Saving" : dirty ? "Unsaved" : "Saved"
    readonly property string script: Qt.resolvedUrl("../scripts/notes.py").toString().replace("file://", "")
    property var drafts: ({})
    property int storeRevision: 0
    property var queue: []
    property var flight: null
    property var response: null
    property var receipts: ({})
    property var flushGroups: ({})
    property var acknowledged: ({})
    property var failedJobs: []
    property var draftFailures: ({})
    property int sequence: 0
    property bool selectionChanged: false

    function identity(prefix): string { return (prefix || "note") + "-" + Date.now().toString(36) + "-" + (++sequence) + "-" + Math.random().toString(36).slice(2,9); }
    function copy(value): var { return JSON.parse(JSON.stringify(value)); }
    function refused(message, id): var { return {ok:false,ticket:"",id:id||"",revision:0,status:"refused",error:message}; }
    function note(id): var { return items.find(value => value.id === id); }
    function isDirty(id): bool { return !!drafts[id]?.dirty; }
    function contentError(value): string {
        return value.title.length > 300 || value.body.length > 1000000 || value.title.includes("\0") || value.body.includes("\0")
            ? "Use a title up to 300 characters and a body up to 1,000,000 characters without NUL." : "";
    }
    function updateDraft(value): void {
        drafts = Object.assign({}, drafts, {[value.id]:value});
        if (value.id === activeId) draft = copy(value);
    }
    function currentDraft(id): var {
        const existing = drafts[id];
        if (existing) return copy(existing);
        const value = note(id);
        return {id,title:value?.title||"",body:value?.body||"",cursor:0,scroll:0,baseRevision:value?.revision||0,generation:0,savedGeneration:0,dirty:false};
    }
    function select(id): bool {
        if (Session.isLocked() || typeof id !== "string" || (id && !note(id))) return false;
        if (id === activeId) return true;
        flush("selection");
        activeId = id; selectionChanged = true;
        updateDraft(currentDraft(id));
        persistSelection();
        return true;
    }
    function newNote(): bool {
        if (Session.isLocked()) return false;
        if (!activeId) return true;
        return select("");
    }
    function openLibrary(): void { if (!Session.isLocked()) libraryOpen = true; }
    function edit(content, cursor, scroll): void {
        if (Session.isLocked() || !content || typeof content.title !== "string" || typeof content.body !== "string") return;
        const invalid = contentError(content);
        let value = currentDraft(activeId);
        const changed = value.title !== content.title || value.body !== content.body;
        const empty = !invalid && !content.title.trim() && !content.body.trim();
        const accepted = queue.concat(flight?[flight]:[],failedJobs).some(job=>job.draftId===activeId||job.command?.id===activeId);
        if (activeId && !value.baseRevision && empty && !accepted) {
            const id=activeId,next=Object.assign({},drafts);delete next[id];drafts=next;
            items=items.filter(entry=>entry.id!==id);activeId="";selectionChanged=true;
            value=Object.assign({},value,{id:"",baseRevision:0,generation:0,savedGeneration:0,dirty:false});
            const unresolved=Object.values(draftFailures).some(failure=>isDirty(failure.id));
            if(loaded&&failureStatus==="refused"&&!unresolved){error="";failureStatus="";}
            persistSelection();
        }
        if (!activeId && empty) {
            value.title=content.title;value.body=content.body;value.cursor=Math.max(0,Number(cursor)||0);value.scroll=Math.max(0,Number(scroll)||0);
            updateDraft(value); return;
        }
        if (!activeId) {
            value.id=identity("note");activeId=value.id;selectionChanged=true;
            const stamp=new Date().toISOString();
            items=items.concat([{id:value.id,title:"",body:"",createdAt:stamp,updatedAt:stamp,status:"active",pinned:false,revision:0}]);
            const next=Object.assign({},drafts);delete next[""];drafts=next;
        }
        value.title=content.title;value.body=content.body;
        value.cursor=Math.max(0,Math.min(content.body.length,Number(cursor)||0));value.scroll=Math.max(0,Number(scroll)||0);
        if (changed) {value.generation++;value.dirty=true;if(!Object.keys(draftFailures).length){error="";failureStatus="";}}
        updateDraft(value);
        if (invalid) {error=invalid;failureStatus="refused";}
        if (changed) saveDelay.restart();
    }
    function search(query, status): var {
        if (Session.isLocked()) return [];
        query=String(query||"").trim().toLocaleLowerCase();status=status||"active";
        if (!["active","pinned","archived","trash"].includes(status)) return [];
        return items.filter(value => status==="pinned" ? value.status==="active"&&value.pinned : value.status===status)
            .map(value => {const pending=drafts[value.id];const title=pending?.title??value.title,body=pending?.body??value.body;
                return {id:value.id,title,createdAt:value.createdAt,updatedAt:value.updatedAt,status:value.status,pinned:value.pinned,revision:value.revision,
                    dirty:!!pending?.dirty,preview:body.replace(/\s+/g," ").trim().slice(0,140),matches:!query||(title+"\n"+body).toLocaleLowerCase().includes(query)};})
            .filter(value=>value.matches).sort((a,b)=>Number(b.pinned)-Number(a.pinned)||b.updatedAt.localeCompare(a.updatedAt)||a.id.localeCompare(b.id));
    }
    function read(id): var {
        if (Session.isLocked()) return {ok:false,note:null,dirty:false,error:"Session is locked"};
        const value=note(id);
        if (!loaded || !value) return {ok:false,note:null,dirty:false,error:!loaded?"Notes have not loaded":"Note no longer exists"};
        const pending=drafts[id];
        return {ok:true,note:Object.assign({},value,pending?{title:pending.title,body:pending.body}:{}),dirty:!!pending?.dirty,error:""};
    }
    function metadata(query, status): var {
        if (Session.isLocked()) return {ok:false,items:[],activeId:"",error:"Session is locked"};
        if (!loaded) return {ok:false,items:[],activeId:"",error:error||"Notes have not loaded"};
        return {ok:true,items:search(query,status).map(value=>({id:value.id,title:value.title,createdAt:value.createdAt,updatedAt:value.updatedAt,status:value.status,pinned:value.pinned,revision:value.revision,dirty:value.dirty})),activeId,error:""};
    }
    function remember(result): void {
        const next=Object.assign({},receipts,{[result.ticket]:result}),keys=Object.keys(next);
        for (const key of keys.slice(0,Math.max(0,keys.length-128))) delete next[key];
        receipts=next;
    }
    function request(command, operationId): var {
        if (Session.isLocked()) return refused("Session is locked",command?.id);
        if (Preferences.preview) return refused("External note commands are disabled in preview",command?.id);
        if (!command || typeof command !== "object" || !["create","update","append","pin","status","delete","export","recover"].includes(command.kind)) return refused("Unknown notes operation");
        if(command.kind==="export"&&(!Array.isArray(command.ids)||!command.ids.length||command.ids.some(id=>typeof id!=="string")))return refused("Choose notes to export");
        if (!loaded && command.kind!=="recover") return refused(error||"Notes have not loaded",command.id);
        if (typeof operationId !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/.test(operationId)) return refused("Supply a unique operation id",command.id);
        const existing=queue.concat(flight?[flight]:[]).find(job=>job.ticket===operationId);
        if (existing) return JSON.stringify(existing.command)===JSON.stringify(command)?receipts[operationId]:refused("Operation id was already used for another command",command.id);
        const replayingPersistedOperation = ["persisted","verified"].includes(receipts[operationId]?.status);
        if (replayingPersistedOperation) return enqueue({action:"request",command:copy(command),ticket:operationId,ui:false});
        if (command.kind==="recover" && (loaded || !error)) return refused("Recovery is only available when notes cannot be read");
        if (!["create","export","recover"].includes(command.kind)) {
            const target=note(command.id);
            if (!target) return refused("Note no longer exists",command.id);
            if (isDirty(command.id)) return refused("Note has unsaved typing. Save it before changing it.",command.id);
            if (!Number.isInteger(command.expectedRevision) || command.expectedRevision!==target.revision) return {ok:false,ticket:"",id:command.id,revision:target.revision,status:"conflict",error:"Note changed. Read its current revision and retry."};
        }
        if (command.kind==="export" && (command.ids||[]).some(id=>isDirty(id))) return refused("Save note drafts before exporting them");
        return enqueue({action:"request",command:copy(command),ticket:operationId,ui:false});
    }
    function enqueue(job): var {
        const result={ok:true,ticket:job.ticket,id:job.command?.id||"",revision:job.command?.expectedRevision||0,status:"pending",error:""};
        if (job.ticket) remember(result);
        queue=queue.concat([job]);Qt.callLater(pump);return result;
    }
    function queueDrafts(allowLocked): var {
        const tickets=[];
        if (!loaded) return tickets;
        for (const value of Object.values(drafts)) {
            if (!value.dirty) continue;
            const invalid=contentError(value);
            if(invalid){
                error=invalid;failureStatus="refused";
                draftFailures=Object.assign({},draftFailures,{[value.id]:{ok:false,id:value.id,generation:value.generation,status:failureStatus,error}});
                continue;
            }
            const pending=queue.concat(flight?[flight]:[],failedJobs).find(job=>job.draftId===value.id);
            if (pending) {tickets.push(pending.ticket);continue;}
            const command={kind:value.baseRevision?"update":"create",id:value.id,title:value.title,body:value.body};
            if (value.baseRevision) command.expectedRevision=value.baseRevision;
            const ticket=identity("save");
            enqueue({action:"request",command,ticket,draftId:value.id,generation:value.generation,ui:true,allowLocked:!!allowLocked});tickets.push(ticket);
        }
        return tickets;
    }
    function flush(reason): var {
        if (Session.isLocked()) return refused("Session is locked");
        return flushAccepted(reason,false);
    }
    function flushAccepted(reason, allowLocked): var {
        saveDelay.stop();
        if (!loaded) return refused(error||"Notes have not loaded");
        if(allowLocked)queue=queue.map(job=>job.draftId?Object.assign({},job,{allowLocked:true}):job);
        const targets={};for(const value of Object.values(drafts))if(value.dirty)targets[value.id]=value.generation;
        const tickets=queueDrafts(allowLocked);
        if (!Object.keys(targets).length) return {ok:!error,ticket:"",id:activeId,revision:note(activeId)?.revision||0,status:error?(failureStatus||"failed"):"persisted",error};
        const ticket=identity("flush");
        const groups=Object.assign({},flushGroups,{[ticket]:{targets,tickets,reason:reason||"manual"}}),keys=Object.keys(groups);
        for(const key of keys.slice(0,Math.max(0,keys.length-128)))delete groups[key];flushGroups=groups;
        return {ok:true,ticket,id:activeId,revision:note(activeId)?.revision||0,status:"pending",error:""};
    }
    function receipt(ticket): var {
        const group=flushGroups[ticket];
        if (group) {
            if(Object.keys(group.targets).every(id=>(acknowledged[id]||0)>=group.targets[id]))return {ok:true,ticket,status:Preferences.preview?"verified":"persisted",id:activeId,revision:note(activeId)?.revision||0,error:""};
            const failure=group.tickets.map(value=>receipts[value]).find(value=>value&&["failed","refused","conflict"].includes(value.status));
            const draftFailure=Object.keys(group.targets).map(id=>draftFailures[id]).find(value=>value&&(acknowledged[value.id]||0)<group.targets[value.id]&&value.generation>=group.targets[value.id]);
            return failure||draftFailure?Object.assign({},failure||draftFailure,{ticket}):{ok:true,ticket,status:"pending",error:""};
        }
        return receipts[ticket]||{ok:false,ticket,status:"refused",error:"Unknown or expired operation receipt"};
    }
    function persistSelection(): void {
        if (!loaded || Preferences.preview || Session.isLocked()) return;
        queue=queue.filter(job=>job.action!=="select");
        enqueue({action:"select",activeId,ticket:"",ui:true});
    }
    function uiMutation(command): var {
        if (Session.isLocked()) return refused("Session is locked",command.id);
        if (!loaded) return refused(error||"Notes have not loaded",command.id);
        const target=note(command.id);
        if (!target && command.kind!=="export" && command.kind!=="recover") return refused("Note no longer exists",command.id);
        flushAccepted("management",false);
        return enqueue({action:"request",command:copy(command),ticket:identity("ui"),ui:true,deferred:true,generation:drafts[command.id]?.generation||0});
    }
    function setPinned(id,pinned): var { return uiMutation({kind:"pin",id,pinned:!!pinned}); }
    function setStatus(id,status): var {
        const target=note(id),result=uiMutation({kind:"status",id,status});
        if(result.ok&&status==="trash")undo={id,previousStatus:target.status,previousPinned:target.pinned,ticket:result.ticket};
        return result;
    }
    function deleteNote(id): var { return uiMutation({kind:"delete",id}); }
    function exportNotes(ids,destination): var { const command={kind:"export",ids:ids||[activeId]};if(destination)command.destination=destination;return uiMutation(command); }
    function recover(): var {
        if (Session.isLocked()) return refused("Session is locked");
        if (Preferences.preview) return refused("Recovery is disabled in preview");
        return request({kind:"recover"},identity("recover"));
    }
    function undoTrash(): var {
        if (!undo) return refused("No note to restore");
        const value=undo,result=setStatus(value.id,value.previousStatus);
        if(result.ok){if(value.previousPinned)setPinned(value.id,true);undo=null;}return result;
    }
    function retry(): void {
        if(Session.isLocked()||writer.running)return;
        error="";failureStatus="";
        const jobs=failedJobs;failedJobs=[];
        if(!loaded)enqueue({action:"load",ticket:"",ui:true});
        for(const job of jobs)if(job.action!=="load")enqueue(job);
        queueDrafts(false);Qt.callLater(pump);
    }
    function adoptStore(store, recovery): void {
        if(!store||!Array.isArray(store.items))return;
        const local=items.filter(value=>isDirty(value.id)&&!store.items.some(entry=>entry.id===value.id));
        items=store.items.concat(local);storeRevision=store.revision;
        for(const entry of store.receipts||[])remember(entry.result);
        for(const value of Object.values(drafts)) {
            const entry=store.items.find(note=>note.id===value.id);
            if(!value.dirty){if(entry)updateDraft(Object.assign({},value,{title:entry.title,body:entry.body,baseRevision:entry.revision}));}
            else if(recovery)updateDraft(Object.assign({},value,{baseRevision:entry?.revision||0}));
        }
        if(!selectionChanged){activeId=store.selection?.activeId||"";updateDraft(currentDraft(activeId));}
        loaded=true;
    }
    function pump(): void {
        if(writer.running||flight||!queue.length)return;
        const job=queue[0];queue=queue.slice(1);flight=job;response=null;
        if(Session.isLocked()&&!job.allowLocked){complete({ok:false,status:"refused",error:"Session is locked"});return;}
        if(job.action!=="load"&&job.command?.kind!=="recover"&&!loaded){complete({ok:false,status:"refused",error:"Notes have not loaded"});return;}
        if(job.deferred){
            const target=note(job.command.id);
            if(target)job.command.expectedRevision=target.revision;
            if(job.command.kind==="export"?(job.command.ids||[]).some(id=>isDirty(id)):isDirty(job.command.id)){
                complete({ok:false,status:"refused",error:"Typing changed before the operation. Save and retry."});return;
            }
            job.deferred=false;
        }
        if(job.action==="select"&&job.activeId&&!note(job.activeId)?.revision){complete({ok:true});return;}
        if(Preferences.preview){Qt.callLater(()=>complete(previewResult(job)));return;}
        job.payload={action:job.action,expectedStoreRevision:storeRevision};
        if(job.command){job.payload.command=job.command;job.payload.operationId=job.ticket;if(job.draftId)job.payload.activeId=activeId;}
        if(job.action==="select")job.payload.activeId=job.activeId;
        writer.running=true;
    }
    function previewResult(job): var {
        const values=copy(items),command=job.command;
        if(!command)return {ok:true};
        let value=values.find(entry=>entry.id===command.id),revision=value?.revision||0;
        if(command.kind==="create"){value=Object.assign({},value||{id:command.id||identity("note"),createdAt:new Date().toISOString(),status:"active",pinned:false},{title:command.title||"",body:command.body||"",revision:1,updatedAt:new Date().toISOString()});const index=values.findIndex(entry=>entry.id===value.id);if(index>=0)values[index]=value;else values.push(value);}
        else if(command.kind==="export")return {ok:true,status:"verified",path:"Preview export",ticket:job.ticket,id:"",revision:0,preview:true};
        else if(!value)return {ok:false,status:"refused",error:"Note no longer exists"};
        else if(command.kind==="delete"){if(value.status!=="trash")return {ok:false,status:"refused",error:"Move a note to Trash before deleting it permanently"};values.splice(values.indexOf(value),1);}
        else {if(command.kind==="update"){value.title=command.title??value.title;value.body=command.body??value.body;}else if(command.kind==="pin")value.pinned=command.pinned;else if(command.kind==="status"){value.status=command.status;if(value.status!=="active")value.pinned=false;}value.revision++;value.updatedAt=new Date().toISOString();}
        revision=value?.revision||revision+1;
        return {ok:true,status:"verified",ticket:job.ticket,id:value?.id||command.id,revision,preview:true,store:{revision:storeRevision+1,items:values,receipts:[],selection:{activeId:values.some(entry=>entry.id===activeId)?activeId:""}}};
    }
    function complete(result): void {
        const job=flight;if(!job)return;
        result=result||{ok:false,status:"failed",error:"Notes storage stopped without a response"};
        if(result.store)adoptStore(result.store,job.command?.kind==="recover"&&result.ok);
        if(result.ok){
            error="";failureStatus="";
            failedJobs=failedJobs.filter(value=>value.ticket!==job.ticket);
            if(job.command?.kind==="recover"){
                failedJobs=failedJobs.filter(value=>!value.draftId&&value.action!=="load");
                draftFailures={};
            }
            if(job.draftId){
                const value=drafts[job.draftId];
                if(value){
                    const current=Object.assign({},value,{baseRevision:result.revision,savedGeneration:job.generation,dirty:value.generation!==job.generation});
                    const persisted=note(job.draftId);
                    if(!current.dirty&&persisted)Object.assign(current,{title:persisted.title,body:persisted.body,baseRevision:persisted.revision});
                    updateDraft(current);
                    acknowledged=Object.assign({},acknowledged,{[job.draftId]:job.generation});
                    const failures=Object.assign({},draftFailures);delete failures[job.draftId];draftFailures=failures;
                }
            }
            if(job.command?.kind==="delete"){
                const next=Object.assign({},drafts);delete next[job.command.id];drafts=next;
                if(activeId===job.command.id){activeId="";updateDraft(currentDraft(""));}
            }
            if(undo&&job.command?.id===undo.id&&["status","delete"].includes(job.command.kind)&&note(undo.id)?.status!=="trash")undo=null;
            if(result.path)exportPath=result.path;
            if(job.ticket)remember(Object.assign({ok:true,ticket:job.ticket,id:job.command?.id||"",revision:0,status:Preferences.preview?"verified":"persisted",error:""},result,{store:undefined}));
            const unresolved=Object.values(draftFailures).find(value=>isDirty(value.id));
            if(unresolved){error=unresolved.error;failureStatus=unresolved.status;}
        }else{
            error=result.error||"Could not save notes";failureStatus=result.status||"failed";
            if(job.action==="load"||result.readFailed)loaded=false;
            if(job.ticket)remember({ok:false,ticket:job.ticket,id:job.command?.id||"",revision:job.command?.expectedRevision||0,status:failureStatus,error});
            if(job.draftId)draftFailures=Object.assign({},draftFailures,{[job.draftId]:{ok:false,id:job.draftId,generation:job.generation,status:failureStatus,error}});
            if(job.action!=="select")failedJobs=failedJobs.concat([job]);
        }
        flight=null;
        if(result.ok&&dirty&&!queue.some(value=>value.deferred))queueDrafts(Session.isLocked());
        Qt.callLater(pump);
    }
    Timer {id:saveDelay;interval:350;onTriggered:root.flushAccepted("autosave",false)}
    Process {
        id:writer
        command:["python3",root.script]
        stdinEnabled:true
        onStarted:write(JSON.stringify(root.flight.payload)+"\n")
        stdout:StdioCollector {onStreamFinished:{try{root.response=JSON.parse(text);}catch(e){root.response={ok:false,status:"failed",error:"Could not read the notes storage response"};}}}
        onExited:Qt.callLater(()=>root.complete(root.response))
    }
    Component.onCompleted:if(!Preferences.preview)enqueue({action:"load",ticket:"",ui:true})
    Connections {target:Session;function onLockedChanged(){if(Session.locked){saveDelay.stop();root.flushAccepted("lock",true);}else if(!root.loaded)root.retry();}}
    IpcHandler {
        target:"notes"
        function status(): string {return JSON.stringify({loaded:root.loaded,dirty:root.dirty,saving:root.saving,saveState:root.saveState,error:root.error,activeId:Session.isLocked()?"":root.activeId,count:root.items.length,revision:root.storeRevision,preview:Preferences.preview});}
        function list(query:string,status:string):string {return JSON.stringify(root.metadata(query,status));}
        function read(id:string):string {return JSON.stringify(root.read(id));}
        function flush(reason:string):string {return JSON.stringify(root.flush(reason));}
        function receipt(ticket:string):string {return JSON.stringify(root.receipt(ticket));}
        function request(value:string,operationId:string):string {try{return JSON.stringify(root.request(JSON.parse(value),operationId));}catch(e){return JSON.stringify(root.refused("Invalid notes command"));}}
    }
}
