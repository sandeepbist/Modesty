"""Normalize conversation state and streamed provider responses."""
import json
import math
import re
import time
import uuid
from .actions import ACTIONS

def clean_citations(value):
    return [{k: v[:2000] if isinstance(v, str) else v for k, v in c.items()
             if k in {"url", "title", "snippet", "published", "publisher", "host", "document", "headlineOnly"} and isinstance(v, (str, bool))}
            for c in (value if isinstance(value, list) else [])[:12]
            if isinstance(c, dict) and isinstance(c.get("url"), str) and c["url"].startswith(("https://", "http://", "file://"))]



def clean_execution(value):
    receipts=[]
    for entry in (value if isinstance(value,list) else [])[-24:]:
        if not isinstance(entry,dict): continue
        tool=entry.get("tool",{}); result=entry.get("result",{})
        if not isinstance(tool,dict) or not isinstance(result,dict): continue
        receipts.append({"at":entry.get("at",0),
            "tool":{k:v[:2000] if isinstance(v,str) else v[:96] for k,v in tool.items() if k in {"name","purpose","path","argv","uri","action_name","action_args","id","operation"} and isinstance(v,(str,list))},
            "result":{k:v[:2000] if isinstance(v,str) else v for k,v in result.items() if k in {"ok","status","error","path","exitCode","stdout","stderr","note"} and (isinstance(v,(str,bool)) or v is None or type(v) in (int,float))}})
    return receipts



def clean_messages(messages):
    if not isinstance(messages, list):
        return []
    return [{"role": m["role"], "text": m["text"][:12000], "id": str(m.get("id", ""))[:80], "hidden": m.get("hidden") is True,
             "presentation": presentation(m.get("presentation")) if m["role"] == "assistant" else {},
             "citations": clean_citations(m.get("citations")) if m["role"] == "assistant" else [],
             "execution": clean_execution(m.get("execution")) if m["role"] == "assistant" else [],
             "failed": m.get("failed") is True} for m in messages[-16:]
            if isinstance(m, dict) and m.get("role") in {"user", "assistant"} and isinstance(m.get("text"), str)][:16]



def request_scope(query, history, max_turns=4, max_text=1000, **context):
    """Earlier turns resolve references; they are not a queue of unfinished goals."""
    return dict(context, conversation_context={
        "scope": "Earlier turns are reference material only, including unanswered or failed requests. Do not retry or combine them with latest_request unless latest_request explicitly asks to continue them.",
        "turns": [{"role": m["role"], "text": m["text"][:max_text], "failed": m.get("failed", False)} for m in history[-max_turns:]]},
        latest_request=query[:6000])



def clean_task_context(value):
    if not isinstance(value, dict):
        return {"recentTasks": [], "pendingTask": None, "taskExpires": 0}
    recent = []
    for task in (value.get("recentTasks", []) if isinstance(value.get("recentTasks"), list) else [])[-8:]:
        if not isinstance(task, dict) or task.get("name") not in ACTIONS or not isinstance(task.get("args"), dict):
            continue
        clean = {k: v[:240] if isinstance(v, str) else v for k, v in task.items()
                 if k in {"key", "name", "status", "batch", "reminderId", "expectedUntil", "at"}
                 and (isinstance(v, str) or type(v) in (int, float) and math.isfinite(v))}
        clean["args"] = {k: v[:240] if isinstance(v, str) else v for k, v in task["args"].items()
                         if k in {"title", "date", "time", "id", "dueAt", "lead", "count", "mode", "enabled", "seconds", "minutes", "level", "paused", "panel", "operation", "width", "format"}
                         and (isinstance(v, str) or type(v) is bool or type(v) in (int, float) and math.isfinite(v))}
        if task["name"]=="file_action" and isinstance(task["args"].get("paths"),list):
            clean["args"]["paths"]=[p[:1024] for p in task["args"]["paths"][:3] if isinstance(p,str)]
        recent.append(clean)
    pending = value.get("pendingTask")
    pending = {k: v[:160] if isinstance(v, str) else v for k, v in pending.items()
               if k in {"kind", "need", "title", "date", "time", "dueAt"} and (isinstance(v, str) or type(v) in (int, float) and math.isfinite(v))} if isinstance(pending, dict) and pending.get("kind") == "reminder" else None
    expires = value.get("taskExpires", 0)
    expires = expires if type(expires) in (int, float) and math.isfinite(expires) and time.time()*1000 < expires <= time.time()*1000+120000 else 0
    run=value.get("systemRun","")
    return {"recentTasks": recent, "pendingTask": pending if expires else None, "taskExpires": expires,
        "systemRun":run if isinstance(run,str) and re.fullmatch(r"[a-f0-9]{32}",run) else ""}



