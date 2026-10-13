#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from qml import run

ROOT = Path(__file__).resolve().parents[1]

run('''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
ShellRoot {
    FloatingWindow {visible:true;implicitWidth:700;implicitHeight:500
        Island.NotesMenu {id:panel;width:396;height:386}
    }
    TestCase {id:keyboard;when:false}
    function check(value,message) {if(!value)throw new Error(message);}
    Timer {interval:150;running:true;onTriggered:{try {
        const recover=keyboard.findChild(panel,"notesRecover"),retry=keyboard.findChild(panel,"notesRetry");
        check(recover&&retry,"Recovery controls missing");
        Notes.edit({title:"Draft",body:"Keep unsaved typing"},5,12);
        const draft=JSON.stringify(Notes.draft);
        for(const error of ["Save failed","Note changed","Invalid note title","Export destination already exists"]){
            Notes.error=error;
            check(Notes.loaded&&retry.visible&&!recover.visible,"Readable Notes offer Recover for "+error);
        }
        Notes.loaded=false;Notes.error="Could not read notes";
        check(recover.visible&&recover.enabled&&retry.visible,"Read failure hides Recover");
        Notes.error="";
        check(!recover.visible,"Initial loading offers Recover");
        check(JSON.stringify(Notes.draft)===draft&&Notes.dirty,"Recovery controls changed dirty draft");
        console.log("PASS Notes UI recovery appears only after read failure and preserves dirty draft");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''', "PASS Notes UI recovery appears only after read failure and preserves dirty draft")

with tempfile.TemporaryDirectory(prefix="modesty-notes-qml-") as temporary:
    workspace = Path(temporary)
    services = workspace / "services"
    services.mkdir()
    fail = workspace / "fail"
    lose_ack = workspace / "lose-ack"
    requests = workspace / "requests.jsonl"
    wrapper = workspace / "storage.py"
    wrapper.write_text(f'''import contextlib,io,json,runpy,sys,time
from pathlib import Path
line=sys.stdin.buffer.readline()
request=json.loads(line)
if request.get("action")=="request":
    with Path({str(requests)!r}).open("a") as stream:
        stream.write(json.dumps(request)+"\\n")
    time.sleep(.22)
    if Path({str(fail)!r}).exists():
        print(json.dumps({{"ok":False,"status":"failed","error":"Injected disk failure"}}))
        sys.exit(1)
sys.stdin=io.TextIOWrapper(io.BytesIO(line))
sys.argv=[{str(ROOT / "scripts/notes.py")!r}]
if request.get("action")=="request" and Path({str(lose_ack)!r}).exists():
    Path({str(lose_ack)!r}).unlink()
    with contextlib.redirect_stdout(io.StringIO()):
        runpy.run_path(sys.argv[0],run_name="__main__")
    sys.exit(1)
runpy.run_path(sys.argv[0],run_name="__main__")
''')
    source = (ROOT / "services/Notes.qml").read_text().replace(
        'Qt.resolvedUrl("../scripts/notes.py").toString().replace("file://", "")', json.dumps(str(wrapper)))
    (services / "Notes.qml").write_text(source)
    for name, body in {
        "Preferences": "property bool preview:false",
        "Session": "property bool locked:false;function isLocked():bool{return locked;}",
    }.items():
        (services / f"{name}.qml").write_text(f"pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {{{body}}}\n")
    (services / "qmldir").write_text("\n".join(f"singleton {name} 1.0 {name}.qml" for name in ("Notes", "Preferences", "Session")) + "\n")
    (workspace / "shell.qml").write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import "services" as Audit
