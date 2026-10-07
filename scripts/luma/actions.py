"""Validate proposed desktop actions and explicitly attached paths."""
from datetime import date, datetime
import math
from pathlib import Path
import re
import time

PANELS = {"settings", "quicksettings", "calendar", "themes", "wallpapers", "wifi", "bluetooth", "display", "sound", "media", "notifhistory", "focus", "performance"}
ACTIONS = {"open_app", "close_app", "volume", "brightness", "focus", "focus_pause", "focus_cancel", "appearance", "awake", "peace", "nightlight", "media_pause", "media_play", "media_next", "media_previous", "open_panel", "reminder", "reminder_update", "reminder_remove", "file_action"}


def validated_action(action, applications=(), reminders=(), attached_paths=()):
    if not isinstance(action, dict) or action.get("name") not in ACTIONS or not isinstance(action.get("args"), dict):
        raise ValueError("Unsupported action")
    name, args = action["name"], action["args"]
    def number(key, low, high):
        value = args.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError("Invalid " + key)
        return value
    if name=="file_action":
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
    elif name in {"reminder_update", "reminder_remove"}:
        identifier = args.get("id")
        reminder = next((r for r in reminders if isinstance(r, dict) and r.get("id") == identifier), None)
        if not isinstance(identifier, str) or not reminder:
            raise ValueError("Reminder is no longer active")
        clean = {"id": identifier}
        label = "Remove reminder · " + str(reminder.get("title", ""))[:160]
        if name == "reminder_update":
            due = number("dueAt", time.time()*1000+1, (time.time()+365*86400)*1000)
            title = args.get("title", reminder.get("title", ""))
            if not isinstance(title, str) or not title.strip() or len(title.strip()) > 160:
                raise ValueError("Invalid reminder title")
            clean.update(title=title.strip(), dueAt=due)
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
            actual=datetime.fromtimestamp(timestamp/1000).astimezone()
            if actual.date()!=day or actual.strftime("%H:%M")!=when:
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
    return {"name": name, "args": clean, "label": label, "status": "pending"}



def attachment_file(path):
    file = Path(path).expanduser().resolve()
    home = Path.home().resolve()
    if home not in file.parents or not file.is_file() or file.stat().st_size > 8_000_000:
        raise ValueError("Choose a file inside your home folder, up to 8 MB.")
    if any(part in {".ssh", ".gnupg", ".aws", ".azure"} for part in file.parts) or file.name.startswith(".env") or file.suffix in {".key", ".pem"}:
        raise ValueError("Credential files cannot be attached.")
    return file
