#!/usr/bin/env python3
import calendar
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FOLDER = Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'modesty'
PATH = FOLDER/'reminders.json'


def local_zone():
    for value in (os.environ.get('TZ', '').removeprefix(':'),
                  str(Path('/etc/localtime').resolve()).partition('/zoneinfo/')[2]):
        if value:
            try:
                ZoneInfo(value)
                return value
            except (ValueError, ZoneInfoNotFoundError):
                pass
    return 'UTC'


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Invalid date')
    return date.fromisoformat(value)


def repeat_value(value=None, anchor=None):
    value = value if value is not None else {'kind': 'none'}
    if not isinstance(value, dict) or value.get('kind') not in {'none', 'daily', 'weekly', 'monthly'}:
        raise ValueError('Invalid reminder recurrence')
    interval = value.get('interval', 1)
    if type(interval) is not int or not 1 <= interval <= 365:
        raise ValueError('Invalid recurrence interval')
    weekdays = value.get('weekdays', [anchor.isoweekday()] if anchor else [])
    if not isinstance(weekdays, list) or any(type(n) is not int or not 1 <= n <= 7 for n in weekdays):
        raise ValueError('Invalid recurrence weekdays')
    if value['kind'] == 'weekly' and not weekdays:
        raise ValueError('Choose at least one weekday')
    anchor_day = value.get('anchorDay', anchor.day if anchor else 1)
    if type(anchor_day) is not int or not 1 <= anchor_day <= 31:
        raise ValueError('Invalid monthly anchor')
    return dict(kind=value['kind'], interval=interval, weekdays=sorted(set(weekdays)), anchorDay=anchor_day)


def local_timestamp(day_value, clock, zone):
    """Use the first fold. A nonexistent time moves forward by the DST gap."""
    naive = datetime.combine(day(day_value), time.fromisoformat(clock))
    tz = ZoneInfo(zone)
    choices = [naive.replace(tzinfo=tz, fold=fold) for fold in (0, 1)]
    valid = [value for value in choices if value.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) == naive]
    if valid:
        return round(min(value.timestamp() for value in valid)*1000)
    forward = [value.astimezone(timezone.utc).astimezone(tz) for value in choices]
    return round(min(value.timestamp() for value in forward if value.replace(tzinfo=None) > naive)*1000)


def occurrence_key(entry, value=None):
    return (value or entry['date']) + 'T' + entry['time']


