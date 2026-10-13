#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reminders', ROOT/'scripts/reminders.py')
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

with tempfile.TemporaryDirectory(prefix='modesty-reminders-') as state:
    environment = dict(os.environ, XDG_STATE_HOME=state, TZ='UTC')
    def command(value=None):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/reminders.py')]+(['--stdin'] if value else []),
                                input=json.dumps(value)+'\n' if value else None,
                                env=environment, capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)
        assert result.returncode == (0 if data['ok'] else 1) or data.get('status') in {'conflict','refused'}, data
        return data
    assert command()['items'] == []
    data = command(dict(kind='create', id='unicode', title='Water 🌱', date='2026-01-31', time='09:00',
                        repeat={'kind': 'monthly', 'anchorDay': 31}, zone='UTC', operationId='create-once'))
    assert data['receipt']['status'] == 'persisted'
    assert data['revision'] == 1 and data['items'][0]['revision'] == 1
    assert command(dict(kind='create', id='unicode', title='Water 🌱', date='2026-01-31', time='09:00', repeat={'kind':'monthly','anchorDay':31},zone='UTC',operationId='create-once'))['revision'] == 1
    assert command(dict(kind='create', title='Different', operationId='create-once'))['status'] == 'refused'
    assert command(dict(kind='update',id='unicode',title='Boolean revision',expectedRevision=True))['status'] == 'failed'
    assert command(dict(kind='complete',id='unicode',done='false'))['status'] == 'failed'
    path = Path(state)/'modesty/reminders.json'
    assert path.stat().st_mode & 0o777 == 0o600
    conflict = command(dict(kind='update', id='unicode', title='Overwritten', expectedRevision=999))
    assert conflict['status'] == 'conflict' and command()['items'][0]['title'] == 'Water 🌱'
    completed = command(dict(kind='complete', id='unicode', now=backend.local_timestamp('2026-01-31', '08:00', 'UTC')))
    assert completed['items'][0]['date'] == '2026-02-28'
    assert not completed['items'][0]['done'] and completed['items'][0]['repeat']['anchorDay'] == 31
    completed = command(dict(kind='complete', id='unicode', now=backend.local_timestamp('2026-02-28', '08:00', 'UTC')))
    assert completed['items'][0]['date'] == '2026-03-31'
    assert command(dict(kind='complete', id='unicode', occurrenceKey='2026-05-31T09:00'))['status'] == 'failed'
    resumed = command(dict(kind='check', now=backend.local_timestamp('2026-06-30', '10:00', 'UTC')))
    assert len(resumed['notices']) == 1 and resumed['notices'][0]['date'] == '2026-06-30'
    assert resumed['items'][0]['date'] == '2026-07-31'
    assert command(dict(kind='check', now=backend.local_timestamp('2026-06-30', '10:01', 'UTC')))['notices'] == []
    completed = command(dict(kind='complete', id='unicode', occurrenceKey='2026-06-30T09:00', now=backend.local_timestamp('2026-06-30', '10:02', 'UTC')))
    assert completed['items'][0]['date'] == '2026-07-31'
    completed = command(dict(kind='complete', id='unicode', occurrenceKey='2026-06-30T09:00', now=backend.local_timestamp('2026-06-30', '10:03', 'UTC')))
    assert completed['items'][0]['date'] == '2026-07-31'
    assert command(dict(kind='remove', id='unicode'))['items'] == []
    command(dict(kind='create', id='finite', title='Deadline', date='2026-07-10', time='12:00', lead=7, count=3))
    data = command(dict(kind='check', now=backend.local_timestamp('2026-07-11', '12:00', 'UTC')))
    assert data['items'][0]['delivered'] == ['2026-07-03', '2026-07-07', '2026-07-10']
    assert len(data['notices']) == 1
    assert command(dict(kind='check', now=backend.local_timestamp('2026-07-12', '12:00', 'UTC')))['notices'] == []
    assert command(dict(kind='complete', id='finite'))['items'][0]['done']
    assert not command(dict(kind='complete', id='finite', done=False))['items'][0]['done']
    original = command(dict(kind='create', id='guarded', title='Original', date='2099-05-01', time='09:00'))
    row = next(item for item in original['items'] if item['id'] == 'guarded')
    winner = command(dict(kind='update', id='guarded', title='Winner', expectedRevision=row['revision']))
    before = path.read_bytes()
    for kind in ('complete', 'remove'):
        stale = command(dict(kind=kind, id='guarded', expectedRevision=row['revision']))
        assert stale['status'] == 'conflict' and path.read_bytes() == before, stale
    revision = next(item for item in winner['items'] if item['id'] == 'guarded')['revision']
    fresh = command(dict(kind='complete', id='guarded', expectedRevision=revision))
    row = next(item for item in fresh['items'] if item['id'] == 'guarded')
    assert row['done'] and row['title'] == 'Winner' and row['revision'] == revision + 1
    assert not any(item['id'] == 'guarded' for item in command(dict(kind='remove', id='guarded', expectedRevision=row['revision']))['items'])
    invalid_revision = dict(command(), expectedRevision=True)
    assert command(invalid_revision)['status'] == 'failed'
    valid = path.read_bytes()
    corrupted = json.loads(valid)
    corrupted['receipts'][0]['revision'] = True
    path.write_text(json.dumps(corrupted))
    assert command(dict(kind='update', id='finite', title='Unsafe'))['status'] == 'failed'
    assert json.loads(path.read_text()) == corrupted
    path.write_bytes(valid)
    corrupted = json.loads(valid)
    corrupted['receipts'].append(dict(corrupted['receipts'][0]))
    path.write_text(json.dumps(corrupted))
    assert command()['status'] == 'failed'
    path.write_bytes(valid)
    path.write_text('{broken')
    failure = command(dict(kind='create', title='Lost', date='2026-07-10', time='12:00'))
    assert not failure['ok'] and path.read_text() == '{broken'

