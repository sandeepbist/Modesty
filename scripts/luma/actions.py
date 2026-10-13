"""Validate proposed desktop actions and explicitly attached paths."""
from datetime import date, datetime
import math
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pathlib import Path
import re
import time

PANELS = {"settings", "quicksettings", "calendar", "themes", "wallpapers", "wifi", "bluetooth", "display", "sound", "media", "notifhistory", "focus", "performance", "notes", "recorder", "privacy", "power", "launcher"}

S = {"type": "STRING"}
N = {"type": "NUMBER"}
I = {"type": "INTEGER"}
B = {"type": "BOOLEAN"}
REPEAT_SCHEMA = {"type":"OBJECT", "properties":{"kind":{"type":"STRING","enum":["none","daily","weekly","monthly"]},"interval":I,"weekdays":{"type":"ARRAY","items":I},"anchorDay":I}, "required":["kind"]}
PREFERENCES = {
    **{key: B for key in ("remindersEnabled", "deviceIndicator", "contextDevices", "contextBattery", "compactMissingLyrics", "launcherCalculator", "launcherDescriptions", "matugenAutomatic", "themeGtk", "themeFolders", "themeQt", "themeFoot", "themeSpotify", "footerTray", "footerVisible", "footerThemes", "footerWallpapers", "footerPower", "footerSettings", "recordCursor", "crispText", "liveMedia", "mediaAutoHide", "focusQuiet", "footerPerformance", "mediaVisualizer", "mediaLyrics", "fuzzyApps", "rememberApps", "terminalGreeting", "terminalArtFavoritesOnly", "terminalArtMinimal", "companionEnabled", "companionZen", "companionTerminal", "agentFeedback", "contextWorkspace", "contextVolume", "contextBrightness", "welcomeAtLogin", "contextEvents", "wallpaperColors", "use24Hour", "showSeconds", "showAlbum", "showStatus", "shadows")},
    **{key: {"type":"NUMBER","minimum":low,"maximum":high} for key, low, high in (("focusMinutes",1,120),("breakMinutes",1,60),("recordCountdown",0,5),("matugenContrast",-1,1),("matugenSource",0,4),("wallpaperDuration",.2,.7),("windowGap",-32,40),("trayIconSize",16,24),("traySpacing",0,12),("controlGap",4,16),("controlRadius",8,24),("controlIconSize",18,30),("sliderThickness",4,14),("terminalArtSize",24,60),("launcherVisibleRows",3,8),("companionSize",40,90),("companionInset",0,160),("contextDuration",800,4000),("tooltipDelay",150,1000),("hoverLift",0,10),("motionSpeed",.65,1.5),("notificationDuration",2000,12000),("uiScale",.85,1.25),("topMargin",0,32),("barHeight",28,44),("collapsedWidth",72,150),("clusterGap",6,28),("expandedRadius",16,36),("innerPadding",6,16),("mediaWidth",300,440),("controlsWidth",340,440),("launcherWidth",420,680),("calendarWidth",280,400))},
    **{key:{"type":"STRING","enum":values} for key,values in {"motion":["fluid","gentle","instant"],"wallpaperTransition":["none","fade"],"fontFamily":["Instrument Sans","Inter Variable","Adwaita Sans"],"clockFontFamily":["Instrument Sans","Inter Variable","Adwaita Sans"],"companionSide":["left","right"],"terminal":["foot","kitty","alacritty","wezterm"],"terminalArtMode":["original","theme"],"terminalArtFormat":["image","ascii"],"terminalArtCollection":["atelier","portraits","legends","all"],"matugenScheme":["scheme-content","scheme-expressive","scheme-fidelity","scheme-fruit-salad","scheme-monochrome","scheme-neutral","scheme-rainbow","scheme-tonal-spot","scheme-vibrant","scheme-smart"]}.items()},
    "recordFps":{"type":"INTEGER","enum":[30,60]}
}
CATALOG = {}
for key, specification in PREFERENCES.items():
    if specification["type"] == "NUMBER" and key not in {"uiScale", "matugenContrast", "wallpaperDuration", "motionSpeed"}:
        specification["type"] = "INTEGER"
def register(names, description, fields=None, required=(), review=False):
    for name in names.split():
        CATALOG[name] = {"description":description, "fields":fields or {}, "required":list(required), "review":review}
