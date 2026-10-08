#!/usr/bin/env python3
"""Local file index and clipboard adapter for Quick Search."""
import fcntl
import importlib.util
from datetime import datetime
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote_plus, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

HOME = Path.home()
CACHE = Path(os.environ.get("XDG_CACHE_HOME", HOME / ".cache")) / "modesty"
INDEX = CACHE / "command-files.sqlite3"
AI_KEY = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "modesty" / "gemini.key"
SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".Trash", "Trash", "target", "build", "dist", ".next", ".turbo"}
ROOTS = ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos", "App", "Projects", ".config/hypr", ".config/modesty", ".config/foot", ".config/fish")
LIMIT = 250_000


def emit(**data):
    print(json.dumps(data, ensure_ascii=False), flush=True)


def index_files():
    CACHE.mkdir(parents=True, exist_ok=True)
    with (CACHE / "command-files.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if INDEX.exists() and time.time() - INDEX.stat().st_mtime < 60:
            emit(ok=True, indexed=True)
            return
        temp = INDEX.with_suffix(".building")
        temp.unlink(missing_ok=True)
        db = sqlite3.connect(temp)
        try:
            db.execute("CREATE VIRTUAL TABLE files USING fts5(path UNINDEXED, name, folder, kind UNINDEXED, modified UNINDEXED)")
            rows = []
            stack = [HOME / name for name in ROOTS if (HOME / name).is_dir()]
            count = 0
            while stack and count < LIMIT:
                folder = stack.pop()
                try:
                    entries = os.scandir(folder)
                    with entries:
                        for item in entries:
                            if item.name in SKIP or item.is_symlink():
                                continue
                            try:
                                directory = item.is_dir(follow_symlinks=False)
                                if not directory and not item.is_file(follow_symlinks=False):
                                    continue
                                stat = item.stat(follow_symlinks=False)
                            except OSError:
                                continue
                            if directory:
                                stack.append(Path(item.path))
                            rows.append((item.path, item.name, str(folder.relative_to(HOME)), "folder" if directory else "file", int(stat.st_mtime)))
                            count += 1
                            if len(rows) >= 1000:
                                db.executemany("INSERT INTO files(path,name,folder,kind,modified) VALUES (?,?,?,?,?)", rows)
                                rows.clear()
                            if count >= LIMIT:
                                break
                except OSError:
                    continue
            if rows:
                db.executemany("INSERT INTO files(path,name,folder,kind,modified) VALUES (?,?,?,?,?)", rows)
            db.commit()
        finally:
            db.close()
        temp.replace(INDEX)
        emit(ok=True, indexed=True, count=count, limited=count >= LIMIT)


def fetch_file_rows(query):
    if not INDEX.exists() or not query.strip():
        return []
    terms = re.findall(r"[\w]+", query.casefold(), re.UNICODE)[:8]
    if not terms:
        return []
    expression = " AND ".join('"' + term.replace('"', '') + '"*' for term in terms)
    try:
        db = sqlite3.connect(f"file:{INDEX}?mode=ro", uri=True, timeout=1)
        rows = db.execute("SELECT path,name,folder,kind,modified FROM files WHERE files MATCH ? ORDER BY bm25(files,0,3,0.45), modified DESC LIMIT 35", (expression,)).fetchall()
        db.close()
    except (sqlite3.Error, OSError):
        rows = []
    return [dict(path=p, title=n, subtitle=str(Path(p).parent).replace(str(HOME), "~", 1), kind=k, modified=m) for p,n,folder,k,m in rows]


def search_files(query):
    emit(ok=True, query=query, rows=fetch_file_rows(query), indexed=INDEX.exists())

def clipboard_list():
    try:
        raw = subprocess.run(["cliphist", "list"], capture_output=True, text=True, timeout=2, check=True).stdout
        rows = []
        for line in raw.splitlines()[:100]:
            match = re.match(r"^(\d+)\s+(.+)$", line)
            if match:
                rows.append(dict(id=match.group(1), title=match.group(2).strip()[:180]))
        emit(ok=True, rows=rows)
    except (OSError, subprocess.SubprocessError) as error:
        emit(ok=False, rows=[], error=str(error))


def knowledge_adapter():
    spec = importlib.util.spec_from_file_location("knowledge", Path(__file__).with_name("luma-knowledge.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def search_contents(query):
    knowledge = knowledge_adapter()
    if knowledge.roots():
        emit(ok=True, query=query, rows=knowledge.search(query))
        return
    if len(query.strip()) < 3:
        emit(ok=True, query=query, rows=[])
        return
    roots = [str(HOME / name) for name in ROOTS[:8] if (HOME / name).is_dir()]
    args = ["rg", "--files-with-matches", "--null", "--ignore-case", "--fixed-strings", "--max-filesize", "1M", "--no-messages"]
    for name in SKIP | {".env", "*.key", "*.pem"}:
        args.extend(("--glob", "!**/" + name + "/**" if "*" not in name and not name.startswith(".") else "!" + name))
    try:
        found = subprocess.run(args + ["--", query] + roots, capture_output=True, timeout=4).stdout.split(b"\0")[:35]
        rows = []
        for value in found:
            if not value:
                continue
            path = os.fsdecode(value)
            rows.append(dict(path=path, title=Path(path).name, subtitle=str(Path(path).parent).replace(str(HOME), "~", 1), kind="content"))
        emit(ok=True, query=query, rows=rows)
    except (OSError, subprocess.SubprocessError) as error:
        emit(ok=False, query=query, rows=[], error=str(error))


def search_browser(query):
    if len(query.strip()) < 2:
        emit(ok=True, query=query, rows=[])
        return
    profile = next((path for root in (HOME / ".zen", HOME / ".mozilla/firefox") if root.is_dir() for path in root.glob("*/places.sqlite")), None)
    if not profile:
        emit(ok=True, query=query, rows=[])
        return
    value = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    try:
        db = sqlite3.connect(profile.as_uri() + "?immutable=1", uri=True, timeout=.3)
        matches = db.execute("""SELECT p.url, coalesce(p.title,p.url),
            EXISTS(SELECT 1 FROM moz_bookmarks b WHERE b.fk=p.id AND b.type=1) AS bookmarked
            FROM moz_places p WHERE p.url LIKE 'http%' AND
            (p.title LIKE ? ESCAPE '\\' OR p.url LIKE ? ESCAPE '\\')
            ORDER BY bookmarked DESC, p.frecency DESC, p.last_visit_date DESC LIMIT 18""", (value,value)).fetchall()
        db.close()
        rows = [dict(url=url,title=title[:160],subtitle=(urlsplit(url).hostname or "Web"),kind="bookmark" if bookmarked else "history") for url,title,bookmarked in matches]
        emit(ok=True, query=query, rows=rows)
    except (sqlite3.Error, OSError, ValueError):
        emit(ok=True, query=query, rows=[])


class LiveResults(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.current = None
        self.capture = ""
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get("class", "").split()
        if tag == "a" and "result-link" in classes:
            target = parse_qs(urlsplit(attributes.get("href", "")).query).get("uddg", [""])[0]
            if urlsplit(target).scheme in {"http", "https"}:
                self.current = {"url": target, "title": "", "subtitle": ""}
                self.capture, self.parts = "title", []
        elif tag == "td" and "result-snippet" in classes and self.current:
            self.capture, self.parts = "subtitle", []

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if (tag == "a" and self.capture == "title") or (tag == "td" and self.capture == "subtitle"):
            value = " ".join(" ".join(self.parts).split())
            self.current[self.capture] = value[:240]
            self.capture = ""
            if tag == "td" and self.current["title"]:
                self.rows.append(self.current)
                self.current = None


def online_cache_path(query):
    return CACHE / "command-web" / (hashlib.sha256(("2:"+query).encode()).hexdigest()[:32] + ".json")


def cached_online_rows(query):
    for cache in (online_cache_path(query), CACHE / "command-web.json"):
        try:
            if time.time() - cache.stat().st_mtime < 90:
                data = json.loads(cache.read_text())
                if data.get("query") == query and isinstance(data.get("rows"), list) and (not current_query(query) or any(row.get("published") for row in data["rows"])):
                    return data["rows"]
        except (OSError, ValueError):
            pass
    return []


def fetch_online_rows(query):
    cache = online_cache_path(query)
    cache.parent.mkdir(parents=True, exist_ok=True)
    # Partition network locks so unrelated queries usually run concurrently.
    # ponytail: 256 lock shards bound file count; collisions may serialize two
    # different queries. Increase shards only if measured contention matters.
    with (cache.parent / (cache.stem[:2] + ".lock")).open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        rows = cached_online_rows(query)
        if rows:
            return rows
        try:
            rows = download_news_rows(query) if current_query(query) else download_online_rows(query)
        except (OSError, ValueError):
            rows = []
        if not rows and current_query(query):
            try:
                rows = download_online_rows(query + " " + str(datetime.now().year))
            except (OSError, ValueError):
                pass
        if not rows:
            # Independent search transport; never turn an engine challenge into
            # proof that the user's question has no answer.
            request = Request("https://www.bing.com/search?" + urlencode({"q": query[:240], "format": "rss"}),
                              headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urlopen(request, timeout=5) as response:
                    feed = ElementTree.fromstring(response.read(262_144))
                for item in feed.findall("./channel/item")[:8]:
                    url = item.findtext("link", "")
                    if urlsplit(url).scheme not in {"https", "http"}:
                        continue
                    host = (urlsplit(url).hostname or "Web").removeprefix("www.")
                    snippet = item.findtext("description", "")[:1600]
                    rows.append({"title": item.findtext("title", host), "url": url, "host": host,
                                 "snippet": snippet, "subtitle": host + " · " + snippet})
            except (OSError, ValueError, ElementTree.ParseError):
                pass
        if rows:
            with tempfile.NamedTemporaryFile(mode="w", dir=cache.parent, delete=False) as temp:
                json.dump({"query": query, "rows": rows}, temp)
                temporary = temp.name
            os.replace(temporary, cache)
            # Keep only a small recent search cache; lock files remain stable.
            try:
                entries = sorted(cache.parent.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                for expired in entries[128:]:
                    expired.unlink(missing_ok=True)
            except OSError:
                pass
        return rows


def current_query(query):
    if re.match(r"^(?:please\s+)?(?:remind\s+me\b|(?:set|add|create|schedule)\s+(?:a\s+)?reminder\b)", query.strip(), re.I):
        return False
    return bool(re.search(r"\b(?:latest|news|today|current|recent|breaking|this week|this month|updates?)\b", query, re.I))


def download_news_rows(query):
    # Dated headline evidence, never pretend the feed contains full articles.
    topic = re.split(r"[?!;\n]|\s+and\s+(?:summarize|explain|include|list)\b", query.strip(), maxsplit=1, flags=re.I)[0]
    terms = re.sub(r"^(?:please\s+)?(?:what(?:'s| is| are)|show me|give me|tell me about|find)\s+", "", topic, flags=re.I)
    terms = re.sub(r"\b(?:the latest|latest|recent|current|news|reports?|updates?)\b", " ", terms, flags=re.I)
    terms = re.sub(r"\bthis\s+(?:week|month)\b", " ", terms, flags=re.I)
    terms = re.sub(r"^(?:\s*(?:the|on|about|in|for|of)\b)+\s*", "", terms, flags=re.I).strip()
    terms = " ".join(terms.split()) or query
    window = "when:30d" if re.search(r"\bmonth\b", query, re.I) else "when:1d" if re.search(r"\b(?:today|breaking)\b", query, re.I) else "when:7d"
    request = Request("https://news.google.com/rss/search?" + urlencode({"q": terms[:220]+" "+window, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}), headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=5) as response:
        try:
            feed = ElementTree.fromstring(response.read(524_288))
        except ElementTree.ParseError as error:
            raise ValueError("Unreadable news feed") from error
    rows = []
    for item in feed.findall("./channel/item")[:40]:
        url, published = item.findtext("link", ""), item.findtext("pubDate", "")
        try:
            stamp = parsedate_to_datetime(published).timestamp()
        except (ValueError, TypeError):
            continue
        if urlsplit(url).scheme != "https" or stamp > time.time()+300:
            continue
        title = item.findtext("title", "")[:300]
        publisher = item.findtext("source", "News")
        rows.append({"title": title, "url": url, "host": publisher, "published": published, "headlineOnly": True,
                     "snippet": title + " · Published " + published + ". Headline evidence only; article content was not retrieved.",
                     "subtitle": publisher + " · " + datetime.fromtimestamp(stamp).strftime("%d %b %Y"), "stamp": stamp})
    # Keep the search engine's relevance ranking; dates remain explicit evidence.
    return rows[:8]


def download_online_rows(query):
    url = "https://lite.duckduckgo.com/lite/?q=" + quote_plus(query[:100])
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=4) as response:
        page = response.read(262_144).decode("utf-8", "replace")
    parser = LiveResults()
    parser.feed(page)
    rows = []
    for row in parser.rows[:12]:
        host = (urlsplit(row["url"]).hostname or "Web").removeprefix("www.")
        row["snippet"] = row["subtitle"]
        row["host"] = host
        row["subtitle"] = host + (" · " + row["snippet"] if row["snippet"] else "")
        rows.append(row)
    return rows


def search_online(query):
    query = query.strip()
    if len(query) < 3:
        emit(ok=True, query=query, rows=[])
        return
    try:
        rows = fetch_online_rows(query)
        emit(ok=True, query=query, rows=rows)
    except (OSError, ValueError) as error:
        emit(ok=False, query=query, rows=[], error=str(error)[:120])


def quick_answer(query):
    """Show an attributed instant answer when the source supplies one."""
    query = query.strip()
    entity = re.fullmatch(r"(?:what|who) (?:is|was|are|were) (?:an? |the )?(.+?)[?.!]*", query, re.I)
    subject = entity.group(1).strip() if entity else ""
    if not subject or len(subject) > 80 or re.search(r"\b(?:and|or|why|how|when|where)\b", subject, re.I):
        emit(ok=True, query=query, answer=None)
        return
    url = "https://api.duckduckgo.com/?q=" + quote_plus(subject) + "&format=json&no_html=1&skip_disambig=1"
    try:
        request = Request(url, headers={"User-Agent": "Modesty Quick Search/1.0"})
        with urlopen(request, timeout=3) as response:
            data = json.load(response)
        abstract = " ".join(data.get("AbstractText", "").split())
        source = data.get("AbstractURL", "")
        if abstract and urlsplit(source).scheme == "https":
            title = data.get("Heading", "")
            hostname = (urlsplit(source).hostname or "Web").removeprefix("www.")
            answer = {"title": title or "Quick answer", "text": abstract, "source": source, "sourceName": "Wikipedia" if hostname == "wikipedia.org" or hostname.endswith(".wikipedia.org") else hostname, "label": "Overview"}
        else:
            answer = None
        emit(ok=True, query=query, answer=answer)
    except (OSError, ValueError, json.JSONDecodeError):
        emit(ok=True, query=query, answer=None)


def ai_answer(query, rows, key, model):
    if model not in {"gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"}:
        return None
    sources = [row for row in rows if row.get("snippet")][:5]
    if not sources:
        return None
    evidence = "\n".join(f"[{index}] {row['title']}: {row['snippet']}" for index, row in enumerate(sources, 1))
    payload = {
        "contents": [{"parts": [{"text": "Answer every part of the question directly and completely using only the cited live sources. For a process, explain its main stages as numbered steps. Use plain text with short paragraphs, without Markdown headings or emphasis. Keep the answer under 220 words, but do not cut a sentence short. If sources do not support an answer, return an empty answer. Return JSON with answer and source_ids (1-based). Do not invent facts.\nQuestion: " + query + "\nSources:\n" + evidence}]}],
        "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 800},
    }
    models = [model, "gemini-3.1-flash-lite" if model == "gemini-3.5-flash-lite" else "gemini-3.5-flash-lite"]
    for candidate in models:
        request = Request(f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent",
                          data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urlopen(request, timeout=12) as response:
                data = json.load(response)
            break
        except HTTPError as error:
            if error.code not in {502, 503, 504}:
                raise
            if candidate == models[-1]:
                raise
    content = "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"])
    result = json.loads(content)
    if not isinstance(result, dict) or not isinstance(result.get("source_ids"), list):
        return None
    ids = [int(item) for item in result["source_ids"] if type(item) in (int, str) and str(item).isdigit() and 1 <= int(item) <= len(sources)]
    answer = re.sub(r"[^\S\n]+", " ", str(result.get("answer", ""))).strip()
    if not answer or not ids:
        return None
    cited = [sources[index-1] for index in dict.fromkeys(ids)]
    return {"title": "Answer", "text": answer, "source": cited[0]["url"], "sourceName": cited[0]["host"],
            "label": "AI answer", "citations": [{"title": row["title"], "url": row["url"], "host": row["host"]} for row in cited]}


def source_preview(query, rows):
    """Offer a full article overview for explanatory queries when AI is unavailable."""
    if not re.match(r"^(?:explain|describe|overview|how (?:does|do|is|are))\b", query, re.I):
        return None
    wiki = next((row for row in rows if urlsplit(row["url"]).hostname == "en.wikipedia.org"
                 and urlsplit(row["url"]).path.startswith("/wiki/")), None)
    if not wiki:
        return None
    title = unquote(urlsplit(wiki["url"]).path.removeprefix("/wiki/")).replace("_", " ")
    terms = [word for word in re.findall(r"[a-z]{4,}", query.casefold())
             if word not in {"explain", "describe", "overview", "whole", "entire", "process", "about", "please", "what", "does", "with", "that", "this"}]
    if not terms:
        return None
    params = urlencode({"action": "query", "prop": "extracts", "explaintext": 1, "exintro": 1, "titles": title, "format": "json"})
    request = Request("https://en.wikipedia.org/w/api.php?" + params,
                      headers={"User-Agent": "Modesty/1.0 (desktop search)"})
    try:
        with urlopen(request, timeout=4) as response:
            pages = json.load(response)["query"]["pages"]
        extract = next(iter(pages.values())).get("extract", "").strip()
    except (OSError, ValueError, KeyError, StopIteration):
        return None
    if len(extract) < 120 or (not any(term in title.casefold() for term in terms)
                              and sum(term in extract.casefold() for term in terms) < min(2, len(terms))):
        return None
    return {"title": title, "text": extract, "source": wiki["url"],
            "sourceName": "Wikipedia", "label": "Overview"}


def generate_answer(query, model):
    query = query.strip()
    key = os.environ.get("GEMINI_API_KEY", "").strip() or (AI_KEY.read_text().strip() if AI_KEY.is_file() else "")
    if len(query) < 4:
        emit(ok=True, query=query, answer=None, reason="short_query")
        return
    try:
        rows = fetch_online_rows(query)
        overview = source_preview(query, rows)
        if overview:
            rows = [{"url": overview["source"], "title": overview["title"],
                     "host": overview["sourceName"], "snippet": overview["text"]}] + [
                         row for row in rows if row["url"] != overview["source"]]
        try:
            answer = ai_answer(query, rows, key, model) if rows and key else None
            reason = "" if answer else "no_key" if not key else "no_answer"
        except HTTPError as error:
            answer = None
            reason = "busy" if error.code == 503 else "quota" if error.code == 429 else "unavailable"
        except (OSError, ValueError, KeyError, IndexError):
            answer = None
            reason = "unavailable"
        answer = answer or overview
        emit(ok=True, query=query, answer=answer, reason=reason)
    except (OSError, ValueError, KeyError, IndexError):
        emit(ok=True, query=query, answer=None, reason="unavailable")


def key_path(provider="gemini"):
    if provider not in {"gemini", "jev"}:
        raise ValueError("Unknown provider")
    return AI_KEY if provider == "gemini" else AI_KEY.with_name("typesafe.key")


def key_status(provider="gemini"):
    emit(ok=True, configured=bool(os.environ.get("GEMINI_API_KEY" if provider == "gemini" else "TYPESAFE_API_KEY", "").strip() or key_path(provider).is_file()))


def key_set(provider="gemini"):
    path = key_path(provider)
    key = sys.stdin.readline().strip()
    if not re.fullmatch(r"[\x21-\x7e]{20,512}", key):
        emit(ok=False, error="Invalid API key")
        return
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as file:
        file.write(key + "\n")
        temp = file.name
    os.chmod(temp, 0o600)
    os.replace(temp, path)
    emit(ok=True, configured=True)


def key_clear(provider="gemini"):
    key_path(provider).unlink(missing_ok=True)
    key_status(provider)


def clipboard_copy(identifier):
    if not identifier.isdecimal():
        raise ValueError("Invalid clipboard entry")
    data = subprocess.run(["cliphist", "decode"], input=identifier.encode(), capture_output=True, timeout=3, check=True).stdout
    subprocess.run(["wl-copy"], input=data, timeout=3, check=True)
    emit(ok=True)


def clipboard_wipe():
    subprocess.run(["cliphist", "wipe"], capture_output=True, timeout=3, check=True)
    emit(ok=True)


def preview(path):
    file = Path(path).expanduser().resolve()
    if not file.is_file() or HOME not in file.parents or file.stat().st_size > 32_000_000:
        emit(ok=False, path=path, text="Preview unavailable")
        return
    suffix = file.suffix.lower()
    if suffix == ".pdf":
        try:
            value = subprocess.run(["pdftotext", "-f", "1", "-l", "2", str(file), "-"], capture_output=True, text=True, timeout=2).stdout[:4000]
        except (OSError, subprocess.SubprocessError):
            value = ""
    elif suffix in {".txt", ".md", ".json", ".py", ".qml", ".js", ".ts", ".rs", ".go", ".lua", ".sh", ".toml", ".yaml", ".yml", ".css", ".html"}:
        value = file.open("r", encoding="utf-8", errors="replace").read(4000)
    else:
        value = ""
    emit(ok=True, path=path, text=value)


if __name__ == "__main__":
    try:
        command = sys.argv[1]
        if command == "index": index_files()
        elif command == "files": search_files(sys.argv[2])
        elif command == "contents": search_contents(sys.argv[2])
        elif command == "browser": search_browser(sys.argv[2])
        elif command == "online": search_online(sys.argv[2])
        elif command == "answer": quick_answer(sys.argv[2])
        elif command == "ai": generate_answer(sys.argv[2], sys.argv[3])
        elif command == "key-status": key_status(sys.argv[2] if len(sys.argv) > 2 else "gemini")
        elif command == "key-set": key_set(sys.argv[2] if len(sys.argv) > 2 else "gemini")
        elif command == "key-clear": key_clear(sys.argv[2] if len(sys.argv) > 2 else "gemini")
        elif command == "clipboard": clipboard_list()
        elif command == "copy": clipboard_copy(sys.argv[2])
        elif command == "wipe": clipboard_wipe()
        elif command == "preview": preview(sys.argv[2])
        else: raise ValueError("Unknown command")
    except Exception as error:
        emit(ok=False, error=str(error))
        sys.exit(1)
