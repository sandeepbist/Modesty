#!/usr/bin/env python3
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/notes.py"
spec = importlib.util.spec_from_file_location("notes_storage", SCRIPT)
notes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notes)


with tempfile.TemporaryDirectory(prefix="modesty-notes-") as temporary:
    workspace = Path(temporary)
    environment = dict(os.environ, XDG_STATE_HOME=str(workspace))
    folder = workspace / "modesty"
    path = folder / "notes.json"
    revision = 0

    def call(value=None, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(value or {"action": "load"}),
                                text=True, capture_output=True, env=environment, timeout=10)
        response = json.loads(result.stdout)
        assert response["ok"] is success and (result.returncode == 0) is success, response
        return response

    def request(command, operation, expected=None, success=True):
        global revision
        response = call({"action": "request", "command": command, "operationId": operation,
                         "expectedStoreRevision": revision if expected is None else expected}, success)
        if response.get("store"):
            revision = response["store"]["revision"]
        return response

    assert call()["store"] == notes.blank()
    body = "First line\nMarkdown **bold**\nनमस्ते 📝\n$(do not run) `literal`"
    create = {"kind": "create", "title": "Unicode", "body": body}
    created = request(create, "create-1")
    identity = created["id"]
    assert created["status"] == "persisted" and created["revision"] == 1
    assert path.stat().st_mode & 0o777 == 0o600
    assert folder.stat().st_mode & 0o777 == 0o700
    assert (folder / "notes.lock").stat().st_mode & 0o777 == 0o600
    assert call()["store"]["items"][0]["body"] == body
    duplicate = request(create, "create-1", expected=0)
    assert duplicate["id"] == identity and duplicate["store"]["revision"] == 1
    assert request({**create, "body": "different"}, "create-1", success=False)["status"] == "refused"

    stale = request({"kind": "append", "id": identity, "expectedRevision": 1, "body": "\nmore"}, "stale", expected=0, success=False)
    assert stale["status"] == "conflict" and stale["store"]["revision"] == 1
    append = {"kind": "append", "id": identity, "expectedRevision": 1, "body": "\nmore"}
    added = request(append, "append-1")
    assert added["revision"] == 2 and added["store"]["items"][0]["body"] == body + "\nmore"
    assert request(append, "append-1", expected=0)["revision"] == 2
    assert request({**append, "body": "stale"}, "append-stale", success=False)["status"] == "conflict"
    assert (folder / "notes.backup.json").stat().st_mode & 0o777 == 0o600
    assert notes.read_private(folder / "notes.backup.json")["items"][0]["revision"] == 1
    backup = folder / "notes.backup.json"
    confirmed, saved_backup = path.read_bytes(), backup.read_bytes()
    refusal = request({"kind": "recover"}, "recover-valid", success=False)
    assert refusal["status"] == "refused", refusal
    assert path.read_bytes() == confirmed and backup.read_bytes() == saved_backup
    assert call()["store"]["items"][0]["body"] == body + "\nmore"

    selected = call({"action": "select", "activeId": identity, "expectedStoreRevision": revision})
    revision = selected["store"]["revision"]
    assert call()["store"]["selection"]["activeId"] == identity
    pinned = request({"kind": "pin", "id": identity, "expectedRevision": 2, "pinned": True}, "pin-1")
    assert pinned["store"]["items"][0]["pinned"]
    archived = request({"kind": "status", "id": identity, "expectedRevision": 3, "status": "archived"}, "archive-1")
    assert not archived["store"]["items"][0]["pinned"]
    assert request({"kind": "pin", "id": identity, "expectedRevision": 4, "pinned": True}, "pin-archived", success=False)["status"] == "refused"
    assert request({"kind": "delete", "id": identity, "expectedRevision": 4}, "delete-active", success=False)["status"] == "refused"

    exported = workspace / "export.md"
    result = request({"kind": "export", "ids": [identity], "destination": str(exported)}, "export-1")
    assert result["status"] == "verified" and result["path"] == str(exported)
    assert exported.read_text() == "# Unicode\n\n" + body + "\nmore\n"
    assert exported.stat().st_mode & 0o777 == 0o600
    assert request({"kind": "export", "ids": [identity], "destination": str(path)}, "export-private", success=False)["status"] == "refused"
    exported.write_text("Existing unrelated document")
    assert request({"kind": "export", "ids": [identity], "destination": str(exported)}, "export-existing", success=False)["status"] == "refused"
    assert exported.read_text() == "Existing unrelated document"

    good = path.read_bytes()
    current = notes.read_private(path)
    original_replace = os.replace
    def fail_primary(source, destination):
        if Path(destination) == path:
            raise OSError("simulated disk failure")
        original_replace(source, destination)
    with patch.object(notes.os, "replace", side_effect=fail_primary):
        try:
            notes.transact({"action": "request", "command": {"kind": "update", "id": identity, "expectedRevision": 4, "body": "Never committed"},
                            "operationId": "fail-1", "expectedStoreRevision": revision}, folder)
            raise AssertionError("Write failure accepted")
        except OSError:
            pass
    assert path.read_bytes() == good
    assert not list(folder.glob(".notes-*"))
    assert notes.read_private(folder / "notes.backup.json") == current

    path.write_text('{"version":1,"items":broken}')
    assert not call(success=False)["ok"]
    assert request({"kind": "create", "body": "Must not replace corrupt notes"}, "bad-create", success=False)["readFailed"]
    assert path.read_text() == '{"version":1,"items":broken}'
    saved_backup = backup.read_bytes()
    recovered = request({"kind": "recover"}, "recover-1")
    assert recovered["store"]["items"] == current["items"] and recovered["store"]["revision"] > current["revision"]
    assert backup.read_bytes() == saved_backup and notes.read_private(backup) == current
    confirmed = path.read_bytes()
    assert request({"kind": "recover"}, "recover-1", expected=0) == recovered
    assert path.read_bytes() == confirmed and backup.read_bytes() == saved_backup
    path.unlink()
    recovered_missing = request({"kind": "recover"}, "recover-missing", expected=0)
    assert recovered_missing["store"]["items"] == current["items"]
    assert recovered_missing["store"]["revision"] == current["revision"] + 1
    assert backup.read_bytes() == saved_backup
    confirmed = path.read_bytes()
    assert request({"kind": "recover"}, "recover-missing", expected=0) == recovered_missing
    assert path.read_bytes() == confirmed and backup.read_bytes() == saved_backup

    trash = request({"kind": "status", "id": identity, "expectedRevision": 4, "status": "trash"}, "trash-1")
    assert trash["revision"] == 5
    removed = request({"kind": "delete", "id": identity, "expectedRevision": 5}, "delete-1")
    assert not removed["store"]["items"] and removed["store"]["selection"]["activeId"] == ""
    assert request({"kind": "create", "body": ""}, "empty", success=False)["status"] == "refused"
    assert request({"kind": "create", "body": "x", "title": "x" * 301}, "too-long", success=False)["status"] == "refused"

    payloads = [{"action": "request", "expectedStoreRevision": revision, "operationId": f"race-{index}",
                 "command": {"kind": "create", "body": f"Writer {index}"}} for index in range(2)]
    children = [subprocess.Popen([sys.executable, str(SCRIPT)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, env=environment) for _ in payloads]
    for child, payload in zip(children, payloads):
        child.stdin.write(json.dumps(payload)); child.stdin.close()
    responses = [json.loads(child.stdout.read()) for child in children]
    for child in children:
        child.wait(timeout=10)
    assert sorted(response["status"] for response in responses) == ["conflict", "persisted"]
    assert len(call()["store"]["items"]) == 1
    revision = call()["store"]["revision"]

    lost_command = {"kind": "create", "id": "lost-ack-create", "body": "Persisted before acknowledgement 📝"}
    original_sync = notes.sync_directory
    def lose_commit_acknowledgement(destination):
        original_sync(destination)
        if notes.read_private(path)["revision"] > revision:
            raise OSError("simulated failure after primary replacement")
    with patch.object(notes, "sync_directory", side_effect=lose_commit_acknowledgement):
        try:
            notes.transact({"action": "request", "command": lost_command,
                            "operationId": "lost-commit-ack", "expectedStoreRevision": revision}, folder)
            raise AssertionError("Post-replacement failure was not injected")
        except OSError:
            pass
    persisted_revision = notes.read_private(path)["revision"]
    retried = request(lost_command, "lost-commit-ack", expected=revision)
    assert retried["id"] == "lost-ack-create" and retried["store"]["revision"] == persisted_revision
    assert len([value for value in retried["store"]["items"] if value["id"] == "lost-ack-create"]) == 1

    for index in range(notes.MAX_RECEIPTS + 3):
        request({"kind": "create", "body": str(index)}, f"bounded-{index}")
    assert len(call()["store"]["receipts"]) == notes.MAX_RECEIPTS
    stored = notes.read_private(path)
    malformed = copy.deepcopy(stored)
    malformed["items"][0]["revision"] = True
    try:
        notes.validate(malformed)
        raise AssertionError("Boolean revision accepted")
    except ValueError:
        pass
    path.unlink()
    path.symlink_to(exported)
    assert not call(success=False)["ok"] and exported.read_text() == "Existing unrelated document"

print("PASS Notes persistence, Unicode, revisions, duplicate retries, private files, safe recovery, missing-store recovery, recovery replay, write failure, export and concurrent writers")
