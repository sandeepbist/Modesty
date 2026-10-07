#!/usr/bin/env python3
"""Read the active application's own surface, never the entire desktop."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def capture(window=None):
    if window is None:
        window = json.loads(subprocess.check_output(["hyprctl", "activewindow", "-j"], timeout=2))
    if not window.get("address") or window.get("class", "").lower() in {"quickshell", "modesty"}:
        raise ValueError("No application window is available")
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
    with tempfile.NamedTemporaryFile(dir=cache, suffix=".png", delete=False) as stream:
        path = Path(stream.name)
    try:
        subprocess.run(["grim", "-T", identifier, "-l", "1", str(path)], check=True, capture_output=True, timeout=5)
        path.chmod(0o600)
        # Keep only recent request captures, not a screenshot history.
        for old in cache.glob("*.png"):
            if old != path and time.time()-old.stat().st_mtime > 120:
                old.unlink(missing_ok=True)
        return {"path": str(path), "app": window["class"], "title": window.get("title", "")[:240], "capturedAt": time.time()}
    except Exception:
        path.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    try:
        selected = json.loads(sys.stdin.readline(16000)) if "--selected" in sys.argv else None
        print(json.dumps(capture(selected)))
    except (OSError, ValueError, subprocess.SubprocessError):
        print(json.dumps({"error": "Could not read the current application window."}))