ShellRoot {
    id:audit
    property string invalidTitle:""
    property string invalidBody:""
    property string invalidId:""
    Loader {id:panel;active:true;sourceComponent:Item {property string text:Audit.Notes.draft.body}}
    IpcHandler {
        target:"audit"
        function snapshot():string {const n=Audit.Notes;return JSON.stringify({draft:n.draft,items:n.items,dirty:n.dirty,saving:n.saving,error:n.error,loaded:n.loaded,undo:n.undo,exportPath:n.exportPath});}
        function edit(title:string,body:string,cursor:int,scroll:int):string {Audit.Notes.edit({title,body},cursor,scroll);return Audit.Notes.activeId;}
        function invalid(kind:string):void {audit.invalidTitle=kind==="title-limit"?"t".repeat(301):kind==="title-nul"?"before\\0after":"Validation";audit.invalidBody=kind==="body-limit"?"x".repeat(1000001):kind==="body-nul"?"before\\0after":"Keep typing through recovery";Audit.Notes.edit({title:audit.invalidTitle,body:audit.invalidBody},5,12);audit.invalidId=Audit.Notes.activeId;}
        function invalidState():string {const n=Audit.Notes,read=n.read(audit.invalidId);return JSON.stringify({draftMatches:n.draft.title===audit.invalidTitle&&n.draft.body===audit.invalidBody,readMatches:read.note?.title===audit.invalidTitle&&read.note?.body===audit.invalidBody,dirty:n.dirty,readDirty:read.dirty,error:n.error});}
        function copy(id:string):bool {const body=Audit.Notes.read(id).note.body;Quickshell.clipboardText=body;return Quickshell.clipboardText===body;}
        function choose(id:string):bool {return Audit.Notes.select(id);}
        function blank():bool {return Audit.Notes.newNote();}
        function lock(value:bool):void {Audit.Session.locked=value;}
        function close():void {panel.active=false;}
        function open():void {panel.active=true;}
        function retry():void {Audit.Notes.retry();}
        function pin(id:string,value:bool):string {return JSON.stringify(Audit.Notes.setPinned(id,value));}
        function status(id:string,value:string):string {return JSON.stringify(Audit.Notes.setStatus(id,value));}
        function remove(id:string):string {return JSON.stringify(Audit.Notes.deleteNote(id));}
        function undo():string {return JSON.stringify(Audit.Notes.undoTrash());}
        function recover():string {return JSON.stringify(Audit.Notes.recover());}
        function exportNotes(id:string,destination:string):string {return JSON.stringify(Audit.Notes.exportNotes([id],destination));}
    }
}
''')
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", QSG_RHI_BACKEND="software",
                       MODESTY_PREVIEW="0", QS_NO_RELOAD_POPUP="1",
                       XDG_STATE_HOME=str(workspace / "state"), XDG_CACHE_HOME=str(workspace / "cache"))
    with (workspace / "log").open("w+") as log:
        process = subprocess.Popen(["qs", "--no-color", "-p", str(workspace)], env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)

        def call(target, method, *args, raw=False):
            result = subprocess.run(["qs", "ipc", "--pid", str(process.pid), "call", target, method, *map(str, args)],
                                    capture_output=True, text=True, timeout=4)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            return result.stdout.strip() if raw else json.loads(result.stdout)

        def snapshot():
            return call("audit", "snapshot")

        def wait(predicate, label, timeout=8):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                if process.poll() is not None:
                    log.seek(0)
                    raise AssertionError(log.read())
                try:
                    value = predicate()
                    if value:
                        return value
                except AssertionError:
                    pass
                time.sleep(.035)
            log.seek(0)
            raise AssertionError(label + "\n" + log.read()[-4000:])

        def settled():
            value = snapshot()
            return value if value["loaded"] and not value["saving"] and not value["dirty"] else None

        def completed(ticket, expected="persisted"):
            value = call("notes", "receipt", ticket)
            return value if value["status"] == expected else None

        def mutation(command, operation):
            return call("notes", "request", json.dumps(command, ensure_ascii=False), operation)

        try:
            wait(lambda: call("notes", "status")["loaded"], "Initial notes load")
            readable_recovery = call("audit", "recover")
            assert not readable_recovery["ok"] and readable_recovery["status"] == "refused", readable_recovery
            call("audit", "edit", "", "", 0, 0, raw=True)
            assert not snapshot()["items"] and not snapshot()["dirty"]
            first = call("audit", "edit", "", "पहला 📝\nFirst body", 6, 12, raw=True)
            initial = call("notes", "flush", "race")
            assert initial["ok"] and initial["status"] == "pending"
            wait(lambda: call("notes", "status")["saving"], "Draft save begins")
            call("audit", "edit", "", "पहला 📝\nNew text during save", 11, 27, raw=True)
            assert call("audit", "blank")
            second = call("audit", "edit", "Second", "Second body", 4, 8, raw=True)
            call("notes", "flush", "switch")
            call("audit", "close", raw=True)
            call("audit", "lock", "true", raw=True)
            assert not call("notes", "read", first)["ok"]
            assert not call("notes", "list", "", "active")["ok"]
            assert not mutation({"kind": "create", "body": "Locked"}, "locked")["ok"]
            assert not call("notes", "flush", "locked")["ok"]
            before = snapshot()["draft"]["body"]
            call("audit", "edit", "", "Blocked input", 0, 0, raw=True)
            assert snapshot()["draft"]["body"] == before
            wait(settled, "Pre-lock draft flush completes")
            assert completed(initial["ticket"])
            call("audit", "lock", "false", raw=True)
            call("audit", "open", raw=True)
            assert call("audit", "choose", first)
            value = snapshot()
            assert value["draft"]["body"] == "पहला 📝\nNew text during save"
            assert value["draft"]["cursor"] == 11 and value["draft"]["scroll"] == 27
            assert len(value["items"]) == 2
            metadata = call("notes", "list", "New text", "active")
            assert len(metadata["items"]) == 1
            assert "body" not in metadata["items"][0] and "preview" not in metadata["items"][0]
            actual = call("notes", "read", first)
            assert actual["note"]["revision"] == 2 and not actual["dirty"]
            call("audit", "edit", "", "Unsaved typing", 8, 31, raw=True)
            refused = mutation({"kind": "append", "id": first, "expectedRevision": 2, "body": "Overwrite"}, "dirty-target")
            assert not refused["ok"] and refused["status"] == "refused"
            call("notes", "flush", "dirty")
            wait(settled, "Dirty note persists")
            revision = call("notes", "read", first)["note"]["revision"]
            append = {"kind": "append", "id": first, "expectedRevision": revision, "body": "\nAppended once"}
            requested = mutation(append, "append-once")
            assert requested["status"] == "pending"
            wait(lambda: completed(requested["ticket"]), "Append receipt")
            repeat = mutation(append, "append-once")
            assert repeat["ok"]
            wait(lambda: completed(repeat["ticket"]), "Retry receipt")
            assert call("notes", "read", first)["note"]["body"].count("Appended once") == 1
            call("audit", "pin", first, "true")
            wait(settled, "Pin")
            trashed = call("audit", "status", first, "trash")
            wait(lambda: completed(trashed["ticket"]), "Trash")
            assert call("notes", "read", first)["note"]["status"] == "trash"
            assert snapshot()["undo"]["id"] == first
            call("audit", "undo")
            wait(settled, "Trash Undo")
            restored = call("notes", "read", first)["note"]
            assert restored["status"] == "active" and restored["pinned"]

            assert call("audit", "blank")
            lose_ack.touch()
            lost = call("audit", "edit", "Lost ack", "Sent generation", 7, 10, raw=True)
            lost_flush = call("notes", "flush", "lost-ack")
            wait(lambda: requests.exists() and any(json.loads(line)["command"].get("id") == lost
                 for line in requests.read_text().splitlines()), "Lost acknowledgement save starts")
            call("audit", "edit", "Lost ack", "New generation during lost acknowledgement", 16, 24, raw=True)
            wait(lambda: completed(lost_flush["ticket"], "failed"), "Lost acknowledgement reports failure")
            path = workspace / "state/modesty/notes.json"
            stored = json.loads(path.read_text())
            assert next(value for value in stored["items"] if value["id"] == lost)["body"] == "Sent generation"
            assert snapshot()["dirty"] and snapshot()["draft"]["body"] == "New generation during lost acknowledgement"
            call("audit", "close", raw=True)
            assert call("audit", "choose", first)
            wait(lambda: not snapshot()["saving"], "Selection after lost acknowledgement")
            assert call("audit", "choose", lost)
            wait(lambda: not snapshot()["saving"], "Select lost acknowledgement draft")
            call("audit", "retry", raw=True)
            wait(lambda: snapshot()["draft"]["baseRevision"] == 1 and snapshot()["dirty"]
                 and snapshot()["saving"], "Only sent generation acknowledged")
            assert call("notes", "status")["saveState"] != "Saved"
            wait(settled, "Lost create acknowledgement retry")
            assert call("audit", "choose", lost)
            saved = call("notes", "read", lost)["note"]
            assert saved["body"] == "New generation during lost acknowledgement" and saved["revision"] == 2
            assert snapshot()["draft"]["cursor"] == 16 and snapshot()["draft"]["scroll"] == 24
            writes = [json.loads(line) for line in requests.read_text().splitlines()
                      if json.loads(line)["command"].get("id") == lost]
            assert [value["command"]["kind"] for value in writes] == ["create", "create", "update"]
            assert writes[0]["operationId"] == writes[1]["operationId"]
            assert len([value for value in json.loads(path.read_text())["items"] if value["id"] == lost]) == 1
            assert completed(lost_flush["ticket"])

            lose_ack.touch()
            call("audit", "edit", "Lost ack", "Update snapshot", 8, 32, raw=True)
            lost_update = call("notes", "flush", "lost-update")
            wait(lambda: len([json.loads(line) for line in requests.read_text().splitlines()
                 if json.loads(line)["command"].get("id") == lost
                 and json.loads(line)["command"]["kind"] == "update"]) == 2, "Lost update save starts")
            call("audit", "edit", "Lost ack", "Newest update during lost acknowledgement", 18, 39, raw=True)
            wait(lambda: completed(lost_update["ticket"], "failed"), "Lost update acknowledgement")
            assert call("notes", "status")["saveState"] != "Saved"
            call("audit", "retry", raw=True)
            wait(settled, "Lost update acknowledgement retry")
            current = call("notes", "read", lost)["note"]
            assert current["revision"] == 4 and current["body"] == "Newest update during lost acknowledgement"

            lose_ack.touch()
            lost_append = mutation({"kind": "append", "id": lost, "expectedRevision": 4,
                                    "body": "\nLost append once"}, "lost-append")
            wait(lambda: completed(lost_append["ticket"], "failed"), "Lost append acknowledgement")
            call("audit", "retry", raw=True)
            wait(lambda: completed(lost_append["ticket"]), "Lost append acknowledgement retry")
            assert call("notes", "read", lost)["note"]["body"].count("Lost append once") == 1

            lose_ack.touch()
            call("audit", "edit", "Lost ack", "Saved before another session edits", 12, 41, raw=True)
            old_ack = call("notes", "flush", "old-ack-new-store")
            wait(lambda: completed(old_ack["ticket"], "failed"), "Saved draft acknowledgement lost")
            saved_store = json.loads(path.read_text())
            saved_note = next(value for value in saved_store["items"] if value["id"] == lost)
            external = subprocess.run([sys.executable, str(ROOT / "scripts/notes.py")],
                                      input=json.dumps({"action": "request", "expectedStoreRevision": saved_store["revision"],
                                                        "operationId": "external-after-ack-loss",
                                                        "command": {"kind": "append", "id": lost, "expectedRevision": saved_note["revision"], "body": "\nNewer remote text"}}),
                                      capture_output=True, text=True, env=environment, timeout=4)
            assert external.returncode == 0, external.stdout + external.stderr
            call("audit", "retry", raw=True)
            wait(settled, "Receipt replay adopts newest persisted note")
            actual = call("notes", "read", lost)["note"]
            assert actual["body"] == "Saved before another session edits\nNewer remote text"
            assert actual["revision"] == saved_note["revision"] + 1

            lose_ack.touch()
            lost_pin = call("audit", "pin", lost, "true")
            wait(lambda: completed(lost_pin["ticket"], "failed"), "Lost management acknowledgement")
            assert call("audit", "choose", first)
            wait(lambda: not snapshot()["saving"], "Reload persisted management revision")
            call("audit", "retry", raw=True)
            wait(lambda: completed(lost_pin["ticket"]), "Lost management acknowledgement retry")
            assert call("notes", "read", lost)["note"]["pinned"]

            observed = call("notes", "read", lost)["note"]["revision"]
            stale = mutation({"kind": "append", "id": lost, "expectedRevision": observed - 1,
                              "body": "Must not append"}, "qml-stale-note")
            assert not stale["ok"] and stale["status"] == "conflict"
            assert call("audit", "choose", lost)
            wait(settled, "Select draft before external write")
            external = subprocess.run([sys.executable, str(ROOT / "scripts/notes.py")],
                                      input=json.dumps({"action": "request", "expectedStoreRevision": json.loads(path.read_text())["revision"],
                                                        "operationId": "external-session", "command": {"kind": "create", "id": "external-session-note", "body": "Other session"}}),
                                      capture_output=True, text=True, env=environment, timeout=4)
            assert external.returncode == 0, external.stdout + external.stderr
            call("audit", "edit", "Lost ack", "Local text through store conflict", 15, 43, raw=True)
            conflict = call("notes", "flush", "store-conflict")
            wait(lambda: completed(conflict["ticket"], "conflict"), "Stale store refuses local save")
            assert snapshot()["dirty"] and snapshot()["draft"]["body"] == "Local text through store conflict"
            call("audit", "retry", raw=True)
            wait(settled, "Unrelated store conflict retry")
            assert call("notes", "read", lost)["note"]["body"] == "Local text through store conflict"
            assert call("notes", "read", "external-session-note")["note"]["body"] == "Other session"
            call("audit", "status", "external-session-note", "trash")
            wait(settled, "Trash external test note")
            call("audit", "remove", "external-session-note")
            wait(settled, "Remove external test note")
            call("audit", "status", lost, "trash")
            wait(settled, "Trash acknowledgement test note")
            call("audit", "remove", lost)
            wait(settled, "Remove acknowledgement test note")
            assert call("audit", "choose", first)

            fail.touch()
            call("audit", "edit", "", "Retain failed draft", 9, 45, raw=True)
            failed = call("notes", "flush", "failure")
            wait(lambda: completed(failed["ticket"], "failed"), "Failed draft receipt")
            assert snapshot()["dirty"] and snapshot()["loaded"]
            call("audit", "close", raw=True)
            assert call("audit", "blank")
            assert call("audit", "choose", first)
            assert snapshot()["draft"]["body"] == "Retain failed draft"
            assert snapshot()["draft"]["cursor"] == 9 and snapshot()["draft"]["scroll"] == 45
            wait(lambda: not snapshot()["saving"], "Failed queue drains")
            assert call("notes", "status")["saveState"] == "Failed"
            backup = path.with_name("notes.backup.json")
            current_bytes, backup_bytes = path.read_bytes(), backup.read_bytes()
            dirty_draft = snapshot()["draft"]
            recovery_refused = call("audit", "recover")
            assert not recovery_refused["ok"] and recovery_refused["status"] == "refused", recovery_refused
            direct_refused = mutation({"kind": "recover"}, "loaded-recovery")
            assert not direct_refused["ok"] and direct_refused["status"] == "refused", direct_refused
            assert snapshot()["draft"] == dirty_draft and snapshot()["dirty"]
            assert path.read_bytes() == current_bytes and backup.read_bytes() == backup_bytes
            fail.unlink()
            call("audit", "retry", raw=True)
            wait(settled, "Save retry")
            assert call("notes", "read", first)["note"]["body"] == "Retain failed draft"

            path = workspace / "state/modesty/notes.json"
            valid = path.read_bytes()
            path.write_text("corrupt JSON")
            call("audit", "edit", "", "Retain draft through load retry", 13, 49, raw=True)
            blocked = call("notes", "flush", "corrupt-draft-retry")
            wait(lambda: completed(blocked["ticket"], "failed"), "Draft read failure blocks writes")
            assert not snapshot()["loaded"] and snapshot()["dirty"] and path.read_text() == "corrupt JSON"
            path.write_bytes(valid)
            call("audit", "retry", raw=True)
            wait(settled, "Load retry replays accepted draft")
            assert call("notes", "read", first)["note"]["body"] == "Retain draft through load retry"

            path.write_text("corrupt JSON")
            call("audit", "edit", "", "Read failure draft before recovery", 14, 51, raw=True)
            rejected = call("notes", "flush", "corrupt-draft-recovery")
            wait(lambda: completed(rejected["ticket"], "failed"), "Read failure blocks writes")
            assert not snapshot()["loaded"] and path.read_text() == "corrupt JSON"
            assert not mutation({"kind": "create", "body": "Still blocked"}, "blocked-create")["ok"]
            call("audit", "edit", "", "Keep typing through recovery", 12, 54, raw=True)
            assert snapshot()["dirty"]
            assert not call("notes", "flush", "blocked")["ok"]
            recovery = call("audit", "recover")
            assert recovery["ok"]
            wait(lambda: completed(recovery["ticket"]), "Explicit validated recovery")
            wait(settled, "Recovered draft persists")
            assert call("notes", "read", first)["note"]["body"] == "Keep typing through recovery"
            assert snapshot()["draft"]["cursor"] == 12 and snapshot()["draft"]["scroll"] == 54
            current_bytes, backup_bytes = path.read_bytes(), backup.read_bytes()
            replay = mutation({"kind": "recover"}, recovery["ticket"])
            assert replay["ok"], replay
            wait(lambda: completed(replay["ticket"]), "Completed recovery replay with readable Notes")
            wait(settled, "Recovery replay settles")
            assert path.read_bytes() == current_bytes and backup.read_bytes() == backup_bytes
            for kind in ("title-limit","body-limit","title-nul","body-nul"):
                before=json.loads(path.read_text())
                call("audit","invalid",kind,raw=True)
                value=call("audit","invalidState")
                assert value["dirty"] and value["draftMatches"], (kind,value)
                rejected=call("notes","flush","invalid-content")
                assert completed(rejected["ticket"],"refused"), (kind,rejected)
                call("audit","retry",raw=True)
                assert call("notes","status")["saveState"]=="Failed" and call("audit","invalidState")["dirty"], kind
                assert call("audit","choose",second)
                wait(lambda:not snapshot()["saving"],"Invalid draft selection")
                value=call("audit","invalidState")
                assert value["readMatches"] and value["readDirty"], (kind,value)
                assert call("audit","choose",first)
                call("audit","close",raw=True);call("audit","open",raw=True)
                assert call("audit","invalidState")["draftMatches"], kind
                assert call("audit","copy",first), kind
                assert next(note for note in json.loads(path.read_text())["items"] if note["id"]==first)==next(note for note in before["items"] if note["id"]==first), kind
                call("audit","edit","","Keep typing through recovery",12,54,raw=True)
                call("notes","flush","corrected-content")
                wait(settled,"Corrected invalid draft persists")
                assert not snapshot()["error"] and completed(rejected["ticket"]), kind
            print("PASS invalid Notes titles, bodies and NUL remain dirty through retry, switch, reload and copy; corrected text saves")
            call("audit","status",first,"trash")
            wait(settled,"Trash before native restore")
            assert snapshot()["undo"]["id"]==first
            restored=mutation({"kind":"status","id":first,"status":"active","expectedRevision":call("notes","read",first)["note"]["revision"]},"restore-clears-undo")
            wait(lambda:completed(restored["ticket"]),"Native restore clears Undo")
            assert snapshot()["undo"] is None
            destination = workspace / "second.md"
            exported = call("audit", "exportNotes", second, destination)
            wait(lambda: completed(exported["ticket"], "verified"), "Verified export")
            assert destination.read_text() == "# Second\n\nSecond body\n"
            assert snapshot()["exportPath"] == str(destination)
            call("audit", "status", second, "trash")
            wait(settled, "Move second note to Trash")
            removed = call("audit", "remove", second)
            wait(lambda: completed(removed["ticket"]), "Permanent deletion receipt")
            assert not call("notes", "read", second)["ok"]
            assert snapshot()["undo"] is None
            persisted = json.loads(path.read_text())
            assert len(persisted["items"]) == 1 and persisted["items"][0]["body"] == "Keep typing through recovery"
            flush = call("notes", "flush", "graceful-restart")
            assert flush["ok"] and flush["status"] == "persisted" and not snapshot()["saving"]
            process.terminate()
            process.wait(timeout=4)
            process = subprocess.Popen(["qs", "--no-color", "-p", str(workspace)], env=environment,
                                       stdout=log, stderr=subprocess.STDOUT)
            wait(settled, "Restart restores persisted notes")
            assert snapshot()["draft"]["id"] == first
            assert snapshot()["draft"]["body"] == "Keep typing through recovery"
            assert call("notes", "read", first)["note"]["revision"] == persisted["items"][0]["revision"]
            replay = mutation(append, "append-once")
            wait(lambda: completed(replay["ticket"]), "Persisted receipt replay after service restart")
            assert call("notes", "read", first)["note"]["body"] == "Keep typing through recovery"
            assert json.loads(path.read_text())["revision"] == persisted["revision"]
            log.seek(0)
            output = log.read()
            assert "ReferenceError" not in output and "TypeError" not in output, output[-3500:]
        finally:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=4)

print("PASS Notes QML real storage, IPC, snapshot races, lock flush, draft survival, dirty guards, lost acknowledgements, retry, conflicts, Trash Undo, export, recovery and restart")
