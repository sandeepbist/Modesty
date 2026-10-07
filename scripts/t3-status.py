#!/usr/bin/env python3
"""Read only T3's current task metadata; never read prompts or credentials."""
import json
import os
from pathlib import Path
import sqlite3


def snapshot(directory=None):
    directory = Path(directory) if directory is not None else Path.home() / '.t3/userdata'
    try:
        runtime = json.loads((directory / 'server-runtime.json').read_text())
        pid = int(runtime['pid'])
        process = Path('/proc') / str(pid)
        if process.stat().st_uid != os.getuid():
            return dict(available=False, tasks=[])
        command = (process / 'cmdline').read_bytes()
        if b't3code' not in command or b'apps/server' not in command:
            return dict(available=False, tasks=[])
        database = directory / 'statev2.sqlite'
        if not database.exists():
            database = directory / 'state.sqlite'
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=.15) as connection:
            connection.execute('PRAGMA query_only=ON')
            if connection.execute("SELECT 1 FROM sqlite_master WHERE name='orchestration_v2_projection_provider_turns'").fetchone():
                return v2_snapshot(connection, runtime.get('startedAt', ''))
            rows = connection.execute('''
                SELECT s.thread_id, s.provider_name,
                       t.pending_approval_count, t.pending_user_input_count, s.active_turn_id
                FROM projection_thread_sessions s
                JOIN projection_threads t ON t.thread_id=s.thread_id
                JOIN projection_turns turn ON turn.thread_id=s.thread_id AND turn.turn_id=s.active_turn_id
                JOIN provider_session_runtime provider ON provider.thread_id=s.thread_id
                WHERE s.active_turn_id IS NOT NULL
                  AND (s.status='running' AND turn.state='running' AND provider.status='running'
                       OR t.pending_approval_count > 0 OR t.pending_user_input_count > 0)
                  AND t.deleted_at IS NULL AND t.archived_at IS NULL
                  AND s.updated_at >= ?
                ORDER BY turn.started_at, s.thread_id
            ''', (runtime.get('startedAt', ''),)).fetchall()
            recent = connection.execute("""
                SELECT turn.thread_id, turn.turn_id, turn.state
                FROM projection_turns turn JOIN projection_threads t ON t.thread_id=turn.thread_id
                WHERE turn.state IN ('completed','error','interrupted')
                  AND turn.completed_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes')
                  AND t.deleted_at IS NULL AND t.archived_at IS NULL
                ORDER BY turn.completed_at DESC LIMIT 64
            """).fetchall()
        # T3 can resume the same turn after a steering message while retaining
        # its previous completed_at. Current session/turn/runtime states win.
        tasks = []
        for thread, provider, approval, question, turn in rows:
            label = LABELS.get(provider, str(provider or 'Agent').replace('-', ' ').title())[:24]
            tasks.append(dict(id=thread, turn=turn, provider=label, waiting=bool(approval or question)))
        return dict(available=True, tasks=tasks, recent=[dict(id=t, turn=r, state=s) for t,r,s in recent])
    except (OSError, ValueError, KeyError, sqlite3.Error):
        return dict(available=False, tasks=[])


LABELS = {'codex': 'Codex', 'claude': 'Claude', 'claude-code': 'Claude',
          'claudeCode': 'Claude', 'gemini': 'Gemini', 'opencode': 'OpenCode',
          'openrouter': 'OpenRouter', 'cursor': 'Cursor'}


def v2_snapshot(connection, started):
    # Query only task metadata. Prompt, message and credential columns stay unread.
    rows = connection.execute('''
        SELECT p.provider_thread_id, p.provider, turn.provider_turn_id,
               EXISTS(SELECT 1 FROM orchestration_v2_projection_runtime_requests r
                      WHERE r.provider_turn_id=turn.provider_turn_id
                        AND r.status NOT IN ('resolved','cancelled','failed')) AS waiting
        FROM orchestration_v2_projection_provider_turns turn
        JOIN orchestration_v2_projection_provider_threads p
          ON p.provider_thread_id=turn.provider_thread_id
        JOIN orchestration_v2_projection_threads t ON t.thread_id=turn.thread_id
        WHERE t.deleted_at IS NULL AND t.archived_at IS NULL
          AND turn.started_at >= ?
          AND turn.ordinal=(SELECT MAX(x.ordinal)
                            FROM orchestration_v2_projection_provider_turns x
                            WHERE x.provider_thread_id=turn.provider_thread_id)
          AND (turn.status='running' AND p.status='active' OR waiting)
        ORDER BY turn.started_at, p.provider_thread_id
    ''', (started,)).fetchall()
    recent = connection.execute('''
        SELECT turn.provider_thread_id, turn.provider_turn_id, turn.status
        FROM orchestration_v2_projection_provider_turns turn
        JOIN orchestration_v2_projection_threads t ON t.thread_id=turn.thread_id
        WHERE turn.status IN ('completed','failed','interrupted','cancelled')
          AND turn.completed_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes')
          AND t.deleted_at IS NULL AND t.archived_at IS NULL
        ORDER BY turn.completed_at DESC LIMIT 64
    ''').fetchall()
    return dict(available=True, tasks=[dict(id=thread, turn=turn,
        provider=LABELS.get(provider, str(provider or 'Agent').replace('-', ' ').title())[:24],
        waiting=bool(waiting)) for thread, provider, turn, waiting in rows],
        recent=[dict(id=thread, turn=turn, state={'failed':'error','cancelled':'interrupted'}.get(state,state))
                for thread, turn, state in recent])


if __name__ == '__main__':
    print(json.dumps(snapshot()))
