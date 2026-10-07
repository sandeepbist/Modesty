#!/usr/bin/env python3
"""Conservative local task parsing. Ambiguous requests stay in conversation."""
from datetime import datetime, timedelta
import re

START = re.compile(r"^(?:please\s+)?(?:remind\s+me\b|(?:set|add|create|schedule)\s+(?:me\s+)?(?:a\s+)?reminder\b)\s*", re.I)
UNITS = {"s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
         "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
         "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
         "d": 86400, "day": 86400, "days": 86400}
DURATION = r"\d+(?:\.\d+)?\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|[smhd])\b"
RELATIVE = re.compile(r"\b(?:in|after|for)\s+(" + DURATION + r"(?:\s*(?:and\s*)?" + DURATION + r")*)\s*(?:from\s+now|later)?\b", re.I)
TIME = re.compile(r"\b(?:at\s+)?(\d{1,2})(?::([0-5]\d))?\s*(am|pm)?\b", re.I)
MONTHS = {datetime(2000, i, 1).strftime(fmt).lower(): i for i in range(1, 13) for fmt in ("%b", "%B")}
WEEKDAYS = {datetime(2024, 1, i+1).strftime(fmt).lower(): i for i in range(7) for fmt in ("%a", "%A")}


def request_text(query):
    return re.sub(r"^(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?", "", query.strip(), flags=re.I).strip(" .!?")


def clock(text):
    match = TIME.fullmatch(text.strip())
    if not match:
        return None
    hour, minute, period = int(match[1]), int(match[2] or 0), (match[3] or "").lower()
    if period:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if period == "pm" else 0)
    elif not match[2] or hour > 23:
        return None  # Bare 10 could mean morning or evening; ask instead.
    return hour, minute


def day(text, now):
    text = text.strip().lower().removeprefix("on ")
    if text in {"today", "tomorrow"}:
        return (now + timedelta(days=text == "tomorrow")).date()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return datetime.strptime(text, "%Y-%m-%d").date()
    weekday = text.removeprefix("next ")
    if weekday in WEEKDAYS:
        distance = (WEEKDAYS[weekday] - now.weekday()) % 7
        return (now + timedelta(days=distance or 7)).date()
    match = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)(?:\s+(\d{4}))?", text)
    if not match:
        reverse = re.fullmatch(r"([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?", text)
        if reverse:
            match = (None, reverse[2], reverse[1], reverse[3])
    if match and match[2] in MONTHS:
        result = datetime(int(match[3] or now.year), MONTHS[match[2]], int(match[1])).date()
        if not match[3] and result < now.date():
            result = result.replace(year=now.year+1)
        return result
    return None


