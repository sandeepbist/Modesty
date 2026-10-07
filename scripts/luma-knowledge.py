#!/usr/bin/env python3
"""Opt-in local passage index. SQLite FTS, no network or embedding provider."""
import fcntl
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
import tempfile

HOME = Path.home().resolve()
STATE = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local/state")) / "modesty"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "modesty"
INDEX = CACHE / "luma-knowledge.sqlite3"
TEXT = {".txt", ".md", ".rst", ".csv", ".log", ".py", ".qml", ".js", ".ts", ".go", ".rs", ".lua", ".toml", ".yaml", ".yml", ".html", ".css"}
SKIP = {"node_modules", "venv", "target", "build", "dist", "Trash"}


def roots(values=None):
    if values is None:
        try:
            values = json.loads((STATE / "preferences.json").read_text()).get("lumaKnowledgeRoots", [])
        except (OSError, ValueError):
            values = []
    if not isinstance(values, list):
        raise ValueError("Choose folders to index.")
    result = []
    for value in values[:12]:
        if not isinstance(value, str):
            continue
        path = Path(value).expanduser().resolve()
        # Whole-home and hidden folders are deliberately not implicit grants.
        if HOME in path.parents and path.is_dir() and not any(p.startswith(".") for p in path.relative_to(HOME).parts):
            if not any(parent == path or parent in path.parents for parent in result):
                result = [p for p in result if path not in p.parents] + [path]
    return result


def permitted(path, selected):
    path = Path(path)
    try:
        resolved = path.resolve(strict=True)
        return (not path.is_symlink() and resolved == path and resolved.is_file()
                and any(root in resolved.parents for root in selected)
                and not any(p.startswith(".") or p in SKIP for p in resolved.relative_to(HOME).parts)
                and not re.search(r"(?:secrets?|credentials?|passwords?|private[-_]key|tokens?)[-_.]", resolved.name, re.I)
                and resolved.suffix.lower() in TEXT | {".pdf"}
                and resolved.stat().st_size <= 8_000_000)
    except (OSError, ValueError):
        return False


def connect():
    CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(INDEX, timeout=2)
    INDEX.chmod(0o600)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS documents(path TEXT PRIMARY KEY, modified INTEGER, size INTEGER, pages INTEGER, truncated INTEGER)")
    db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(path UNINDEXED, page UNINDEXED, part UNINDEXED, title, body, tokenize='unicode61')")
    db.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)")
    return db


def pages(path):
    if path.suffix.lower() == ".pdf":
        # Embedded text only: background indexing never spends seconds per page on OCR.
        with tempfile.TemporaryDirectory(prefix="luma-index-") as temporary:
            output=Path(temporary)/"text"
            subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", "200", str(path), str(output)],
                           capture_output=True, timeout=12, check=True)
            with output.open(encoding="utf-8", errors="replace") as stream:
                raw=stream.read(200001)
        truncated=len(raw)>200000
        chunks=raw[:200000].split("\f")
        if chunks and not chunks[-1].strip():
            chunks.pop()
        return [(i+1,text) for i,text in enumerate(chunks[:200])], truncated or len(chunks)>=200
    with path.open(encoding="utf-8", errors="replace") as stream:
        text = stream.read(200001)
    return [(0, text[:200000])], len(text) > 200000