assert backend.local_timestamp('2026-03-08', '02:30', 'America/New_York') == backend.local_timestamp('2026-03-08', '03:30', 'America/New_York')
assert backend.local_timestamp('2026-11-01', '01:30', 'America/New_York') == 1793511000000
entry = backend.make_entry(dict(title='Daily', date='2026-03-07', time='09:00', repeat={'kind': 'daily'}, zone='America/New_York'))
next_day, at = backend.next_occurrence(entry, entry['at'])
assert next_day == '2026-03-08' and at-entry['at'] == 23*3600000
entry = backend.make_entry(dict(title='Weekdays', date='2026-07-03', time='09:00', repeat={'kind': 'weekly', 'weekdays': [1,2,3,4,5]}, zone='UTC'))
assert backend.next_occurrence(entry, entry['at'])[0] == '2026-07-06'
entry = backend.make_entry(dict(title='Fortnight', date='2026-07-01', time='09:00', repeat={'kind':'weekly','interval':2,'weekdays':[1,5]}, zone='UTC'))
assert entry['date'] == '2026-07-03'
assert backend.next_occurrence(entry, entry['at'])[0] == '2026-07-13'
entry = backend.make_entry(dict(title='Leap month', date='2028-01-31', time='09:00', repeat={'kind':'monthly','anchorDay':31}, zone='UTC'))
assert backend.next_occurrence(entry, entry['at'])[0] == '2028-02-29'
entry = backend.make_entry(dict(title='Fall back', date='2026-10-31', time='01:30', repeat={'kind':'daily'}, zone='America/New_York'))
fall_day, fall_at = backend.next_occurrence(entry, entry['at'])
assert fall_day == '2026-11-01' and fall_at == 1793511000000
entry['date'], entry['at'] = fall_day, fall_at
assert backend.next_occurrence(entry, fall_at)[1]-fall_at == 25*3600000
with tempfile.TemporaryDirectory(prefix='modesty-reminder-failure-') as state:
    with patch.object(backend, 'FOLDER', Path(state)), patch.object(backend, 'PATH', Path(state)/'reminders.json'):
        backend.run(dict(kind='create', id='before', title='Safe', date='2026-07-10', time='12:00'))
        before = backend.PATH.read_bytes()
        with patch.object(backend.os, 'replace', side_effect=OSError('simulated write failure')):
            try:
                backend.run(dict(kind='update', id='before', title='Unsafe'))
            except OSError:
                pass
            else:
                raise AssertionError('Write failure returned an acknowledgment')
        assert backend.PATH.read_bytes() == before
