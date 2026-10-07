#!/usr/bin/env python3
"""Check V2 task metadata without loading messages or provider secrets."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('t3_status', ROOT / 'scripts/t3-status.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    (folder / 'server-runtime.json').write_text(json.dumps(dict(pid=os.getpid(), startedAt='2026-01-01T00:00:00Z')))
    # A legacy database can still exist after migration; never prefer it to V2.
    (folder / 'state.sqlite').write_text('obsolete database')
    with sqlite3.connect(folder / 'statev2.sqlite') as c:
        c.executescript('''
            CREATE TABLE orchestration_v2_projection_threads(thread_id,deleted_at,archived_at);
            CREATE TABLE orchestration_v2_projection_provider_threads(provider_thread_id,provider,status);
            CREATE TABLE orchestration_v2_projection_provider_turns(provider_thread_id,provider_turn_id,thread_id,ordinal,status,started_at,completed_at);
            CREATE TABLE orchestration_v2_projection_runtime_requests(provider_turn_id,status);
            INSERT INTO orchestration_v2_projection_threads VALUES('main',NULL,NULL),('hidden',NULL,'archived');
            INSERT INTO orchestration_v2_projection_provider_threads VALUES('agent','codex','active'),('old','claude','idle'),('hidden','codex','active'),('idle','codex','idle');
            INSERT INTO orchestration_v2_projection_provider_turns VALUES
              ('agent','superseded','main',1,'running','2026-01-02T00:00:00Z',NULL),
              ('agent','current','main',2,'running','2026-01-02T00:00:00Z',NULL),
              ('old','before-restart','main',1,'running','2025-01-02T00:00:00Z',NULL),
              ('hidden','archived','hidden',1,'running','2026-01-02T00:00:00Z',NULL),
              ('idle','stale','main',1,'running','2026-01-02T00:00:00Z',NULL);
            INSERT INTO orchestration_v2_projection_runtime_requests VALUES('current','pending');
        ''')
        with patch.object(Path, 'read_bytes', return_value=b't3code apps/server'):
            result = reader.snapshot(folder)
        assert result['available'] and result['tasks'] == [dict(id='agent',turn='current',provider='Codex',waiting=True)], result
        c.execute("UPDATE orchestration_v2_projection_runtime_requests SET status='resolved'")
        c.execute("UPDATE orchestration_v2_projection_provider_turns SET status='failed',completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE provider_turn_id='current'")
        c.commit()
        result = reader.v2_snapshot(c, '2026-01-01T00:00:00Z')
        assert not result['tasks'] and result['recent'] == [dict(id='agent',turn='current',state='error')], result
print('PASS V2 database selection, task state, waiting, restart filtering and outcomes')