register("open_app close_app", "Launch or gracefully close an exact installed application.", {"id":S}, ["id"])
register("volume brightness", "Set observed audio volume or display brightness percentage.", {"level":N}, ["level"])
register("focus", "Start focus timer. Changing duration restarts it.", {"minutes":I}, ["minutes"])
register("focus_pause", "Pause or resume active focus timer.", {"paused":B})
register("focus_cancel", "End focus timer.")
register("appearance", "Set appearance mode.", {"mode":{"type":"STRING","enum":["light","dark"]}}, ["mode"])
register("awake", "Keep screen awake for optional seconds or indefinitely.", {"enabled":B,"seconds":N}, ["enabled"])
register("peace nightlight wifi bluetooth", "Set notifications peace, night light, Wi-Fi or Bluetooth enabled state.", {"enabled":B}, ["enabled"])
register("audio_mute microphone_mute", "Set output or microphone mute, optionally exact observed device id.", {"muted":B,"id":S}, ["muted"])
register("audio_device", "Choose exact observed output or input audio device.", {"id":S,"direction":{"type":"STRING","enum":["output","input"]}}, ["id","direction"])
register("microphone_volume", "Set microphone volume percentage, optionally observed device id.", {"level":N,"id":S}, ["level"])
register("wifi_connect wifi_disconnect wifi_forget", "Operate on exact observed Wi-Fi network id. Password and enterprise authentication stay in native Wi-Fi panel.", {"id":S}, ["id"])
register("bluetooth_connect bluetooth_disconnect bluetooth_pair bluetooth_forget", "Operate on exact observed Bluetooth device id. Pairing confirmation remains native.", {"id":S}, ["id"])
register("media_pause media_play media_next media_previous media_stop", "Control observed MPRIS player, default active player.", {"id":S})
register("media_seek", "Seek observed player to position in seconds.", {"id":S,"seconds":N}, ["seconds"])
register("media_repeat", "Set repeat off, track or playlist when player supports it.", {"id":S,"mode":{"type":"STRING","enum":["none","track","playlist"]}}, ["mode"])
register("media_shuffle", "Set shuffle when observed player supports it.", {"id":S,"enabled":B}, ["enabled"])
register("recording_start", "Start native screen recording, optional region selection and sound.", {"region":B,"sound":B})
register("recording_pause", "Pause or resume current recording.", {"paused":B}, ["paused"])
register("recording_stop", "Finish and save current recording.")
register("notification_dismiss", "Dismiss exact observed notification id.", {"id":S}, ["id"])
register("notification_clear", "Clear notification history.")
register("palette", "Select observed palette name.", {"name":S}, ["name"])
register("wallpaper", "Apply exact observed wallpaper path.", {"path":S}, ["path"])
register("display", "Set observed monitor mode and scale. Native display rollback confirmation remains mandatory.", {"id":S,"mode":S,"scale":N}, ["id","mode","scale"], True)
register("preference", "Set supported presentation preferences. Access, credentials and privacy permissions cannot be changed.", {"key":{"type":"STRING","enum":sorted(PREFERENCES)},"value":{"anyOf":[S,N,B]}}, ["key","value"])
register("lock", "Lock session through native authentication boundary.")
register("sleep", "Lock then suspend using native sleep mode.", {"mode":{"type":"STRING","enum":["suspend","hibernate","hybrid-sleep","suspend-then-hibernate"]}}, ["mode"], True)
register("system", "Explicitly reviewed logout, reboot or power off.", {"operation":{"type":"STRING","enum":["logout","reboot","poweroff"]}}, ["operation"], True)
register("update", "Check, download, apply, rollback or reload through native updater validation.", {"operation":{"type":"STRING","enum":["check","download","apply","rollback","reload"]}}, ["operation"], True)
register("open_panel", "Open native desktop panel.", {"panel":{"type":"STRING","enum":sorted(PANELS)}}, ["panel"])
reminder_fields={"title":S,"date":S,"time":S,"lead":I,"count":I,"dueAt":N,"repeat":REPEAT_SCHEMA,"zone":S}
register("reminder", "Create reminder. lead/count are finite advance notices; repeat is calendar recurrence with IANA zone.", reminder_fields, ["title","date","time"])
register("reminder_update", "Update observed reminder with actual revision. Preserve repeat unless explicitly changed.", {**reminder_fields,"id":S,"expectedRevision":I}, ["id","title","dueAt"])
register("reminder_remove reminder_complete", "Cancel a reminder series or complete its current occurrence. Completion advances recurring series.", {"id":S,"expectedRevision":I}, ["id"])
register("note_create", "Create Quick Note with optional title and plain UTF-8 Markdown body.", {"title":S,"body":S}, ["body"])
register("note_update note_append", "Update or append to observed Quick Note. Read actual revision first. Dirty UI drafts reject mutation.", {"id":S,"expectedRevision":I,"title":S,"body":S}, ["id","expectedRevision"])
register("note_pin", "Pin or unpin active note.", {"id":S,"expectedRevision":I,"pinned":B}, ["id","expectedRevision","pinned"])
register("note_archive note_trash note_restore note_delete", "Archive, move to recoverable Trash, restore or permanently delete observed Quick Note. Permanent deletion requires review.", {"id":S,"expectedRevision":I}, ["id","expectedRevision"])
for name in ("reminder_remove","note_delete","wifi_forget","bluetooth_forget"): CATALOG[name]["review"]=True
register("note_open", "Select observed note and open native Notes editor.", {"id":S}, ["id"])
register("note_export", "Export observed Quick Notes as new Markdown files, never overwrite existing files.", {"ids":{"type":"ARRAY","items":S},"destination":S}, ["ids"])
register("file_action", "Create compressed, merged or resized copies of explicitly attached files.", {"operation":S,"paths":{"type":"ARRAY","items":S},"width":I,"format":S}, ["operation","paths"])
ACTIONS = set(CATALOG)
ACTION_SCHEMA={"type":"ARRAY", "items":{"anyOf":[{"type":"OBJECT","description":entry["description"],"properties":{"name":{"type":"STRING","enum":[name]},"args":{"type":"OBJECT","properties":entry["fields"],"required":entry["required"]}},"required":["name","args"]} for name,entry in CATALOG.items()]}}