def reminder(query, pending=None, now=None):
    """Return a resolved request/clarification, or None for the model to interpret."""
    now = now or datetime.now().astimezone()
    query = request_text(query)
    intro = START.match(query.strip())
    pending = pending if isinstance(pending, dict) and pending.get("kind") == "reminder" else None
    if not intro and not pending:
        return None
    if pending and not intro and re.match(r"^(?:what|who|why|where|how|can you|explain|latest|news|change|switch|turn|stay|keep|open|launch|start|pause|stop)\b", query.strip(), re.I):
        return None
    draft = dict(pending) if not intro else {"kind": "reminder"}
    text = query.strip()[intro.end():].strip() if intro else query.strip()
    if re.search(r"\b(?:and(?:\s+then)?|then)\s+(?:change|switch|set|turn|stay|keep|open|launch|start|pause|resume|cancel|stop)\b", text, re.I):
        return None
    if pending and not intro and draft.get("need") == "title":
        # Only the immediate clarification accepts a free-form title.
        if START.match(text) or len(text) > 160:
            return None
        draft["title"] = text
        text = ""
    relative = RELATIVE.search(text)
    if relative:
        seconds = sum(float(n) * UNITS[u.lower()] for n, u in re.findall(r"(\d+(?:\.\d+)?)\s*([a-z]+)", relative[1], re.I))
        if not 1 <= seconds <= 365*86400:
            return {"text": "Choose a reminder between one second and one year from now.", "draft": {}}
        draft["dueAt"] = round((now + timedelta(seconds=seconds)).timestamp()*1000)
        text = (text[:relative.start()] + " " + text[relative.end():]).strip()
    else:
        date_pattern = r"\b(?:on\s+)?(?:\d{4}-\d{2}-\d{2}|today|tomorrow|(?:next\s+)?(?:" + "|".join(WEEKDAYS) + r")|\d{1,2}(?:st|nd|rd|th)?\s+(?:" + "|".join(MONTHS) + r")(?:\s+\d{4})?|(?:" + "|".join(MONTHS) + r")\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)\b"
        date_match = re.search(date_pattern, text, re.I)
        if date_match:
            try:
                resolved = day(date_match[0], now)
            except ValueError:
                return {"text": "That date isn’t valid. Which date did you mean?", "draft": {"kind": "reminder", "need": "when"}}
            draft["date"] = resolved.isoformat()
            text = (text[:date_match.start()] + " " + text[date_match.end():]).strip()
        time_match = re.search(r"\bat\s+\d{1,2}(?::[0-5]\d)?\s*(?:am|pm)?\b", text, re.I)
        if not time_match and pending and pending.get("need") == "when":
            time_match = TIME.fullmatch(text)
        if time_match:
            value = clock(time_match[0])
            if value:
                draft["time"] = "%02d:%02d" % value
                text = (text[:time_match.start()] + " " + text[time_match.end():]).strip()
            else:
                return {"text": "Morning or evening? Use a time such as 10am or 22:00.", "draft": dict(draft, need="when")}
        if draft.get("date") and draft.get("time"):
            due = datetime.fromisoformat(draft["date"] + "T" + draft["time"]).astimezone()
            draft["dueAt"] = round(due.timestamp()*1000)
        elif draft.get("time") and not draft.get("date"):
            due = now.replace(hour=int(draft["time"][:2]), minute=int(draft["time"][3:]), second=0, microsecond=0)
            if due > now:
                draft["dueAt"] = round(due.timestamp()*1000)
    title = re.sub(r"^(?:for|to|about)\s+", "", text, flags=re.I).strip(" ,.;\"'")
    if title:
        # Unsupported scheduling/repeat words go to the model, never become a title.
        if re.search(r"\b(?:on|at|every|weekly|daily|before|from now)\b", title, re.I):
            return None
        if len(title) > 160:
            return {"text": "Use a reminder title of up to 160 characters.", "draft": dict(draft, need="title")}
        draft["title"] = title
    if not draft.get("title"):
        return {"text": "What should I remind you about?", "draft": dict(draft, need="title")}
    if not draft.get("dueAt"):
        return {"text": "When should I remind you? Include a time, such as tomorrow at 10am.", "draft": dict(draft, need="when")}
    if draft["dueAt"] <= now.timestamp()*1000:
        draft.pop("dueAt", None)
        return {"text": "That time has passed. When should I remind you instead?", "draft": dict(draft, need="when")}
    due = datetime.fromtimestamp(draft["dueAt"]/1000).astimezone()
    return {"title": draft["title"], "date": due.date().isoformat(), "time": due.strftime("%H:%M"), "dueAt": draft["dueAt"], "lead": 0, "count": 1}