def recurring_days(entry, after):
    repeat = entry['repeat']
    anchor = day(entry['startsOn'])
    after = max(after, anchor)
    interval = repeat['interval']
    if repeat['kind'] == 'daily':
        distance = (after-anchor).days
        current = anchor + timedelta(days=((distance+interval-1)//interval)*interval)
        while True:
            yield current
            current += timedelta(days=interval)
    elif repeat['kind'] == 'weekly':
        week = anchor-timedelta(days=anchor.weekday())
        distance = max(0, (after-week).days//7)
        week += timedelta(weeks=(distance//interval)*interval)
        while True:
            for weekday in repeat['weekdays']:
                current = week+timedelta(days=weekday-1)
                if current >= after:
                    yield current
            week += timedelta(weeks=interval)
    elif repeat['kind'] == 'monthly':
        base = anchor.year*12+anchor.month-1
        distance = (after.year*12+after.month-1)-base
        month_index = base+(distance//interval)*interval
        while True:
            year, month = divmod(month_index, 12)
            month += 1
            current = date(year, month, min(repeat['anchorDay'], calendar.monthrange(year, month)[1]))
            if current >= after:
                yield current
            month_index += interval


def next_occurrence(entry, threshold):
    near = datetime.fromtimestamp(threshold/1000, ZoneInfo(entry['zone'])).date()
    for current in recurring_days(entry, near):
        at = local_timestamp(current.isoformat(), entry['time'], entry['zone'])
        if at > threshold:
            return current.isoformat(), at
    raise ValueError('No next reminder occurrence')


def latest_occurrence(entry, now):
    near = datetime.fromtimestamp(now/1000, ZoneInfo(entry['zone'])).date()
    span = entry['repeat']['interval']*(7 if entry['repeat']['kind'] == 'weekly' else 32 if entry['repeat']['kind'] == 'monthly' else 1)
    latest = None
    for current in recurring_days(entry, max(day(entry['date']), near-timedelta(days=span))):
        at = local_timestamp(current.isoformat(), entry['time'], entry['zone'])
        if at > now:
            return latest
        latest = current.isoformat()
    return latest


def finite_schedule(entry):
    count, lead = entry['count'], entry['lead']
    return [(day(entry['date'])+timedelta(days=-lead+(0 if count == 1 else math.floor(i*lead/(count-1)+.5)))).isoformat() for i in range(count)]


def validate(data):
    if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1 or not isinstance(data.get('items'), list) or len(data['items']) > 256:
        raise ValueError('Invalid reminder file')
    if type(data.get('revision', 0)) is not int or data.get('revision', 0) < 0:
        raise ValueError('Invalid reminder revision')
    seen = set()
    for entry in data['items']:
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not re.fullmatch(r'[a-z0-9-]{1,80}', entry['id']) or entry['id'] in seen:
            raise ValueError('Invalid reminder id')
        seen.add(entry['id'])
        anchor = day(entry.get('date'))
        if not isinstance(entry.get('title'), str) or not entry['title'].strip() or len(entry['title']) > 160:
            raise ValueError('Invalid reminder title')
        if not isinstance(entry.get('time'), str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', entry['time']):
            raise ValueError('Invalid reminder time')
        if type(entry.get('lead')) is not int or not 0 <= entry['lead'] <= 30 or type(entry.get('count')) is not int or not 1 <= entry['count'] <= entry['lead']+1:
            raise ValueError('Invalid reminder schedule')
        if type(entry.get('done')) is not bool or not isinstance(entry.get('delivered'), list) or len(entry['delivered']) > 31:
            raise ValueError('Invalid reminder state')
        if 'at' in entry and (type(entry['at']) not in (int, float) or not math.isfinite(entry['at']) or not 0 < entry['at'] < 253402300799000 or entry['lead'] != 0 or entry['count'] != 1):
            raise ValueError('Invalid exact reminder time')
        for value in entry['delivered']:
            day(value)
        entry['repeat'] = repeat_value(entry.get('repeat'), anchor)
        entry['zone'] = entry.get('zone') or local_zone()
        if not isinstance(entry['zone'], str):
            raise ValueError('Invalid timezone')
        ZoneInfo(entry['zone'])
        entry['revision'] = entry.get('revision', 1)
        if type(entry['revision']) is not int or entry['revision'] < 1:
            raise ValueError('Invalid reminder revision')
        if entry['repeat']['kind'] != 'none':
            if entry['lead'] or entry['count'] != 1:
                raise ValueError('Recurring reminders cannot have advance notices')
            entry['startsOn'] = entry.get('startsOn', entry['date'])
            day(entry['startsOn'])
            if entry['date'] < entry['startsOn'] or next(recurring_days(entry, anchor)) != anchor:
                raise ValueError('Invalid next reminder occurrence')
            entry['at'] = local_timestamp(entry['date'], entry['time'], entry['zone'])
        for field in ('lastDeliveryKey', 'lastCompletionKey'):
            if field in entry:
                key = entry[field]
                if not isinstance(key, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T' + entry['time'], key):
                    raise ValueError('Invalid occurrence key')
                occurred = day(key[:10])
                if entry['repeat']['kind'] != 'none' and (key[:10] < entry['startsOn'] or next(recurring_days(entry, occurred)) != occurred):
                    raise ValueError('Invalid recurrence occurrence key')
    data.setdefault('revision', 0)
    data.setdefault('receipts', [])
    if not isinstance(data['receipts'], list) or len(data['receipts']) > 128:
        raise ValueError('Invalid reminder receipts')
    operations = set()
    for receipt in data['receipts']:
        if not isinstance(receipt, dict) or receipt.get('status') != 'persisted' or receipt.get('ok') is not True:
            raise ValueError('Invalid reminder receipt')
        if not isinstance(receipt.get('operationId'), str) or not 1 <= len(receipt['operationId']) <= 160:
            raise ValueError('Invalid receipt operation id')
        if receipt['operationId'] in operations:
            raise ValueError('Duplicate receipt operation id')
        operations.add(receipt['operationId'])
        if not isinstance(receipt.get('id'), str) or not re.fullmatch(r'[a-z0-9-]{1,80}', receipt['id']):
            raise ValueError('Invalid receipt reminder id')
        if type(receipt.get('revision')) is not int or receipt['revision'] < 1 or receipt.get('error') != '':
            raise ValueError('Invalid receipt revision')
        if 'fingerprint' in receipt and (not isinstance(receipt['fingerprint'], str) or not re.fullmatch(r'[a-f0-9]{64}', receipt['fingerprint'])):
            raise ValueError('Invalid receipt fingerprint')
    return data


def load():
    return validate(json.loads(PATH.read_text())) if PATH.exists() else {'version': 1, 'revision': 0, 'items': [], 'receipts': []}


def atomic_write(data):
    FOLDER.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = None
    backup = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=FOLDER, delete=False, prefix='.reminders-') as stream:
            name = stream.name
            os.fchmod(stream.fileno(), 0o600)
            json.dump(data, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        if PATH.exists():
            previous = load()
            with tempfile.NamedTemporaryFile(mode='w', dir=FOLDER, delete=False, prefix='.reminders-backup-') as stream:
                backup = stream.name
                os.fchmod(stream.fileno(), 0o600)
                json.dump(previous, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(backup, PATH.with_suffix('.json.bak'))
        os.replace(name, PATH)
        name = None
        descriptor = os.open(FOLDER, os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        for temporary in (name, backup):
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)


def make_entry(command, old=None):
    old = old or {}
    entry = deepcopy(old)
    entry.update({name: command[name] for name in ('title', 'date', 'time', 'lead', 'count', 'repeat', 'zone') if name in command})
    entry.setdefault('zone', local_zone())
    ZoneInfo(entry['zone'])
    due = command.get('dueAt')
    if due is not None:
        if type(due) not in (int, float) or not math.isfinite(due) or not 0 < due < 253402300799000:
            raise ValueError('Invalid exact reminder time')
        moment = datetime.fromtimestamp(due/1000, ZoneInfo(entry['zone']))
        entry.update(date=moment.date().isoformat(), time=moment.strftime('%H:%M'), lead=0, count=1, at=due)
        requested_repeat = command.get('repeat', old.get('repeat', {'kind': 'none'}))
        if not isinstance(requested_repeat, dict):
            raise ValueError('Invalid reminder recurrence')
        if requested_repeat.get('kind', 'none') != 'none':
            entry['date'] = command.get('date', entry['date'])
            entry['time'] = command.get('time', entry['time'])
    entry.setdefault('lead', 0)
    entry.setdefault('count', 1)
    entry['id'] = command.get('id') or old.get('id') or uuid.uuid4().hex
    if not isinstance(entry.get('title'), str):
        raise ValueError('Invalid reminder title')
    entry['title'] = entry['title'].strip()
    entry['repeat'] = repeat_value(entry.get('repeat'), day(entry.get('date')))
    entry['revision'] = old.get('revision', 0)+1
    entry.setdefault('done', False)
    entry.setdefault('delivered', [])
    changed = any(entry.get(name) != old.get(name) for name in ('date', 'time', 'lead', 'count', 'repeat', 'zone', 'at'))
    if changed:
        entry['done'] = False
        entry['delivered'] = []
        entry.pop('lastDeliveryKey', None)
        entry.pop('lastCompletionKey', None)
        entry.pop('startsOn', None)
        if due is None:
            entry.pop('at', None)
    if entry['repeat']['kind'] != 'none':
        entry['lead'], entry['count'] = 0, 1
        entry.setdefault('startsOn', entry['date'])
        entry['at'] = local_timestamp(entry['date'], entry['time'], entry['zone'])
        first = next(recurring_days(entry, day(entry['date'])))
        entry['date'] = first.isoformat()
        entry['at'] = local_timestamp(entry['date'], entry['time'], entry['zone'])
    validate({'version': 1, 'items': [entry]})
    return entry


def apply(data, command, now):
    kind = command.get('kind')
    identifier = command.get('id', '')
    old = next((entry for entry in data['items'] if entry['id'] == identifier), None)
    if 'expectedRevision' in command and (type(command['expectedRevision']) is not int or command['expectedRevision'] < 1):
        raise ValueError('Invalid expected reminder revision')
    if kind in {'update', 'complete', 'remove'}:
        if old is None:
            raise ValueError('Reminder no longer exists')
        if 'expectedRevision' in command and command['expectedRevision'] != old['revision']:
            return {'ok': False, 'status': 'conflict', 'id': identifier, 'revision': old['revision'], 'error': 'Reminder changed. Read it again before updating.'}, []
    notices = []
    if kind in {'create', 'update'}:
        if kind == 'create' and old is not None:
            raise ValueError('Reminder id already exists')
        if kind == 'create' and len(data['items']) >= 256:
            raise ValueError('Remove an old reminder before adding another')
        entry = make_entry(command, old)
        data['items'] = [value for value in data['items'] if value['id'] != entry['id']] + [entry]
        identifier = entry['id']
        revision = entry['revision']
    elif kind == 'remove':
        data['items'] = [value for value in data['items'] if value['id'] != identifier]
        revision = old['revision']+1
    elif kind == 'complete':
        if type(command.get('done', True)) is not bool:
            raise ValueError('Invalid completion state')
        if old['repeat']['kind'] == 'none':
            old['done'] = command.get('done', True)
        elif command.get('done', True):
            key = command.get('occurrenceKey') or (old.get('lastDeliveryKey') if old.get('lastDeliveryKey') != old.get('lastCompletionKey') else None) or occurrence_key(old)
            if key not in {occurrence_key(old), old.get('lastDeliveryKey'), old.get('lastCompletionKey')}:
                raise ValueError('Reminder occurrence changed. Read it again before completing.')
            if key != old.get('lastCompletionKey'):
                if key == occurrence_key(old):
                    old['date'], old['at'] = next_occurrence(old, max(old['at'], now))
                old['lastCompletionKey'] = key
            old['done'] = False
        old['revision'] += 1
        revision = old['revision']
    elif kind == 'check':
        for entry in data['items']:
            if entry['done']:
                continue
            if entry['repeat']['kind'] != 'none':
                if entry['at'] > now:
                    continue
                last = latest_occurrence(entry, now)
                if last is None:
                    continue
                key = occurrence_key(entry, last)
                if entry.get('lastDeliveryKey') != key and entry.get('lastCompletionKey') != key:
                    notices.append(dict(entry, date=last, occurrenceKey=key))
                    entry['lastDeliveryKey'] = key
                entry['date'], entry['at'] = next_occurrence(entry, now)
            else:
                due = [value for value in finite_schedule(entry) if (entry.get('at') if entry.get('at') and value == entry['date'] else local_timestamp(value, entry['time'], entry['zone'])) <= now and value not in entry['delivered']]
                if not due:
                    continue
                entry['delivered'] += due
                notices.append(dict(entry, occurrenceKey=occurrence_key(entry, due[-1])))
            entry['revision'] += 1
        revision = data['revision']
    else:
        raise ValueError('Invalid reminder command')
    return {'ok': True, 'status': 'persisted', 'id': identifier, 'revision': revision, 'error': ''}, notices


def run(command=None):
    if command is not None and not isinstance(command, dict):
        raise ValueError('Invalid reminder command')
    if command is not None and 'now' in command and (type(command['now']) not in (int, float) or not math.isfinite(command['now']) or not 0 < command['now'] < 253402300799000):
        raise ValueError('Invalid reminder clock')
    FOLDER.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (FOLDER/'reminders.lock').open('a') as lock:
        os.chmod(lock.name, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = load()
        if command is None or command.get('kind') == 'load':
            return {'ok': True, **data, 'zone': local_zone()}
        if command.get('version') == 1:
            if 'expectedRevision' in command and (type(command['expectedRevision']) is not int or command['expectedRevision'] < 0):
                raise ValueError('Invalid expected store revision')
            if 'expectedRevision' in command and command['expectedRevision'] != data['revision']:
                return {'ok': False, 'status': 'conflict', 'error': 'Reminder store changed'}
            replacement = validate(command)
            replacement['revision'] = data['revision']+1
            atomic_write(replacement)
            return {'ok': True, **replacement, 'status': 'persisted'}
        operation = command.get('operationId', '')
        if not isinstance(operation, str) or len(operation) > 160:
            raise ValueError('Invalid operation id')
        payload = {key: value for key, value in command.items() if key != 'operationId' and not (command.get('generatedId') is True and key == 'id')}
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        previous = next((receipt for receipt in data['receipts'] if receipt.get('operationId') == operation), None) if operation else None
        if previous:
            if previous.get('fingerprint') != fingerprint:
                return {'ok': False, 'status': 'refused', 'error': 'Operation id already used for a different reminder command'}
            return {'ok': True, **data, 'receipt': previous, 'notices': [], 'zone': local_zone()}
        before = deepcopy(data)
        receipt, notices = apply(data, command, command.get('now', datetime.now().timestamp()*1000))
        if not receipt['ok']:
            return {**receipt, **data, 'receipt': receipt}
        if data != before or operation:
            data['revision'] += 1
            if operation:
                receipt['operationId'] = operation
                receipt['fingerprint'] = fingerprint
                data['receipts'] = (data['receipts']+[receipt])[-128:]
            atomic_write(validate(data))
        return {'ok': True, **data, 'receipt': receipt, 'notices': notices, 'zone': local_zone()}


if __name__ == '__main__':
    try:
        command = json.loads(sys.stdin.readline()) if len(sys.argv) > 1 and sys.argv[1] == '--stdin' else json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
        print(json.dumps(run(command), ensure_ascii=False))
    except (ValueError, TypeError, OSError, OverflowError, ZoneInfoNotFoundError) as error:
        print(json.dumps({'ok': False, 'status': 'failed', 'error': str(error)}))
        sys.exit(1)