def action_instructions():
    return "\n".join(name+" "+json_fields(entry)+". "+entry["description"] for name,entry in CATALOG.items())

def json_fields(entry):
    return "{"+", ".join(key+("" if key in entry["required"] else "?")+":"+field["type"].lower() if "type" in field else key+":value" for key,field in entry["fields"].items())+"}"


def protected_notes_path(path):
    state=Path(os.environ.get("XDG_STATE_HOME",Path.home()/".local/state"))/"modesty"
    path=Path(path).expanduser().resolve()
    return path.parent==state.resolve() and (path.name.startswith("notes") or path.name.startswith(".notes-")) or (state/"notes").resolve()==path or (state/"notes").resolve() in path.parents


def checked_repeat(value):
    if not isinstance(value,dict) or value.get("kind") not in {"none","daily","weekly","monthly"}:
        raise ValueError("Invalid reminder recurrence")
    interval=value.get("interval",1)
    if type(interval) is not int or not 1<=interval<=365: raise ValueError("Invalid recurrence interval")
    clean={"kind":value["kind"],"interval":interval}
    if "weekdays" in value:
        weekdays=value["weekdays"]
        if not isinstance(weekdays,list) or not weekdays or any(type(day) is not int or not 1<=day<=7 for day in weekdays): raise ValueError("Invalid recurrence weekdays")
        clean["weekdays"]=sorted(set(weekdays))
    if "anchorDay" in value:
        anchor=value["anchorDay"]
        if type(anchor) is not int or not 1<=anchor<=31: raise ValueError("Invalid monthly anchor")
        clean["anchorDay"]=anchor
    return clean


