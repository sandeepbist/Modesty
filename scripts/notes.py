#!/usr/bin/env python3
import contextlib
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
import uuid

MAX_ITEMS = 2048
MAX_BODY = 1_000_000
MAX_FILE = 32 * 1024 * 1024
MAX_RECEIPTS = 128
ID = re.compile(r"[a-z0-9-]{1,80}\Z")
OPERATION = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
STATUSES = {"active", "archived", "trash"}


class Refused(ValueError):
    pass


class Conflict(ValueError):
    pass


class ReadFailure(Refused):
    pass


def integer(value, minimum=0):
    return type(value) is int and minimum <= value <= 9_007_199_254_740_991


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def text(value, limit, label):
    if not isinstance(value, str) or len(value) > limit or "\x00" in value:
        raise Refused(f"Invalid note {label}")
    return value


def blank():
    return {"version": 1, "revision": 0, "items": [], "receipts": [], "selection": {"activeId": ""}}


def validate(data):
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1 or not integer(data.get("revision")):
        raise Refused("Invalid notes file")
    items = data.get("items")
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise Refused("Invalid notes collection")
    seen = set()
    for note in items:
        if not isinstance(note, dict) or not isinstance(note.get("id"), str) or not ID.fullmatch(note["id"]) or note["id"] in seen:
            raise Refused("Invalid note id")
        seen.add(note["id"])
        text(note.get("title"), 300, "title")
        text(note.get("body"), MAX_BODY, "body")
        if not isinstance(note.get("status"), str) or note["status"] not in STATUSES or type(note.get("pinned")) is not bool or (note["status"] != "active" and note["pinned"]):
            raise Refused("Invalid note status")
        if not integer(note.get("revision"), 1):
            raise Refused("Invalid note revision")
        for field in ("createdAt", "updatedAt"):
            value = note.get(field)
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", value):
                raise Refused("Invalid note date")
            datetime.fromisoformat(value.replace("Z", "+00:00"))
    selection = data.get("selection")
    if not isinstance(selection, dict) or not isinstance(selection.get("activeId"), str) or selection["activeId"] not in seen | {""}:
        raise Refused("Invalid active note")
    receipts = data.get("receipts")
    if not isinstance(receipts, list) or len(receipts) > MAX_RECEIPTS:
        raise Refused("Invalid operation receipts")
    operations = set()
    for receipt in receipts:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("operationId"), str) or not OPERATION.fullmatch(receipt["operationId"]) or receipt["operationId"] in operations:
            raise Refused("Invalid operation receipt")
        operations.add(receipt["operationId"])
        if not isinstance(receipt.get("fingerprint"), str) or not re.fullmatch(r"[a-f0-9]{64}", receipt["fingerprint"]):
            raise Refused("Invalid operation fingerprint")
        result = receipt.get("result")
        if not isinstance(result, dict) or result.get("ok") is not True or result.get("status") not in ("persisted", "verified") or result.get("ticket") != receipt["operationId"] or not integer(result.get("revision")):
            raise Refused("Invalid operation result")
        if not isinstance(result.get("id", ""), str) or (result.get("id", "") and not ID.fullmatch(result["id"])):
            raise Refused("Invalid operation note")
    return data


def encoded(data):
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(payload) > MAX_FILE:
        raise Refused("Notes storage is full. Export or remove old notes.")
    return payload