sys.path.insert(0, str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('tasks', ROOT/'scripts/luma-tasks.py')
tasks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tasks)
now = backend.datetime(2026, 1, 31, 10, tzinfo=backend.ZoneInfo('America/New_York'))
parsed = tasks.reminder('remind me to drink water every day at 9am', now=now)
assert parsed['repeat']['kind'] == 'daily' and parsed['date'] == '2026-02-01' and parsed['zone'] == 'America/New_York'
parsed = tasks.reminder('remind me every weekday at 9am to stretch', now=now)
assert parsed['repeat']['weekdays'] == [1,2,3,4,5] and parsed['date'] == '2026-02-02'
parsed = tasks.reminder('remind me to exercise every Monday and Friday at 9am', now=now)
assert parsed['repeat']['weekdays'] == [1,5]
parsed = tasks.reminder('remind me to pay rent every month on the 31st at 9am', now=now)
assert parsed['date'] == '2026-02-28' and parsed['repeat']['anchorDay'] == 31
parsed = tasks.reminder('remind me to review weekly on Mondays at 9am', now=now)
assert parsed['repeat']['weekdays'] == [1]
parsed = tasks.reminder('remind me to stretch every 2 days at 9am', now=now)
assert parsed['repeat']['interval'] == 2
missing_time = tasks.reminder('remind me to stretch every day', now=now)
assert missing_time['draft']['need'] == 'when' and missing_time['draft']['title'] == 'stretch'
assert tasks.reminder('at 9pm', pending=missing_time['draft'], now=now)['repeat']['kind'] == 'daily'
missing_title = tasks.reminder('remind me every day at 9am', now=now)
assert missing_title['draft']['need'] == 'title'
assert tasks.reminder('Drink water', pending=missing_title['draft'], now=now)['title'] == 'Drink water'
ambiguous = tasks.reminder('remind me to exercise every day at 9', now=now)
assert ambiguous['draft']['repeat']['kind'] == 'daily' and ambiguous['draft']['title'] == 'exercise'
parsed = tasks.reminder('9pm', pending=ambiguous['draft'], now=now)
assert parsed['time'] == '21:00' and parsed['title'] == 'exercise'
assert tasks.reminder('remind me to call on 03/04 at 10am', now=now)['draft']['need'] == 'when'
assert tasks.reminder('remind me to call on 2026-02-30 at 10am', now=now)['draft']['need'] == 'when'
parsed = tasks.reminder('remind me to call tomorrow at 9am in Asia/Kolkata', now=now)
assert parsed['zone'] == 'Asia/Kolkata' and parsed['dueAt'] == backend.local_timestamp(parsed['date'], '09:00', 'Asia/Kolkata')
gap_now = backend.datetime(2026,3,7,12,tzinfo=backend.ZoneInfo('America/New_York'))
parsed = tasks.reminder('remind me to exercise daily at 02:30', now=gap_now)
entry = backend.make_entry(dict(kind='create', **parsed))
assert entry['date'] == '2026-03-08' and entry['time'] == '02:30' and entry['at'] == parsed['dueAt']
print('PASS reminder persistence, revisions, retry receipts, recurrence, resume, completion, DST, parser, and write failures')