def validated_action(action, applications=(), reminders=(), attached_paths=(), notes=(), desktop=None):
    if not isinstance(action, dict) or action.get("name") not in ACTIONS or not isinstance(action.get("args"), dict):
        raise ValueError("Unsupported action")
    name, args = action["name"], action["args"]
    desktop=desktop or {}
    def number(key, low, high):
        value = args.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError("Invalid " + key)
        return value
    def observed(key, identifier):
        rows=desktop.get(key,[])
        row=next((row for row in rows if isinstance(row,dict) and str(row.get("id"))==identifier),None)
        if not isinstance(identifier,str) or not row: raise ValueError("Choose an observed "+key+" target")
        return row
    if name.startswith("note_"):
        clean={}
        if name not in {"note_create","note_export"}:
            identifier=args.get("id")
            note=next((n for n in notes if isinstance(n,dict) and n.get("id")==identifier),None)
            if not isinstance(identifier,str) or not note: raise ValueError("Note is no longer available. List or read notes again.")
            clean["id"]=identifier
            if name!="note_open":
                revision=args.get("expectedRevision")
                if type(revision) is not int or revision<1: raise ValueError("Read note revision before editing")
                if note.get("revision")!=revision: raise ValueError("Note changed. Read it again before editing.")
                if note.get("dirty"): raise ValueError("Note has unsaved typing. Save it before Luma edits it.")
                clean["expectedRevision"]=revision
        if name in {"note_create","note_update","note_append"}:
            for key in ("title","body"):
                if key in args:
                    if not isinstance(args[key],str) or len(args[key].encode())>(512 if key=="title" else 256000): raise ValueError("Invalid note "+key)
                    clean[key]=args[key]
            if name=="note_create" and not (clean.get("title","").strip() or clean.get("body","").strip()): raise ValueError("Write note content first")
            if name=="note_append" and not clean.get("body"): raise ValueError("Append needs note text")
            if name=="note_update" and not any(key in clean for key in ("title","body")): raise ValueError("Choose note content to update")
        if name=="note_pin":
            if type(args.get("pinned")) is not bool: raise ValueError("Invalid pin state")
            clean["pinned"]=args["pinned"]
        if name=="note_delete" and note.get("status")!="trash": raise ValueError("Move note to Trash before permanent deletion")
        if name=="note_export":
            ids=args.get("ids")
            if not isinstance(ids,list) or not ids or len(ids)>1000 or any(not isinstance(i,str) or i not in {n.get("id") for n in notes} for i in ids): raise ValueError("Choose observed notes to export")
            clean["ids"]=list(dict.fromkeys(ids))
            if "destination" in args:
                destination=args["destination"]
                if not isinstance(destination,str) or not Path(destination).expanduser().is_absolute() or protected_notes_path(destination): raise ValueError("Choose a Markdown export folder")
                clean["destination"]=destination
        label=name.replace("note_", "").replace("_"," ").title()+" note"
    elif name in {"audio_mute","microphone_mute","audio_device","microphone_volume"}:
        direction=args.get("direction") if name=="audio_device" else "input" if name.startswith("microphone") else "output"
        if direction not in {"input","output"}: raise ValueError("Invalid audio direction")
        clean={}
        if "id" in args or name=="audio_device":
            row=observed("audioInputs" if direction=="input" else "audioOutputs",args.get("id"));clean["id"]=str(row["id"])
        if name=="audio_device": clean["direction"]=direction
        elif name=="microphone_volume": clean["level"]=number("level",0,100)
        else:
            if type(args.get("muted")) is not bool: raise ValueError("Invalid mute state")
            clean["muted"]=args["muted"]
        label=name.replace("_"," ").title()
    elif name in {"wifi","bluetooth"}:
        if type(args.get("enabled")) is not bool: raise ValueError("Invalid toggle")
        clean={"enabled":args["enabled"]}; label=name.title()+" · "+("On" if args["enabled"] else "Off")
    elif name.startswith("wifi_") or name.startswith("bluetooth_"):
        row=observed("networks" if name.startswith("wifi_") else "bluetoothDevices",args.get("id"))
        clean={"id":args["id"]};label=name.replace("_"," ").title()+" · "+str(row.get("name",""))[:120]
    elif name in {"media_seek","media_repeat","media_shuffle","media_stop"}:
        clean={}
        if "id" in args:
            if not isinstance(args["id"],str) or not re.fullmatch(r"org\.mpris\.MediaPlayer2\.[A-Za-z0-9_.-]{1,180}",args["id"]): raise ValueError("Use an observed MPRIS player ID")
            clean["id"]=args["id"]
        if name=="media_seek":clean["seconds"]=number("seconds",0,864000)
        if name=="media_repeat":
            if args.get("mode") not in {"none","track","playlist"}:raise ValueError("Invalid repeat mode")
            clean["mode"]=args["mode"]
        if name=="media_shuffle":
            if type(args.get("enabled")) is not bool: raise ValueError("Invalid shuffle state")
            clean["enabled"]=args["enabled"]
        label=name.replace("_"," ").title()
    elif name.startswith("recording_"):
        clean={}
        for key in (("region","sound") if name=="recording_start" else ("paused",) if name=="recording_pause" else ()):
            value=args.get(key,False)
            if type(value) is not bool:raise ValueError("Invalid recording option")
            clean[key]=value
        label=name.replace("_"," ").title()
    elif name in {"notification_dismiss","notification_clear"}:
        clean={}
        if name=="notification_dismiss":observed("notifications",args.get("id"));clean["id"]=args["id"]
        label=name.replace("_"," ").title()
    elif name=="palette":
        if args.get("name") not in desktop.get("palettes",[]):raise ValueError("Choose an observed palette")
        clean={"name":args["name"]};label="Palette · "+args["name"]
    elif name=="wallpaper":
        path=args.get("path")
        if not isinstance(path,str) or path not in [r.get("path") for r in desktop.get("wallpapers",[])]:raise ValueError("Choose an observed wallpaper")
        clean={"path":path};label="Wallpaper · "+Path(path).name
    elif name=="display":
        row=observed("monitors",args.get("id"))
        mode=args.get("mode")
        modes=row.get("availableModes",row.get("modes",[]))
        if not isinstance(mode,str) or mode not in modes:raise ValueError("Choose an observed display mode")
        clean={"id":args["id"],"mode":mode,"scale":number("scale",.5,3)};label="Display · "+args["id"]
    elif name=="preference":
        key=args.get("key");value=args.get("value");spec=PREFERENCES.get(key)
        if not spec:raise ValueError("Access, privacy and credential preferences require native Settings")
        kind=spec["type"]
        if kind=="BOOLEAN" and type(value) is not bool or kind=="INTEGER" and type(value) is not int or kind=="NUMBER" and (type(value) not in (int,float) or not math.isfinite(value)) or kind=="STRING" and not isinstance(value,str):raise ValueError("Invalid preference value")
        if "enum" in spec and value not in spec["enum"] or "minimum" in spec and not spec["minimum"]<=value<=spec["maximum"]:raise ValueError("Preference value outside supported range")
        fractional={"uiScale","matugenContrast","wallpaperDuration","motionSpeed"}
        if kind in {"NUMBER","INTEGER"} and key not in fractional and int(value)!=value:raise ValueError("Use whole numbers for this preference")
        clean={"key":key,"value":value};label="Preference · "+key
    elif name in {"lock","sleep","system","update"}:
        clean={}
        key="mode" if name=="sleep" else "operation"
        if name!="lock":
            if args.get(key) not in CATALOG[name]["fields"][key]["enum"]:raise ValueError("Unsupported system operation")
            clean[key]=args[key]
        label=name.title()+(" · "+str(clean.get(key,"")) if clean else "")
    elif name=="file_action":
        operation=args.get("operation")
        paths=args.get("paths")
        if operation not in {"compress","merge","export"} or not isinstance(paths,list) or not 1<=len(paths)<=3 or any(not isinstance(p,str) or p not in attached_paths for p in paths) or len(set(paths))!=len(paths):
            raise ValueError("Choose attached files for this action")
        paths=[str(attachment_file(p)) for p in paths]
        clean={"operation":operation,"paths":paths}
        if operation=="merge" and (len(paths)<2 or any(Path(p).suffix.lower()!=".pdf" for p in paths)):
            raise ValueError("Attach at least two PDFs")
        if operation=="export":
            width=number("width",1,8192)
            if int(width)!=width or args.get("format") not in {"PNG","JPEG","WEBP"} or any(Path(p).suffix.lower() not in {".png",".jpg",".jpeg",".webp"} for p in paths):
                raise ValueError("Choose valid image export options")
            clean.update(width=int(width),format=args["format"])
        label={"compress":"Create ZIP copy","merge":"Merge PDFs in listed order","export":"Save image copies"}[operation]
        if operation=="export":
            label+=f" · {clean['width']} px · {clean['format']}"
    elif name in {"open_app","close_app"}:
        installed = {app["id"]: app["name"] for app in applications if isinstance(app, dict) and isinstance(app.get("id"), str) and isinstance(app.get("name"), str)}
        identifier = args.get("id")
        if not isinstance(identifier, str) or identifier not in installed:
            raise ValueError("Application is not installed")
        clean, label = {"id": identifier}, ("Open " if name=="open_app" else "Close ") + installed[identifier][:120]
    elif name in {"volume", "brightness"}:
        clean = {"level": number("level", 0, 100)}
        label = f"{name.title()} · {clean['level']:g}%"
    elif name == "focus":
        minutes = number("minutes", 1, 120)
        if int(minutes) != minutes:
            raise ValueError("Use whole minutes")
        clean, label = {"minutes": int(minutes)}, f"Focus · {int(minutes)} minutes"
    elif name in {"awake", "peace", "nightlight"}:
        if type(args.get("enabled")) is not bool:
            raise ValueError("Invalid toggle")
        clean = {"enabled": args["enabled"]}
        if name == "awake" and args.get("seconds"):
            clean["seconds"] = number("seconds", 1, 86400)
        label = {"awake": "Keep awake", "peace": "Peace", "nightlight": "Night light"}[name] + (" · On" if args["enabled"] else " · Off")
        if clean.get("seconds"):
            label = "Keep awake · " + str(round(clean["seconds"]/60, 1)).removesuffix(".0") + " minutes"
    elif name == "appearance":
        if args.get("mode") not in {"light", "dark"}:
            raise ValueError("Invalid appearance")
        clean, label = {"mode": args["mode"]}, args["mode"].title() + " appearance"
    elif name == "open_panel":
        if args.get("panel") not in PANELS:
            raise ValueError("Unsupported panel")
        clean, label = {"panel": args["panel"]}, "Open " + args["panel"].replace("quicksettings", "control center")
    elif name in {"reminder_update", "reminder_remove", "reminder_complete"}:
        identifier = args.get("id")
        reminder = next((r for r in reminders if isinstance(r, dict) and r.get("id") == identifier), None)
        if not isinstance(identifier, str) or not reminder:
            raise ValueError("Reminder is no longer active")
        clean = {"id": identifier}
        if type(reminder.get("revision")) is int: clean["expectedRevision"]=reminder["revision"]
        if "expectedRevision" in args:
            revision=args["expectedRevision"]
            if type(revision) is not int or revision<0 or revision!=reminder.get("revision",revision): raise ValueError("Reminder changed. Read it again.")
            clean["expectedRevision"]=revision
        label = ("Complete reminder" if name=="reminder_complete" else "Remove reminder") + " · " + str(reminder.get("title", ""))[:160]
        if name == "reminder_update":
            due = number("dueAt", time.time()*1000+1, (time.time()+365*86400)*1000)
            title = args.get("title", reminder.get("title", ""))
            if not isinstance(title, str) or not title.strip() or len(title.strip()) > 160:
                raise ValueError("Invalid reminder title")
            clean.update(title=title.strip(), dueAt=due)
            if "date" in args:clean["date"]=date.fromisoformat(args["date"]).isoformat()
            if "time" in args:clean["time"]=datetime.strptime(args["time"],"%H:%M").strftime("%H:%M")
            label = title.strip() + " · " + datetime.fromtimestamp(due/1000).astimezone().strftime("%d %b · %H:%M")
    elif name == "reminder":
        title = str(args.get("title", "")).strip()
        day = date.fromisoformat(str(args.get("date", "")))
        when = datetime.strptime(str(args.get("time", "")), "%H:%M").strftime("%H:%M")
        args = dict(args, lead=args.get("lead", 0), count=args.get("count", 1))
        lead, count = number("lead", 0, 30), number("count", 1, 31)
        if not title or len(title) > 160 or day < date.today() or int(lead) != lead or int(count) != count or count > lead + 1:
            raise ValueError("Invalid reminder")
        clean = {"title": title, "date": day.isoformat(), "time": when, "lead": int(lead), "count": int(count)}
        if "dueAt" in args and not lead and count==1:
            timestamp=number("dueAt",time.time()*1000+1,(time.time()+365*86400)*1000)
            zone=args.get("zone")
            actual=datetime.fromtimestamp(timestamp/1000,ZoneInfo(zone)) if zone else datetime.fromtimestamp(timestamp/1000).astimezone()
            matches=actual.date()==day and actual.strftime("%H:%M")==when
            if zone and args.get("repeat",{}).get("kind","none")!="none":
                from reminders import local_timestamp
                matches=abs(local_timestamp(day.isoformat(),when,zone)-timestamp)<60000
            if not matches:
                raise ValueError("Reminder deadline does not match its date/time")
            clean["dueAt"]=timestamp
        if not lead and count == 1 and "dueAt" not in clean:
            due = datetime.combine(day, datetime.strptime(when, "%H:%M").time()).astimezone()
            if due.timestamp() <= time.time():
                raise ValueError("Invalid reminder time. Choose a future time.")
        label = title + " · " + day.isoformat() + " " + when
    elif name == "focus_pause" and "paused" in args:
        if type(args["paused"]) is not bool:
            raise ValueError("Invalid focus state")
        clean, label = {"paused": args["paused"]}, "Pause focus" if args["paused"] else "Resume focus"
    else:
        clean, label = {}, {"focus_pause": "Pause / resume focus", "focus_cancel": "End focus", "media_pause": "Pause media", "media_play": "Play media", "media_next": "Next track", "media_previous": "Previous track"}[name]
        if name.startswith("media_") and "id" in args:
            if not isinstance(args["id"],str) or not re.fullmatch(r"org\.mpris\.MediaPlayer2\.[A-Za-z0-9_.-]{1,180}",args["id"]):
                raise ValueError("Use an observed MPRIS player ID")
            clean["id"]=args["id"]
    if name in {"reminder","reminder_update"}:
        if "repeat" in args: clean["repeat"]=checked_repeat(args["repeat"])
        if "zone" in args:
            if not isinstance(args["zone"],str):raise ValueError("Use an IANA timezone")
            try: ZoneInfo(args["zone"])
            except (ZoneInfoNotFoundError,ValueError): raise ValueError("Use an IANA timezone") from None
            clean["zone"]=args["zone"]
    return {"name": name, "args": clean, "label": label, "status": "pending", "review": CATALOG[name]["review"]}