def read_private(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Refused("Notes storage is not a regular file")
        payload = stream.read(MAX_FILE + 1)
    if len(payload) > MAX_FILE:
        raise Refused("Notes file exceeds the storage limit")
    return validate(json.loads(payload.decode("utf-8")))


def sync_directory(folder):
    descriptor = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic(path, data):
    payload = encoded(validate(data))
    descriptor, temporary = tempfile.mkstemp(prefix=".notes-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def locked(folder):
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    if folder.is_symlink():
        raise Refused("Notes directory cannot be a symbolic link")
    os.chmod(folder, 0o700)
    descriptor = os.open(folder / "notes.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise Refused("Notes lock is not a regular file")
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def export_notes(folder, command, items, operation_id):
    ids = command.get("ids")
    if not isinstance(ids, list) or not 1 <= len(ids) <= MAX_ITEMS or any(not isinstance(value, str) for value in ids) or len(set(ids)) != len(ids):
        raise Refused("Choose notes to export")
    notes = {note["id"]: note for note in items}
    if any(value not in notes for value in ids):
        raise Refused("An export note no longer exists")
    destination = command.get("destination")
    if destination is not None and (not isinstance(destination, str) or not destination or "\x00" in destination):
        raise Refused("Invalid export destination")
    suffix = hashlib.sha256(operation_id.encode()).hexdigest()[:12]
    path = Path(destination).expanduser() if destination else Path.home() / "Downloads" / f"Modesty Notes-{suffix}.md"
    if not path.is_absolute() or path.suffix.lower() not in (".md", ".txt"):
        raise Refused("Choose an absolute Markdown or text destination")
    if path.resolve().is_relative_to(folder.resolve()):
        raise Refused("Cannot export into private notes storage")
    payload = "\n\n---\n\n".join(("# " + notes[value]["title"] + "\n\n" if notes[value]["title"] else "") + notes[value]["body"] for value in ids).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or stream.read(len(payload) + 1) != payload:
                raise Refused("Export destination already exists")
    else:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(path.parent)
    return str(path)


def mutate(data, command, folder, operation_id):
    kind = command.get("kind")
    if kind not in ("create", "update", "append", "pin", "status", "delete", "export", "recover"):
        raise Refused("Unknown notes operation")
    result = {"ok": True, "ticket": operation_id, "id": "", "revision": 0, "status": "persisted", "error": ""}
    if kind == "export":
        result.update(status="verified", path=export_notes(folder, command, data["items"], operation_id))
        return result
    if kind == "recover":
        return result
    if kind == "create":
        if len(data["items"]) >= MAX_ITEMS:
            raise Refused("Notes storage is full. Export or remove old notes.")
        title = text(command.get("title", ""), 300, "title")
        body = text(command.get("body", ""), MAX_BODY, "body")
        if not title.strip() and not body.strip():
            raise Refused("Empty notes are not saved")
        identity = command.get("id", uuid.uuid4().hex)
        if not isinstance(identity, str) or not ID.fullmatch(identity) or any(note["id"] == identity for note in data["items"]):
            raise Refused("Invalid or duplicate note id")
        stamp = now()
        note = {"id": identity, "title": title, "body": body, "createdAt": stamp, "updatedAt": stamp, "status": "active", "pinned": False, "revision": 1}
        data["items"].append(note)
    else:
        identity = command.get("id")
        note = next((note for note in data["items"] if note["id"] == identity), None)
        if note is None:
            raise Refused("Note no longer exists")
        if not integer(command.get("expectedRevision"), 1):
            raise Refused("Read the note revision before changing it")
        if command["expectedRevision"] != note["revision"]:
            raise Conflict("Note changed. Read its current revision and retry.")
        if kind == "delete":
            if note["status"] != "trash":
                raise Refused("Move a note to Trash before deleting it permanently")
            data["items"].remove(note)
            if data["selection"]["activeId"] == identity:
                data["selection"]["activeId"] = ""
            result.update(id=identity, revision=note["revision"] + 1)
            return result
        before = dict(note)
        if kind == "update":
            if "title" not in command and "body" not in command:
                raise Refused("No note changes supplied")
            for field, limit in (("title", 300), ("body", MAX_BODY)):
                if field in command:
                    note[field] = text(command[field], limit, field)
        elif kind == "append":
            addition = text(command.get("body"), MAX_BODY, "body")
            if not addition:
                raise Refused("No text to append")
            note["body"] = text(note["body"] + addition, MAX_BODY, "body")
        elif kind == "pin":
            if type(command.get("pinned")) is not bool or note["status"] != "active":
                raise Refused("Only active notes can be pinned")
            note["pinned"] = command["pinned"]
        elif kind == "status":
            if command.get("status") not in STATUSES:
                raise Refused("Invalid note status")
            note["status"] = command["status"]
            if note["status"] != "active":
                note["pinned"] = False
        if note != before:
            note["revision"] += 1
            note["updatedAt"] = now()
    result.update(id=note["id"], revision=note["revision"])
    return result


def transact(request, folder):
    if not isinstance(request, dict):
        raise Refused("Invalid notes request")
    path, backup = folder / "notes.json", folder / "notes.backup.json"
    with locked(folder):
        action = request.get("action", "load")
        recovering = action == "request" and isinstance(request.get("command"), dict) and request["command"].get("kind") == "recover"
        try:
            current = read_private(path)
        except FileNotFoundError:
            current = None if recovering else blank()
        except (ValueError, TypeError, UnicodeError, OSError):
            if not recovering:
                raise ReadFailure("Could not read notes. Retry or recover the validated backup.")
            current = None
        if action == "load":
            return {"ok": True, "store": current}
        if action not in ("request", "select"):
            raise Refused("Unknown notes transaction")
        if not integer(request.get("expectedStoreRevision")):
            raise Refused("Missing notes store revision")
        operation_id = request.get("operationId", "")
        command = request.get("command")
        if action == "request":
            if not isinstance(command, dict) or not isinstance(operation_id, str) or not OPERATION.fullmatch(operation_id):
                raise Refused("Invalid notes command or operation id")
            fingerprint = hashlib.sha256(encoded(command)).hexdigest()
            if current is not None:
                prior = next((receipt for receipt in current["receipts"] if receipt["operationId"] == operation_id), None)
                if prior:
                    if prior["fingerprint"] != fingerprint:
                        raise Refused("Operation id was already used for another command")
                    return {**prior["result"], "store": current}
        if recovering and current is not None:
            raise Refused("Current notes are valid. Recovery is not available.")
        if current is not None and current["revision"] != request["expectedStoreRevision"]:
            return {"ok": False, "status": "conflict", "error": "Notes changed in another session. Reload before saving.", "store": current}
        if recovering:
            try:
                data = copy.deepcopy(read_private(backup))
            except (ValueError, TypeError, UnicodeError, OSError) as error:
                raise Refused("No validated notes backup is available") from error
            data["revision"] = max(data["revision"], current["revision"] if current else 0)
        else:
            data = copy.deepcopy(current)
        if action == "select":
            identity = request.get("activeId")
            if identity not in {note["id"] for note in data["items"]} | {""}:
                raise Refused("Note no longer exists")
            data["selection"] = {"activeId": identity}
            result = {"ok": True, "status": "persisted"}
        else:
            result = mutate(data, command, folder, operation_id)
            data["receipts"] = [receipt for receipt in data["receipts"] if receipt["operationId"] != operation_id]
            data["receipts"].append({"operationId": operation_id, "fingerprint": fingerprint, "result": result})
            data["receipts"] = data["receipts"][-MAX_RECEIPTS:]
        if "activeId" in request and action == "request":
            identity = request["activeId"]
            if identity in {note["id"] for note in data["items"]} | {""}:
                data["selection"] = {"activeId": identity}
        data["revision"] += 1
        validate(data)
        encoded(data)
        if not recovering and current is not None and path.exists():
            atomic(backup, current)
        atomic(path, data)
        return {**result, "store": data}


def main():
    folder = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "modesty"
    try:
        if len(sys.argv) != 1:
            raise Refused("Notes requests must arrive on stdin")
        line = sys.stdin.buffer.readline(MAX_FILE + 1)
        if len(line) > MAX_FILE:
            raise Refused("Notes request exceeds the storage limit")
        request = json.loads(line) if line.strip() else {"action": "load"}
        response = transact(request, folder)
    except Conflict as error:
        response = {"ok": False, "status": "conflict", "error": str(error)}
    except ReadFailure as error:
        response = {"ok": False, "status": "failed", "readFailed": True, "error": str(error)}
    except (ValueError, TypeError, UnicodeError) as error:
        response = {"ok": False, "status": "refused", "error": str(error)}
    except OSError as error:
        response = {"ok": False, "status": "failed", "error": f"Could not save notes: {error.strerror or str(error)}"}
    print(json.dumps(response, ensure_ascii=False))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