def build(values):
    selected = roots(values)
    CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (CACHE / "luma-knowledge.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with connect() as db:
            old = {p: (m, s) for p, m, s in db.execute("SELECT path, modified, size FROM documents")}
            for path in list(old):
                if not permitted(path,selected):
                    db.execute("DELETE FROM passages WHERE path=?",(path,))
                    db.execute("DELETE FROM documents WHERE path=?",(path,))
                    del old[path]
            db.commit()
            old_counts=dict(db.execute("SELECT path,count(*) FROM passages GROUP BY path"))
            total_passages=sum(old_counts.values())
            seen, count, skipped, limited = set(), 0, 0, False
            for root in selected:
                for folder, dirs, names in os.walk(root, followlinks=False):
                    dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP and not (Path(folder)/d).is_symlink())
                    for name in sorted(names):
                        path = Path(folder)/name
                        if not permitted(path, selected):
                            continue
                        if count >= 15000:
                            limited = True
                            break
                        count += 1
                        seen.add(str(path))
                        try:
                            stat = path.stat()
                        except OSError:
                            skipped += 1
                            continue
                        stamp = stat.st_mtime_ns, stat.st_size
                        if old.get(str(path)) == stamp:
                            continue
                        try:
                            extracted, truncated = pages(path)
                            if (path.stat().st_mtime_ns, path.stat().st_size) != stamp:
                                skipped += 1
                                continue
                            db.execute("DELETE FROM passages WHERE path=?", (str(path),))
                            remaining, rows = 200000, []
                            for number, text in extracted:
                                text = text[:remaining]
                                remaining -= len(text)
                                # Bounded overlapping passages preserve nearby context and actual PDF pages.
                                for start in range(0, len(text), 1100):
                                    body = text[start:start+1400].strip()
                                    if body:
                                        rows.append((str(path), number, start//1100, path.stem, body))
                                if not remaining:
                                    truncated = True
                                    break
                            if total_passages-old_counts.get(str(path),0)+len(rows)>60000:
                                limited=True
                                db.rollback()
                                break
                            total_passages+=len(rows)-old_counts.get(str(path),0)
                            db.executemany("INSERT INTO passages(path,page,part,title,body) VALUES(?,?,?,?,?)", rows)
                            db.execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?)", (str(path), *stamp, len(extracted), int(truncated)))
                            db.commit()
                        except (OSError, ValueError, subprocess.SubprocessError):
                            skipped += 1
                            db.execute("DELETE FROM passages WHERE path=?", (str(path),))
                            db.execute("DELETE FROM documents WHERE path=?", (str(path),))
                    if limited:
                        break
                if limited:
                    break
            # Removed permissions take effect even if a scan reaches its file ceiling.
            for path in old:
                if not permitted(path, selected) or not limited and path not in seen:
                    db.execute("DELETE FROM passages WHERE path=?", (path,))
                    db.execute("DELETE FROM documents WHERE path=?", (path,))
            db.execute("INSERT OR REPLACE INTO meta VALUES('updated',?)", (str(time.time()),))
            db.commit()
            return dict(ok=True, **status(db), skipped=skipped, limited=limited)


def status(db=None):
    if db is None:
        if not INDEX.exists():
            return dict(documents=0, passages=0, updated=0)
        with sqlite3.connect(INDEX.as_uri()+"?mode=ro", uri=True, timeout=1) as connection:
            return status(connection)
    updated = db.execute("SELECT value FROM meta WHERE key='updated'").fetchone()
    return dict(documents=db.execute("SELECT count(*) FROM documents").fetchone()[0],
                passages=db.execute("SELECT count(*) FROM passages").fetchone()[0], updated=float(updated[0]) if updated else 0)


def search(query, limit=12):
    selected = roots()
    terms = list(dict.fromkeys(re.findall(r"\w+", query.casefold())))[:16]
    if not selected or not terms or not INDEX.exists():
        return []
    ignored = {"find", "show", "search", "my", "the", "a", "an", "me", "in", "on", "about", "that", "which", "document", "documents", "pdf", "file", "files", "mention", "mentions", "discusses", "explains", "contains", "where", "is", "are", "of", "for", "to", "and"}
    useful = [t for t in terms if t not in ignored] or terms
    expression = " OR ".join('"'+t+'"*' for t in useful)
    try:
        with sqlite3.connect(INDEX.as_uri()+"?mode=ro", uri=True, timeout=1) as db:
            rows = db.execute("SELECT p.path,p.page,p.part,p.body,d.modified,d.size,d.truncated,bm25(passages,0,0,0,2,1),snippet(passages,4,'','',' … ',48) FROM passages p JOIN documents d ON p.path=d.path WHERE passages MATCH ? ORDER BY bm25(passages,0,0,0,2,1) LIMIT 80", (expression,)).fetchall()
    except sqlite3.Error:
        return []
    result, counts = [], {}
    for path, page, part, body, modified, size, truncated, score,match in rows:
        file = Path(path)
        if not permitted(file, selected):
            continue
        try:
            stat = file.stat()
        except OSError:
            continue
        if (stat.st_mtime_ns, stat.st_size) != (modified, size) or counts.get(path, 0) >= 2:
            continue
        counts[path] = counts.get(path, 0)+1
        result.append(dict(path=path, title=file.name, subtitle=("Page "+str(page)+" · " if page else "")+str(file.parent).replace(str(HOME), "~", 1),
                           page=int(page), part=int(part), excerpt=body, match=match, kind="knowledge", truncated=bool(truncated),
                           url=file.as_uri()+("#page="+str(page) if page else "")))
        if len(result) >= limit:
            break
    return result


if __name__ == "__main__":
    try:
        operation = sys.argv[1] if len(sys.argv)>1 else "status"
        if operation == "build":
            os.nice(10)
            request = json.loads(sys.stdin.readline(64000))
            result = build(request.get("roots", []))
        elif operation == "search":
            result = dict(ok=True, rows=search(sys.argv[2][:500]))
        else:
            result = dict(ok=True, **status())
        print(json.dumps(result), flush=True)
    except (OSError, ValueError, sqlite3.Error):
        print(json.dumps(dict(ok=False, error="Index unavailable or busy. Try refreshing again.")), flush=True)
        sys.exit(1)