def command(query, applications=()):
    """Exact, explicit desktop commands only. Questions/compound requests use AI."""
    value = request_text(query)
    mode = re.fullmatch(r"(?:change|switch|set|turn)\s+(?:(?:it|appearance|theme)\s+)?(?:to\s+)?(dark|light)(?:\s+(?:mode|theme))?", value, re.I)
    if mode:
        return {"name": "appearance", "args": {"mode": mode[1].lower()}}
    awake = re.fullmatch(r"(?:stay\s+awake|keep\s+(?:(?:the|my)\s+)?(?:screen|computer|pc|display)\s+awake|keep\s+awake|(?:turn|switch)\s+on\s+(?:keep\s+)?awake)(?:\s+for\s+(.+))?", value, re.I)
    if awake:
        seconds = 0
        if awake[1]:
            duration = RELATIVE.fullmatch("for " + awake[1])
            if not duration:
                return None
            seconds = sum(float(n)*UNITS[u.lower()] for n,u in re.findall(r"(\d+(?:\.\d+)?)\s*([a-z]+)", duration[1], re.I))
            if not 1 <= seconds <= 86400:
                return None
        return {"name": "awake", "args": {"enabled": True, "seconds": round(seconds)}}
    toggle = re.fullmatch(r"(?:turn|switch)\s+(on|off)\s+(keep\s+awake|awake|peace|do\s+not\s+disturb|night\s*light)", value, re.I)
    if toggle:
        name = "awake" if "awake" in toggle[2].lower() else "nightlight" if "night" in toggle[2].lower() else "peace"
        return {"name": name, "args": {"enabled": toggle[1].lower() == "on"}}
    level = re.fullmatch(r"(?:set|change|adjust)\s+(?:(?:the|my)\s+)?(volume|brightness)\s+(?:to\s+)?(\d{1,3})(?:\s*(?:%|percent))?", value, re.I)
    if level and int(level[2]) <= 100:
        return {"name": level[1].lower(), "args": {"level": int(level[2])}}
    focus = re.fullmatch(r"(?:start|set)\s+(?:a\s+)?(?:focus(?:\s+timer)?|timer)\s+(?:for\s+)?(\d+)\s*(?:minutes?|mins?|m)", value, re.I)
    if focus and 1 <= int(focus[1]) <= 120:
        return {"name": "focus", "args": {"minutes": int(focus[1])}}
    media = {"pause music": "media_pause", "pause media": "media_pause", "play music": "media_play", "resume music": "media_play", "next track": "media_next", "skip song": "media_next", "previous track": "media_previous", "pause focus": "focus_pause", "resume focus": "focus_pause", "cancel focus": "focus_cancel", "stop focus": "focus_cancel"}
    if value.lower() in media:
        args = {"paused": value.lower() == "pause focus"} if media[value.lower()] == "focus_pause" else {}
        return {"name": media[value.lower()], "args": args}
    opening = re.fullmatch(r"(?:open|launch)\s+(.+)", value, re.I)
    if opening:
        name = opening[1].lower()
        panels = {"settings": "settings", "control center": "quicksettings", "calendar": "calendar", "themes": "themes", "wallpapers": "wallpapers", "wifi": "wifi", "wi-fi": "wifi", "bluetooth": "bluetooth", "display": "display", "sound": "sound", "notifications": "notifhistory", "performance": "performance"}
        if name in panels:
            return {"name": "open_panel", "args": {"panel": panels[name]}}
        apps = [a for a in applications if isinstance(a, dict) and isinstance(a.get("name"), str) and (a["name"].lower() == name or len(name)>=3 and a["name"].lower().startswith(name+" "))]
        if len(apps) == 1 and isinstance(apps[0].get("id"), str):
            return {"name": "open_app", "args": {"id": apps[0]["id"]}}
    return None


def commands(query, applications=()):
    single = command(query, applications)
    if single:
        return [single]
    parts = re.split(r"\s+(?:and(?:\s+then)?|then)\s+(?=(?:change|switch|set|turn|stay|keep|open|launch|start|pause|resume|cancel|stop)\b)", query.strip(), flags=re.I)
    if 2 <= len(parts) <= 4:
        actions = [command(part, applications) for part in parts]
        if all(actions):
            return actions
    return None


