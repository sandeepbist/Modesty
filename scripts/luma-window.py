#!/usr/bin/env python3
"""Read the active application's own surface, never the entire desktop."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import tempfile
import time


TEXT_TIMEOUT = 3
MAX_NODES = 1800
MAX_TEXT = 80000
MAX_OUTPUT = 600000
LIMITS = ["Only application-exposed document text is available; virtualized or lazy-loaded content may be missing.",
          "The image covers the visible window only; offscreen imagery is unavailable."]


def native_private(generation):
    status = json.loads(subprocess.check_output(["hyprctl", "luma-private", "status"], timeout=2))
    if (status.get("protocol") != 1 or status.get("generation") != generation or
            status.get("destination") not in {"luma", "native", "waiting-luma", "waiting-native"}):
        raise ValueError("Analyze Page requires the current unlocked private Luma session")


def validate_target(window):
    keys = ("address", "pid", "class", "title")
    if (not isinstance(window, dict) or not isinstance(window.get("address"), str) or not window["address"] or
            type(window.get("pid")) is not int or window["pid"] <= 0 or
            any(not isinstance(window.get(key), str) or not window[key] for key in ("class", "title")) or
            window["class"].lower() in {"quickshell", "modesty"}):
        raise ValueError("Analyze Page requires an exact application target")
    clients = json.loads(subprocess.check_output(["hyprctl", "clients", "-j"], timeout=2))
    matches = [client for client in clients if client.get("class") == window["class"] and client.get("title") == window["title"]]
    if len(matches) != 1:
        raise ValueError("Analyze Page target is ambiguous or unavailable")
    active = json.loads(subprocess.check_output(["hyprctl", "activewindow", "-j"], timeout=2))
    keys += tuple(key for key in ("stableId", "initialClass", "initialTitle") if key in window)
    if any(source.get(key) != window.get(key) for source in (active, matches[0]) for key in keys):
        raise ValueError("Analyze Page target changed")


def document_text(selected, desktop, Atspi):
    visited = 0
    truncated = False
    def children(node):
        nonlocal visited, truncated
        count = node.get_child_count()
        if type(count) is not int or count < 0:
            raise ValueError("Malformed document tree")
        result = []
        for index in range(min(count, MAX_NODES-visited)):
            visited += 1
            child = node.get_child_at_index(index)
            if child is None:
                raise ValueError("Malformed document tree")
            result.append(child)
        if len(result) < count:
            truncated = True
        return result
    def exposed(node, require_visible=True):
        state = node.get_state_set()
        attrs = node.get_attributes() or {}
        return ((not require_visible or state.contains(Atspi.StateType.VISIBLE)) and not state.contains(Atspi.StateType.DEFUNCT) and
                node.get_role() != Atspi.Role.PASSWORD_TEXT and not any(
                    str(attrs.get(key, "")).lower() in {"true", "1", "password"}
                    for key in ("hidden", "aria-hidden", "invisible", "protected", "password")))
    apps = [node for node in children(desktop) if node.get_process_id() == selected["pid"] and exposed(node, False)]
    frames = [node for app in apps for node in children(app)
              if node.get_role() in (Atspi.Role.FRAME, Atspi.Role.WINDOW) and exposed(node)
              and node.get_name() == selected["title"]]
    if len(frames) != 1:
        raise ValueError("No unique accessible application window")
    roles = {getattr(Atspi.Role, name) for name in ("DOCUMENT_WEB", "DOCUMENT_FRAME", "DOCUMENT_TEXT",
             "DOCUMENT_PRESENTATION", "DOCUMENT_SPREADSHEET", "DOCUMENT_EMAIL") if hasattr(Atspi.Role, name)}
    documents = []
    stack = children(frames[0])
    while stack:
        node = stack.pop()
        if not exposed(node):
            continue
        if node.get_role() in roles:
            if node.get_state_set().contains(Atspi.StateType.SHOWING):
                documents.append(node)
            continue
        stack.extend(children(node))
    if len(documents) != 1 or truncated:
        raise ValueError("No unique active accessible document")
    def collect(node, depth=0):
        nonlocal truncated
        if depth > 64:
            raise ValueError("Document nesting limit")
        if not exposed(node):
            return "", False
        descendants = children(node)
        safe = len(descendants) == node.get_child_count()
        pieces, records = [], []
        for child in descendants:
            text, child_safe = collect(child, depth+1)
            records.append((child, text))
            safe = safe and child_safe
            if text:
                pieces.append(text)
        value = ""
        if safe and "Text" in node.get_interfaces():
            count = Atspi.Text.get_character_count(node)
            if type(count) is not int or count < 0:
                raise ValueError("Malformed document text")
            take = min(count, MAX_TEXT)
            value = Atspi.Text.get_text(node, 0, take)
            if not isinstance(value, str) or len(value) > take:
                raise ValueError("Malformed document text")
            if take < count:
                truncated = True
        if "\ufffc" in value:
            replacements = []
            if "Hypertext" in node.get_interfaces():
                for offset, character in enumerate(value):
                    if character != "\ufffc":
                        continue
                    index = Atspi.Hypertext.get_link_index(node, offset)
                    link = Atspi.Hypertext.get_link(node, index) if index >= 0 else None
                    if link is None or Atspi.Hyperlink.get_n_anchors(link) != 1:
                        raise ValueError("Ambiguous embedded document content")
                    anchor = Atspi.Hyperlink.get_object(link, 0)
                    matches = [text for child, text in records if child == anchor]
                    if len(matches) != 1:
                        raise ValueError("Embedded content is outside the document children")
                    replacements.append(matches[0])
            else:
                raise ValueError("No embedded document association")
            chunks = value.split("\ufffc")
            value = chunks[0]+"".join(text+suffix for text, suffix in zip(replacements, chunks[1:]))
        value = "\n".join(([value] if value else [])+[text for text in pieces if text not in value])
        value = value.replace("\x00", "")
        if len(value) > MAX_TEXT:
            truncated = True
        return value[:MAX_TEXT], safe
    text, _ = collect(documents[0])
    if not text.strip():
        raise ValueError("No exposed document text")
    return {"text": text, "characters": len(text), "nodes": visited, "truncated": truncated}


def read_document(window):
    try:
        result = subprocess.run([sys.executable, str(Path(__file__)), "--document-worker"],
                                input=json.dumps(window)+"\n", text=True, capture_output=True, timeout=TEXT_TIMEOUT, check=True)
        if len(result.stdout.encode()) > MAX_OUTPUT:
            raise ValueError("Document output limit")
        value = json.loads(result.stdout)
        if (not isinstance(value, dict) or not isinstance(value.get("text"), str) or
                not 0 < len(value["text"]) <= MAX_TEXT or type(value.get("truncated")) is not bool or
                value.get("characters") != len(value["text"]) or type(value.get("nodes")) is not int or
                not 0 <= value["nodes"] <= MAX_NODES):
            raise ValueError("Malformed document result")
        return value, ""
    except subprocess.TimeoutExpired:
        return None, "Document accessibility timed out."
    except (OSError, ValueError, subprocess.SubprocessError):
        return None, "Document accessibility is unavailable, unsupported or ambiguous."


def capture(window=None, page=False, generation=None, capture_directory=None):
    if window is None:
        window = json.loads(subprocess.check_output(["hyprctl", "activewindow", "-j"], timeout=2))
    if not window.get("address") or window.get("class", "").lower() in {"quickshell", "modesty"}:
        raise ValueError("No application window is available")
    if page:
        native_private(generation)
        validate_target(window)
    source = Path(__file__).with_name("window-toplevel.c")
    protocol = Path("/usr/share/wayland-protocols/staging/ext-foreign-toplevel-list/ext-foreign-toplevel-list-v1.xml")
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home()/".cache"))/"modesty"/"window-context"
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    binary = cache/("toplevel-"+hashlib.sha256(source.read_bytes()).hexdigest()[:16])
    if not binary.exists():
        with tempfile.TemporaryDirectory(dir=cache) as folder:
            folder = Path(folder)
            subprocess.run(["wayland-scanner", "client-header", str(protocol), str(folder/"toplevel-protocol.h")], check=True, capture_output=True, timeout=5)
            subprocess.run(["wayland-scanner", "private-code", str(protocol), str(folder/"protocol.c")], check=True, capture_output=True, timeout=5)
            subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-I"+str(folder), str(source), str(folder/"protocol.c"), "-lwayland-client", "-o", str(folder/"capture")], check=True, capture_output=True, timeout=10)
            (folder/"capture").replace(binary)
    env = dict(os.environ, LUMA_WINDOW_APP=window["class"], LUMA_WINDOW_TITLE=window.get("title", ""))
    identifier = subprocess.check_output([str(binary)], env=env, timeout=3, text=True).strip()
    if not identifier:
        raise ValueError("This compositor cannot capture the application directly")
    with tempfile.NamedTemporaryFile(dir=capture_directory or cache, suffix=".png", delete=False) as stream:
        path = Path(stream.name)
    def cancelled(signum, frame):
        path.unlink(missing_ok=True)
        raise SystemExit(1)
    if page:
        signal.signal(signal.SIGTERM, cancelled)
    try:
        if page:
            native_private(generation)
            validate_target(window)
        subprocess.run(["grim", "-T", identifier, "-l", "1", str(path)], check=True, capture_output=True, timeout=5)
        path.chmod(0o600)
        with path.open("rb") as stream:
            if stream.read(8) != b"\x89PNG\r\n\x1a\n" or not 8 < path.stat().st_size <= 12_000_000:
                raise ValueError("Invalid application image")
        result = {"path": str(path), "app": window["class"], "title": window.get("title", "")[:240], "capturedAt": time.time()}
        if page:
            validate_target(window)
            native_private(generation)
            document, reason = read_document(window)
            native_private(generation)
            validate_target(window)
            final_identifier = subprocess.check_output([str(binary)], env=env, timeout=3, text=True).strip()
            if identifier != final_identifier:
                raise ValueError("Analyze Page source changed")
            result.update(scope="document_text" if document else "visible_window", limits=LIMITS,
                          fallbackReason=reason, truncated=False)
            if document:
                result.update(document)
            result["target"] = {key: window[key] for key in ("address", "pid", "class", "title", "stableId") if key in window}
        # Keep only recent request captures, not a screenshot history.
        for old in cache.glob("*.png"):
            if old != path and time.time()-old.stat().st_mtime > 120:
                old.unlink(missing_ok=True)
        return result
    except Exception:
        path.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    try:
        selected = json.loads(sys.stdin.readline(16000)) if "--selected" in sys.argv or "--document-worker" in sys.argv else None
        if "--document-worker" in sys.argv:
            import gi
            gi.require_version("Atspi", "2.0")
            from gi.repository import Atspi
            Atspi.set_timeout(350, 350)
            print(json.dumps(document_text(selected, Atspi.get_desktop(0), Atspi)))
        else:
            page = "--page" in sys.argv
            generation = selected.pop("_privateGeneration", None) if page else None
            directory = selected.pop("_captureDirectory", None) if page else None
            print(json.dumps(capture(selected, page, generation, directory)))
    except Exception:
        print(json.dumps({"error": "Could not read the current application window."}))