def attachment_file(path):
    file = Path(path).expanduser().resolve()
    home = Path.home().resolve()
    if protected_notes_path(file): raise ValueError("Use scoped Quick Notes tools, not generic files")
    if home not in file.parents or not file.is_file() or file.stat().st_size > 8_000_000:
        raise ValueError("Choose a file inside your home folder, up to 8 MB.")
    if any(part in {".ssh", ".gnupg", ".aws", ".azure"} for part in file.parts) or file.name.startswith(".env") or file.suffix in {".key", ".pem"}:
        raise ValueError("Credential files cannot be attached.")
    return file


def local_note_action(query, desktop, recent_tasks=()):
    text=query.strip()
    create=re.fullmatch(r'(?:create|make|take|write|save)(?: me)? (?:a |an |quick |a quick )?note\s*(?::|saying|that says)\s*(.+)',text,re.I|re.S)
    if create:
        return {"name":"note_create","args":{"body":create[1]}}
    notes=desktop.get('notes',[])
    append=re.fullmatch(r'(?:append|add)\s+(.+?)\s+to\s+(this note|the current note|that note|it)',text,re.I|re.S)
    operation=re.fullmatch(r'(pin|unpin|archive|trash|restore|open)\s+(this note|the current note|that note|it)',text,re.I)
    if not append and not operation:return None
    reference=append[2] if append else operation[2]
    identifier=desktop.get('activeNoteId','')
    if reference.lower() in {'that note','it'}:
        previous=next((task for task in reversed(recent_tasks) if task.get('name','').startswith('note_') and task.get('status') in {'persisted','verified'}),None)
        if previous:identifier=previous.get('noteId') or previous.get('args',{}).get('id') or identifier
    note=next((row for row in notes if row.get('id')==identifier),None)
    if not note:return None
    args={'id':identifier,'expectedRevision':note['revision']}
    if append:
        args['body']=append[1]
        return {'name':'note_append','args':args}
    verb=operation[1].lower()
    if verb in {'pin','unpin'}:args['pinned']=verb=='pin';verb='pin'
    if verb=='open':args.pop('expectedRevision')
    return {'name':'note_'+verb,'args':args}