def followup(query, recent, desktop, now=None):
    """Resolve explicit edits against recent tasks, never a guessed global target."""
    now = now or datetime.now().astimezone()
    value = request_text(query)
    change = re.fullmatch(r"(?:make|change|set)\s+(?:that|it|the\s+(?:reminder|timer|focus|awake\s+time|volume|brightness))\s+(?:to\s+)?(.+)", value, re.I)
    cancel = re.fullmatch(r"(?:cancel|stop)\s+(?:it|that|the\s+(?:reminder|timer|focus|awake\s+time))", value, re.I)
    if not (change or cancel) or not isinstance(recent, list):
        return None
    recent = [t for t in recent[-8:] if isinstance(t, dict) and isinstance(t.get("at"), (int, float))
              and 0 <= now.timestamp()*1000-t["at"] <= 15*60*1000 and t.get("status") in {"done", "scheduled", "requested"}]
    if not recent:
        return {"text": "Which task do you want to change?"}
    named = re.search(r"\bthe\s+(reminder|timer|focus|awake\s+time|volume|brightness)\b", value, re.I)
    if named:
        kind = {"timer": "focus", "awake time": "awake", "reminder": "reminder"}.get(named[1].lower(), named[1].lower())
        recent = [t for t in recent if t.get("name") in ({"reminder", "reminder_update"} if kind == "reminder" else {kind})]
    if not recent:
        return {"text": "I don’t have a recent matching task in this conversation. Which one did you mean?"}
    latest = recent[-1]
    batch = [t for t in recent if t.get("batch") == latest.get("batch")]
    if len(batch) != 1:
        return {"text": "Which task did you mean? Name the reminder, focus timer, awake time, volume or brightness."}
    name, args = latest.get("name"), latest.get("args", {})
    replacement = re.sub(r"\s+instead$", "", change[1], flags=re.I) if change else ""
    action = None
    if name in {"reminder", "reminder_update"}:
        identifier = latest.get("reminderId")
        reminder = next((r for r in desktop.get("reminders", []) if r.get("id") == identifier), None)
        if not reminder:
            return {"text": "That reminder is no longer active. Set a new one or choose another reminder."}
        if cancel:
            action = {"name": "reminder_remove", "args": {"id": identifier}}
        else:
            parsed = RELATIVE.fullmatch("for " + replacement)
            if not parsed:
                return None  # Dates and complex edits go to the model with the same task context.
            seconds = sum(float(n)*UNITS[u.lower()] for n, u in re.findall(r"(\d+(?:\.\d+)?)\s*([a-z]+)", parsed[1], re.I))
            if not 1 <= seconds <= 365*86400:
                return {"text": "Choose a reminder between one second and one year from now."}
            action = {"name": "reminder_update", "args": {"id": identifier, "title": reminder["title"], "dueAt": round((now+timedelta(seconds=seconds)).timestamp()*1000)}}
    elif name == "awake":
        if not desktop.get("awake") or desktop.get("awakeUntil") != latest.get("expectedUntil"):
            return {"text": "That awake session has ended or changed. Tell me how long to keep the screen awake."}
        action = {"name": "awake", "args": {"enabled": False}}
        if change:
            parsed = command("stay awake for " + replacement)
            if not parsed:
                return None
            action = parsed
    elif name == "focus":
        focus = desktop.get("focus", {})
        if focus.get("phase") not in {"running", "paused"} or focus.get("duration") != args.get("minutes", 0)*60:
            return {"text": "That focus timer has ended or changed. Which timer did you mean?"}
        if cancel:
            action = {"name": "focus_cancel", "args": {}}
        else:
            action = command("start focus for " + replacement)
            if not action:
                return None
            # Restarting a running timer is a proposal, not an invisible edit.
            return {"actions": [action], "review": True, "text": "Restart this focus timer with the new duration?"}
    elif name in {"volume", "brightness"} and change:
        action = command("set " + name + " to " + replacement)
    if action:
        return {"actions": [action]}
    return None