def conversation_state(value):
    """Migrate the single transcript without discarding it."""
    if isinstance(value, list):
        messages = clean_messages(value)
        identifier = uuid.uuid4().hex
        value = {"active": identifier, "threads": [{"id": identifier, "messages": messages}] if messages else []}
    if not isinstance(value, dict):
        value = {}
    threads = []
    for thread in (value.get("threads", []) if isinstance(value.get("threads"), list) else [])[-32:]:
        if not isinstance(thread, dict) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", str(thread.get("id", ""))):
            continue
        messages = clean_messages(thread.get("messages", []))
        first = next((m["text"] for m in messages if m["role"] == "user"), "New conversation")
        citations = clean_citations(thread.get("citations"))
        threads.append({"id": thread["id"], "title": first[:72], "messages": messages, "citations": citations, "taskContext": clean_task_context(thread.get("taskContext")),
                        "updatedAt": thread.get("updatedAt", 0) if isinstance(thread.get("updatedAt", 0), (int, float)) else 0})
    threads = list({t["id"]: t for t in threads}.values())
    active = value.get("active", "")
    if active not in {t["id"] for t in threads}:
        active = threads[-1]["id"] if threads else uuid.uuid4().hex
    current = next((t for t in threads if t["id"] == active), {})
    return {"version": 3, "active": active, "threads": threads, "messages": current.get("messages", []), "citations": current.get("citations", []), "taskContext": current.get("taskContext", {})}



def stream_answer(raw):
    """Expose only a JSON string prefix; incomplete actions never leave here."""
    match = re.search(r'"answer"\s*:\s*"', raw)
    if not match:
        return None, ""
    try:
        header = json.loads(raw[:match.start()].rstrip().rstrip(",") + "}")
    except ValueError:
        return None, ""
    start, end, escaped = match.end() - 1, match.end(), False
    while end < len(raw):
        char = raw[end]
        if char == '"' and not escaped:
            return header, json.loads(raw[start:end + 1])
        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
        end += 1
    tail = raw[start:]
    # A chunk can end inside a backslash or Unicode escape. Retain it for the next chunk.
    for trim in range(min(6, len(tail))):
        try:
            value = json.loads((tail[:-trim] if trim else tail) + '"')
            return header, value[:-1] if value and 0xD800 <= ord(value[-1]) <= 0xDBFF else value
        except ValueError:
            pass
    return header, ""



def presentation(value):
    """Bounded display data only; it can never contain executable actions."""
    if not isinstance(value, dict) or value.get("layout") not in {"prose", "explanation", "comparison", "decision"}:
        return {}
    # Fall back to the complete plain answer rather than clipping substantive prose.
    if any(isinstance(value.get(k), str) and len(value[k]) > 1800 for k in ("lead", "recommendation")):
        return {}
    def text(value, limit):
        return value.strip()[:limit] if isinstance(value, str) else ""
    def entries(key):
        return value[key] if isinstance(value.get(key), list) else []
    # A partially valid document must not hide parts of the plain answer.
    if any(not isinstance(s, dict) or not isinstance(s.get("title"), str) or not s["title"].strip() or not isinstance(s.get("body"), str) or not s["body"].strip() for s in entries("sections")):
        return {}
    if len(entries("columns")) > 3 or any(not isinstance(c, str) or not c.strip() for c in entries("columns")):
        return {}
    if entries("rows") and (len(entries("columns")) < 2 or any(not isinstance(r, dict) or not isinstance(r.get("label"), str) or not r["label"].strip() or not isinstance(r.get("values"), list) or len(r["values"]) != len(entries("columns")) or not all(isinstance(c, str) for c in r["values"]) for r in entries("rows"))):
        return {}
    if len(entries("sections")) > 6 or len(entries("rows")) > 8 or any(isinstance(s, dict) and isinstance(s.get("body"), str) and len(s["body"]) > 3000 for s in entries("sections")):
        return {}
    if any(isinstance(r, dict) and isinstance(r.get("values"), list) and any(isinstance(c, str) and len(c) > 500 for c in r["values"]) for r in entries("rows")):
        return {}
    columns = [text(c, 80) for c in entries("columns")[:3] if isinstance(c, str) and c.strip()]
    sections = [{"title": text(s.get("title"), 100), "body": text(s.get("body"), 3000)} for s in entries("sections")[:6]
                if isinstance(s, dict) and isinstance(s.get("body"), str) and s["body"].strip()]
    rows = [{"label": text(r.get("label"), 100), "values": [text(c, 500) for c in r["values"]]} for r in entries("rows")[:8]
            if isinstance(r, dict) and isinstance(r.get("values"), list) and len(r["values"]) == len(columns) and all(isinstance(c, str) for c in r["values"])] if len(columns) >= 2 else []
    followups = [{"label": text(f.get("label"), 40), "query": text(f.get("query"), 1000)} for f in entries("followups")[:3]
                 if isinstance(f, dict) and text(f.get("label"), 40) and text(f.get("query"), 1000)]
    layout = "prose" if value["layout"] == "comparison" and not rows else value["layout"]
    return {"layout": layout, "lead": text(value.get("lead"), 1800), "sections": sections,
            "columns": columns if rows else [], "rows": rows, "recommendation": text(value.get("recommendation"), 1800), "followups": followups}
