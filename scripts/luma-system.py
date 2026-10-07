#!/usr/bin/env python3
"""Real system tools for Luma's observe/execute loop; no request phrase tables."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home()/".local/state"))/"modesty"/"luma-system"
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home()/".config"))
DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home()/".local/share"))
PROTECTED = [Path.home()/p for p in (".ssh", ".gnupg", ".aws", ".azure", ".kube", ".mozilla", ".zen", ".password-store", ".netrc", ".git-credentials", ".npmrc", ".pypirc", ".docker", ".bash_history", ".zsh_history", ".t3", ".codex/auth.json", ".claude/.credentials.json")]
PROTECTED += [CONFIG/p for p in ("gcloud", "gh", "rclone", "discord", "chromium", "google-chrome", "BraveSoftware", "modesty/gemini.key", "modesty/typesafe.key")]
PROTECTED += [DATA/p for p in ("keyrings", "fish/fish_history", "opencode/auth.json")]
PROTECTED += list(Path.home().glob(".env*"))
CATALOG = {
    "application_interfaces": "Discover real registered Obsidian vaults, installed CLI paths and live MPRIS player identities, capabilities, supported URI schemes and track metadata. wait_seconds=1..6 waits for a just-launched application's interface; query only when needed, never continuously poll. Vaults contain Markdown notes; write_file can create researched notes at their real paths and open_uri can open obsidian://open?path=encoded_absolute_path. Multiple vaults require resolving which vault the user intends.",
    "media_control": "Control exact observed MPRIS player id: play, pause, next, previous or open_uri. open_uri needs a real supported URI found in web evidence or observed app data, not an invented track ID. It returns observed playback/track metadata and whether the requested URI was verified. A request accepted by the player is not proof of successful playback. No Spotify Web API credentials are required for its exposed desktop interface.",
    "list_directory": "List real children and metadata of path. Discover folders/configuration before choosing a file; maximum 160 entries per page. Use offset for another page.",
    "read_file": "Read up to 48,000 characters of a real UTF-8 text file at path, starting at offset. Returns SHA256 and coverage. Read relevant local configuration, notes, code or logs without requiring an attachment. Credentials and browser/keyring data are excluded.",
    "write_file": "Create, append or replace a UTF-8 file at path with content. mode defaults to create and never overwrites; append/replace require the SHA256 returned by read_file. Existing revisions are backed up; changed files cause a conflict instead of lost edits. Use actual newline characters, not literal backslash-n text. Verify content after writing.",
    "run_command": "Execute argv (array of exact arguments, no shell interpolation) in cwd. Every generic command requires confirmation in review mode, including read-only commands. Default isolation has read-only files, isolated PID/network namespaces, no desktop/system DBus, and known credential locations hidden. Use native performance/hardware tools for actual host readings. Writable home, network or session access expands the approved scope. session=true exposes actual host processes and desktop/service sockets for a necessary CLI/API operation. Set privileged=true only for a necessary administrator command: confirmation then native pkexec authentication. Timeout 1..120 seconds. Shell/code arguments are executable, not harmless text. Inspect actual exit status/stdout/stderr; do not claim success from a command proposal.",
    "desktop_state": "Observe real compositor windows, installed application identities, media players and current Modesty service state. Does not read screen contents or hidden app data.",
    "desktop_action": "Execute one existing native action using action_name and action_args as a JSON object string, then observe service state. Use exact installed IDs and native validated values. Launch/close applications, media, reminders, appearance, focus and other supported controls. Media actions accept id=exact observed MPRIS player DBus name to target that player. A launch request does not prove an app opened.",
    "open_uri": "Open uri through its installed native handler (files, websites or application URI navigation). Derive an app-specific URI from verified documentation/configuration, never invent a successful navigation. Only requests for that destination authorize this operation."
}
FIELDS={"list_directory":{"path","offset"},"read_file":{"path","offset"},"write_file":{"path","content","mode","expected_sha256"},
    "application_interfaces":{"wait_seconds"},"media_control":{"id","operation","uri"},
    "run_command":{"argv","cwd","timeout","writable","network","session","privileged"},"desktop_state":set(),
    "desktop_action":{"action_name","action_args"},"open_uri":{"uri"}}
PROPERTIES={"purpose":{"type":"STRING"},
    "wait_seconds":{"type":"INTEGER"}, "id":{"type":"STRING"}, "operation":{"type":"STRING","enum":["play","pause","next","previous","open_uri"]},
    "path":{"type":"STRING"}, "offset":{"type":"INTEGER"}, "content":{"type":"STRING"},
    "mode":{"type":"STRING","enum":["create","append","replace"]}, "expected_sha256":{"type":"STRING"},
    "argv":{"type":"ARRAY","items":{"type":"STRING"}}, "cwd":{"type":"STRING"}, "timeout":{"type":"INTEGER"},
    "writable":{"type":"BOOLEAN"}, "network":{"type":"BOOLEAN"}, "privileged":{"type":"BOOLEAN"},
    "session":{"type":"BOOLEAN"},
    "action_name":{"type":"STRING"}, "action_args":{"type":"STRING"}, "uri":{"type":"STRING"}
}
REQUIRED={"list_directory":["path"],"read_file":["path"],"write_file":["path","content","mode"],
    "application_interfaces":[],"media_control":["id","operation"],
    "run_command":["argv","writable","network","privileged"],"desktop_state":[],"desktop_action":["action_name","action_args"],"open_uri":["uri"]}
SCHEMA={"type":"ARRAY","description":"Next necessary real tools; maximum three independent calls. Dependent steps wait for real results. Empty when done.","items":{"anyOf":[{
    "type":"OBJECT","description":CATALOG[name],"properties":{"name":{"type":"STRING","enum":[name]},**{key:PROPERTIES[key] for key in ["purpose",*sorted(FIELDS[name])]}},
    "required":["name","purpose",*REQUIRED[name]],"propertyOrdering":["name","purpose",*sorted(FIELDS[name])]
} for name in CATALOG]}}


def private_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary=Path(stream.name)
        stream.write(json.dumps(value,ensure_ascii=False))
    temporary.chmod(0o600)
    temporary.replace(path)


def checked_path(value):
    if not isinstance(value,str) or not value.strip() or len(value)>4096 or "\0" in value:
        raise ValueError("Invalid filesystem path")
    path=Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("Use an absolute filesystem path")
    path=path.resolve()
    if any(path==p.resolve() or p.resolve() in path.parents for p in PROTECTED+[Path("/proc"), STATE]) or any(p.name.startswith(".env") for p in (path,*path.parents)) or path.suffix in {".key",".pem",".p12"}:
        raise ValueError("Credentials, browser data and internal execution records cannot be shared with the model")
    return path


def validated(call):
    if not isinstance(call,dict) or call.get("name") not in CATALOG or not isinstance(call.get("purpose"),str) or not 1<=len(call["purpose"])<=240:
        raise ValueError("Invalid system tool")
    name=call["name"]
    allowed={"name","purpose"}
    call={key:value for key,value in call.items() if key in allowed|FIELDS[name]}
    if name=="application_interfaces":
        wait=call.get("wait_seconds",0)
        if type(wait) is not int or not 0<=wait<=6: raise ValueError("Invalid interface wait")
        call["wait_seconds"]=wait
    elif name=="media_control":
        if not re.fullmatch(r"org\.mpris\.MediaPlayer2\.[A-Za-z0-9_.-]+",str(call.get("id",""))): raise ValueError("Use an observed MPRIS player ID")
        if call.get("operation") not in {"play","pause","next","previous","open_uri"}: raise ValueError("Invalid media operation")
        if call["operation"]=="open_uri":
            uri=call.get("uri","")
            if not isinstance(uri,str) or len(uri)>4096 or not re.match(r"[A-Za-z][A-Za-z0-9+.-]*:",uri) or uri.lower().startswith(("javascript:","data:")) or any(c in uri for c in "\r\n\0"): raise ValueError("Invalid media URI")
    elif name in {"list_directory","read_file","write_file"}:
        call["path"]=str(checked_path(call.get("path")))
        if name!="write_file":
            offset=call.get("offset",0)
            if type(offset) is not int or not 0<=offset<=10_000_000: raise ValueError("Invalid read offset")
            call["offset"]=offset
        else:
            call.setdefault("mode","create")
            if call.get("mode") not in {"create","append","replace"}: raise ValueError("write_file mode must be create, append or replace")
            if not isinstance(call.get("content"),str): raise ValueError("write_file requires content containing the complete UTF-8 text to save")
            if len(call["content"].encode())>256_000: raise ValueError("File edit exceeds 256 KB")
            if call["mode"]!="create" and not re.fullmatch(r"[a-f0-9]{64}",str(call.get("expected_sha256",""))):
                raise ValueError("Read the existing file and supply its SHA256 before editing")
    elif name=="run_command":
        argv=call.get("argv")
        if not isinstance(argv,list) or not 1<=len(argv)<=96 or any(not isinstance(arg,str) or "\0" in arg for arg in argv) or not argv[0] or sum(len(arg) for arg in argv)>16000:
            raise ValueError("Command requires a valid argument array")
        for field in ("writable","network","session","privileged"):
            if type(call.get(field,False)) is not bool: raise ValueError("Invalid command permissions")
            call[field]=call.get(field,False)
        call["cwd"]=str(checked_path(call.get("cwd",str(Path.home()))))
        if not Path(call["cwd"]).is_dir(): raise ValueError("Command working directory is unavailable")
        timeout=call.get("timeout",30)
        if type(timeout) is not int or not 1<=timeout<=120: raise ValueError("Invalid command timeout")
        call["timeout"]=timeout
    elif name=="desktop_action":
        if not isinstance(call.get("action_name"),str) or not isinstance(call.get("action_args"),str): raise ValueError("Invalid native action")
        if not isinstance(json.loads(call["action_args"]),dict): raise ValueError("Native arguments must be an object")
    elif name=="open_uri":
        uri=call.get("uri","")
        if not isinstance(uri,str) or len(uri)>4096 or not re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:",uri) or uri.lower().startswith(("javascript:","data:")) or any(c in uri for c in "\r\n\0"):
            raise ValueError("Invalid native URI")
    return call


def call_id(call):
    return hashlib.sha256(json.dumps({k:v for k,v in call.items() if k!="purpose"},sort_keys=True).encode()).hexdigest()


def observational(call):
    return call["name"] in {"list_directory","read_file","desktop_state","application_interfaces"} or call["name"]=="run_command" and not any(call[k] for k in ("writable","network","session","privileged"))


def media_bus():
    import gi
    gi.require_version("Gio","2.0")
    from gi.repository import Gio, GLib
    return Gio.bus_get_sync(Gio.BusType.SESSION,None), GLib


def media_properties(bus, variant, player, interface):
    return bus.call_sync(player,"/org/mpris/MediaPlayer2","org.freedesktop.DBus.Properties","GetAll",variant.Variant("(s)",(interface,)),None,0,2000,None).unpack()[0]


def media_players():
    bus, variant=media_bus()
    names=bus.call_sync("org.freedesktop.DBus","/org/freedesktop/DBus","org.freedesktop.DBus","ListNames",None,None,0,2000,None).unpack()[0]
    players=[]
    for name in names:
        if not name.startswith("org.mpris.MediaPlayer2."): continue
        try:
            base=media_properties(bus,variant,name,"org.mpris.MediaPlayer2")
            state=media_properties(bus,variant,name,"org.mpris.MediaPlayer2.Player")
            metadata=state.get("Metadata",{})
            players.append({"id":name,"identity":base.get("Identity",""),"desktopEntry":base.get("DesktopEntry",""),"schemes":base.get("SupportedUriSchemes",[]),
                "status":state.get("PlaybackStatus",""),"canPlay":state.get("CanPlay",False),"canPause":state.get("CanPause",False),"canControl":state.get("CanControl",False),
                "canNext":state.get("CanGoNext",False),"canPrevious":state.get("CanGoPrevious",False),
                "track":{"title":metadata.get("xesam:title",""),"artists":metadata.get("xesam:artist",[]),"url":metadata.get("xesam:url",""),"id":metadata.get("mpris:trackid","")}})
        except variant.Error: continue
    return players


def application_interfaces(wait_seconds=0):
    if wait_seconds: time.sleep(wait_seconds)
    vaults=[]
    config=Path(os.environ.get("XDG_CONFIG_HOME",Path.home()/".config"))/"obsidian"/"obsidian.json"
    if config.is_file():
        for identifier,record in json.loads(config.read_text()).get("vaults",{}).items():
            try:
                path=checked_path(record.get("path"))
                if path.is_dir(): vaults.append({"id":identifier,"name":path.name,"path":str(path),"open":record.get("open") is True})
            except ValueError: continue
    try:
        players=media_players(); media_error=""
    except Exception as error:
        players=[]; media_error="Media interface unavailable: "+str(error)[:200]
    return {"ok":True,"vaults":vaults,"players":players,"mediaError":media_error,"cli":{name:shutil.which(name) for name in ("obsidian","playerctl","spotify","xdg-open")}}


def media_control(call):
    bus,variant=media_bus()
    before=next((p for p in media_players() if p["id"]==call["id"]),None)
    if not before: raise ValueError("Requested player is not ready; wait for its interface after launch")
    op=call["operation"]
    capability={"play":"canPlay","pause":"canPause","next":"canNext","previous":"canPrevious","open_uri":"canControl"}[op]
    if not before[capability]: raise ValueError("Player does not support requested control")
    if op=="open_uri" and call["uri"].split(":",1)[0] not in before["schemes"]: raise ValueError("Player does not advertise this URI scheme; use its native URI handler instead, then verify the track")
    method={"play":"Play","pause":"Pause","next":"Next","previous":"Previous","open_uri":"OpenUri"}[op]
    bus.call_sync(call["id"],"/org/mpris/MediaPlayer2","org.mpris.MediaPlayer2.Player",method,variant.Variant("(s)",(call["uri"],)) if op=="open_uri" else None,None,0,3000,None)
    deadline=time.monotonic()+3
    observed=None; verified=False
    while time.monotonic()<deadline:
        observed=next((p for p in media_players() if p["id"]==call["id"]),None)
        if not observed: break
        verified=(observed["status"]=="Playing" if op=="play" else observed["status"]=="Paused" if op=="pause" else bool(observed["track"]["id"] and observed["track"]!=before["track"]) if op in {"next","previous"} else observed["track"]["url"]==call["uri"])
        if verified: break
        time.sleep(.25)
    return {"ok":True,"status":"verified" if verified else "requested","verified":verified,"player":observed,
        "note":"Observed requested state." if verified else "Player accepted the method; requested result is not verified. Inspect actual track before claiming completion."}


def ipc(method, *args):
    result=subprocess.run(["qs","-p",str(ROOT),"ipc","call","luma",method,*args],capture_output=True,text=True,timeout=8)
    if result.returncode: raise RuntimeError("Native desktop service did not respond")
    return json.loads(result.stdout)


def unlocked():
    result=subprocess.run(["qs","-p",str(ROOT),"ipc","call","island","health"],capture_output=True,text=True,timeout=5)
    if result.returncode or json.loads(result.stdout).get("locked",True):
        raise RuntimeError("Unlock normally before Luma performs system work")


def command(call, approved=False):
    if not approved:
        raise ValueError("This command needs concrete approval before execution")
    argv=call["argv"]
    executable=shutil.which(argv[0])
    if not executable: raise ValueError("Command is not installed: "+Path(argv[0]).name)
    if call["privileged"]:
        argv=["pkexec",executable,*argv[1:]]
    else:
        if not shutil.which("bwrap"): raise ValueError("Read-only command isolation needs bubblewrap; command was not run")
        sandbox=["bwrap","--die-with-parent","--new-session","--ro-bind","/","/","--proc","/proc","--dev","/dev"]
        if not call["session"]: sandbox += ["--unshare-pid"]
        if call["writable"]: sandbox += ["--bind",str(Path.home()),str(Path.home())]
        if not call["network"]: sandbox += ["--unshare-net"]
        for path in PROTECTED+[STATE]:
            if path.exists(): sandbox += ["--tmpfs",str(path)] if path.is_dir() else ["--ro-bind","/dev/null",str(path)]
        # Session sockets can mutate applications even with read-only files.
        # Native desktop tools own IPC; generic read commands do not get it.
        runtime=os.environ.get("XDG_RUNTIME_DIR")
        if not call["session"]:
            if runtime and Path(runtime).exists(): sandbox += ["--tmpfs",runtime]
            if Path("/run/dbus").exists(): sandbox += ["--tmpfs","/run/dbus"]
        sandbox += ["--chdir",call["cwd"],"--",executable,*argv[1:]]
        argv=sandbox
    env={k:v for k,v in os.environ.items() if k in {"PATH","HOME","USER","LOGNAME","LANG","LC_ALL","LC_CTYPE","TZ"}}
    # pkexec needs the live session for its native authentication agent.
    if call["privileged"] or call["session"]:
        for key in ("XDG_RUNTIME_DIR","DBUS_SESSION_BUS_ADDRESS","DISPLAY","WAYLAND_DISPLAY","HYPRLAND_INSTANCE_SIGNATURE"):
            if key in os.environ: env[key]=os.environ[key]
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process=subprocess.Popen(argv,cwd=call["cwd"],env=env,stdout=out,stderr=err,start_new_session=True)
        timed_out=False
        try: process.wait(timeout=call["timeout"])
        except subprocess.TimeoutExpired:
            timed_out=True
            os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL); process.wait()
        total=out.tell()+err.tell(); out.seek(0); err.seek(0)
        return {"ok":process.returncode==0 and not timed_out,"exitCode":process.returncode,"timedOut":timed_out,
            "stdout":out.read(20000).decode(errors="replace"),"stderr":err.read(6000).decode(errors="replace"),"truncated":total>26000,
            "isolation":"native authentication" if call["privileged"] else "read-only system; writable home" if call["writable"] else "read-only system",
            "hostProcesses":call["privileged"] or call["session"],"hostNetwork":call["privileged"] or call["network"]}


def execute(call, native_action, approved=False):
    unlocked()
    call=validated(call)
    name=call["name"]
    if name=="application_interfaces": return application_interfaces(call["wait_seconds"])
    if name=="media_control":
        try: return media_control(call)
        except Exception as error: raise ValueError("Media control failed: "+str(error)[:400]) from error
    if name=="desktop_action": return native_action(call["action_name"],json.loads(call["action_args"]))
    if name=="desktop_state":
        import gi
        gi.require_version("Gio","2.0")
        from gi.repository import Gio
        clients=json.loads(subprocess.check_output(["hyprctl","-j","clients"],timeout=3))
        windows=[{k:c.get(k) for k in ("address","class","title","pid","workspace")} for c in clients]
        media=subprocess.run(["playerctl","-l"],capture_output=True,text=True,timeout=3) if shutil.which("playerctl") else None
        applications=[{"id":entry.get_id(),"name":entry.get_display_name()} for entry in Gio.AppInfo.get_all() if entry.get_id() and entry.should_show()][:512]
        return {"ok":True,"windows":windows,"applications":applications,"services":ipc("snapshot"),"mediaPlayers":media.stdout.splitlines() if media else []}
    if name=="run_command": return command(call,approved)
    if name=="open_uri":
        import gi
        gi.require_version("Gio","2.0")
        from gi.repository import Gio
        ok=Gio.AppInfo.launch_default_for_uri(call["uri"],None)
        return {"ok":bool(ok),"status":"requested","uri":call["uri"],"note":"The handler accepted the URI; application navigation has not been verified."}
    path=checked_path(call["path"])
    if name=="list_directory":
        entries=sorted(path.iterdir(),key=lambda p:(not p.is_dir(),p.name.casefold()))
        rows=[]
        for p in entries[call["offset"]:call["offset"]+160]:
            try: rows.append({"name":p.name,"type":"directory" if p.is_dir() else "file","bytes":p.stat().st_size})
            except OSError: rows.append({"name":p.name,"type":"unavailable"})
        return {"ok":True,"path":str(path),"entries":rows,"total":len(entries),"nextOffset":call["offset"]+len(rows) if call["offset"]+len(rows)<len(entries) else None}
    if name=="read_file":
        if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size>4_000_000: raise ValueError("Use a document tool or bounded command for this large/non-text file")
        data=path.read_bytes(); text=data.decode("utf-8")
        if "\0" in text: raise ValueError("File is not UTF-8 text")
        start=call["offset"]; end=min(len(text),start+48000)
        return {"ok":True,"path":str(path),"content":text[start:end],"sha256":hashlib.sha256(data).hexdigest(),"characters":len(text),"offset":start,"nextOffset":end if end<len(text) else None}
    data=call["content"].encode()
    path.parent.mkdir(parents=True,exist_ok=True)
    if call["mode"]=="create":
        with path.open("xb") as stream: stream.write(data)
    else:
        # Keep an advisory lock through the hash check and atomic replacement.
        import fcntl
        with path.open("rb") as source:
            fcntl.flock(source,fcntl.LOCK_EX)
            old=source.read()
            if hashlib.sha256(old).hexdigest()!=call["expected_sha256"]: raise ValueError("File changed since it was read. Read again before editing.")
            revision=STATE/"revisions"/(uuid.uuid4().hex+".bak")
            revision.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            revision.write_bytes(old); revision.chmod(0o600)
            if call["mode"]=="append": data=old+data
            with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as stream:
                temporary=Path(stream.name); stream.write(data); stream.flush(); os.fsync(stream.fileno())
            temporary.chmod(stat.S_IMODE(path.stat().st_mode)); temporary.replace(path)
    return {"ok":True,"path":str(path),"bytes":len(data),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"status":"written"}


def defer(payload, ledger, call, detail):
    token=uuid.uuid4().hex
    private_write(STATE/(token+".json"),{"created":time.time(),"status":"pending","payload":payload,"ledger":ledger,"call":call})
    return {"name":"system_step","args":{"id":token,"detail":detail},"label":call["purpose"],"status":"pending"}


def checkpoint(payload, ledger, token=None, status="active"):
    if token is None:
        for directory,lifetime in ((STATE,1800),(STATE/"runs",86400)):
            for path in directory.glob("*.json"):
                try:
                    if time.time()-json.loads(path.read_text()).get("created",0)>lifetime:
                        path.unlink();path.with_suffix(".lock").unlink(missing_ok=True)
                except (OSError,ValueError,TypeError): pass
    token=token or uuid.uuid4().hex
    if not re.fullmatch(r"[a-f0-9]{32}",token): raise ValueError("Invalid task checkpoint")
    payload=dict(payload,_systemRun=token)
    private_write(STATE/"runs"/(token+".json"),{"created":time.time(),"status":status,"payload":payload,"ledger":ledger})
    return token


@contextmanager
def continue_run(token):
    if not isinstance(token,str) or not re.fullmatch(r"[a-f0-9]{32}",token): raise ValueError("Invalid task checkpoint")
    with (STATE/"runs"/(token+".lock")).open("a") as lock:
        import fcntl
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError("Task is already running; it was not replayed") from None
        job=json.loads((STATE/"runs"/(token+".json")).read_text())
        if job.get("status")=="done": raise ValueError("Task already finished; completed steps were not replayed")
        if time.time()-job["created"]>86400: raise ValueError("Task checkpoint expired; inspect completed steps before making a new request")
        yield job


def resume(token, native_action):
    if not isinstance(token,str) or not re.fullmatch(r"[a-f0-9]{32}",token): raise ValueError("Invalid execution ticket")
    path=STATE/(token+".json")
    with (STATE/(token+".lock")).open("a") as lock:
        import fcntl
        fcntl.flock(lock,fcntl.LOCK_EX)
        job=json.loads(path.read_text())
        if job.get("status")!="pending" or time.time()-job["created"]>1800: raise ValueError("This approval expired or was already used")
        unlocked()
        # Consume BEFORE execution; crash/reload must never replay a side effect.
        job["ledger"].append({"id":call_id(job["call"]),"tool":job["call"],"result":{"ok":False,"status":"outcome_unknown","error":"Approved step started; inspect actual state before repeating it."},"at":time.time()})
        job["status"]="started"; private_write(path,job)
        run=job["payload"].get("_systemRun")
        if run: checkpoint(job["payload"],job["ledger"],run)
    try: result=execute(job["call"],native_action,approved=True)
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error: result={"ok":False,"error":str(error)}
    job["ledger"][-1]["result"]=result
    job["status"]="completed"; private_write(path,job)
    if run: checkpoint(job["payload"],job["ledger"],run)
    payload=job["payload"]; payload["_systemLedger"]=job["ledger"]
    return payload
