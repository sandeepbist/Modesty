#!/usr/bin/env python3
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from luma.actions import ACTIONS,ACTION_SCHEMA,CATALOG,PREFERENCES,validated_action,protected_notes_path,local_note_action
from luma.protocol import clean_execution,clean_task_context
spec=importlib.util.spec_from_file_location('assistant',ROOT/'scripts/luma-assistant.py')
assistant=importlib.util.module_from_spec(spec);spec.loader.exec_module(assistant)
handlers=set(re.findall(r'case "([a-z_]+)"', (ROOT/'services/DesktopActions.qml').read_text()))
assert ACTIONS<=handlers, sorted(ACTIONS-handlers)
assert {item['properties']['name']['enum'][0] for item in ACTION_SCHEMA['items']['anyOf']}==ACTIONS
assert 'paused' in CATALOG['focus_pause']['fields']
assert set(re.findall(r'"([A-Za-z0-9]+)"',re.search(r'preferenceKeys: \[(.*?)\]',(ROOT/'services/DesktopActions.qml').read_text()).group(1)))==PREFERENCES.keys()
assert not {'lumaAccess','lumaSystem','lumaDesktop','lumaLocalFiles','lumaKnowledgeRoots','privacyRadar','profileImage'}&PREFERENCES.keys()
notes=[dict(id='n1',title='Agenda',revision=2,status='active',dirty=False)]
valid=validated_action(dict(name='note_append',args=dict(id='n1',expectedRevision=2,body='\n你好')),notes=notes)
assert valid['args']['body']=='\n你好'
for args in (dict(id='n1',expectedRevision=1,body='stale'),dict(id='n1',expectedRevision=True,body='bool')):
    try:validated_action(dict(name='note_append',args=args),notes=notes)
    except ValueError:pass
    else:raise AssertionError('Unsafe note revision accepted')
try:validated_action(dict(name='note_append',args=valid['args']),notes=[dict(notes[0],dirty=True)])
except ValueError:pass
else:raise AssertionError('Dirty note overwritten')
for args in (dict(key='lumaAccess',value='full'),dict(key='focusMinutes',value=25.5),dict(key='focusMinutes',value=25.0),dict(key='recordFps',value=True)):
    try:validated_action(dict(name='preference',args=args))
    except ValueError:pass
    else:raise AssertionError('Unsafe preference accepted')
assert validated_action(dict(name='preference',args=dict(key='uiScale',value=1.1)))['args']['value']==1.1
assert PREFERENCES['focusMinutes']['type']=='INTEGER'
for filename in ('notes.json','notes.backup.json','notes.lock','.notes-crash'):
    path=assistant.STATE/filename
    assert protected_notes_path(path)
    try:assistant.system_tools.checked_path(str(path))
    except ValueError:pass
    else:raise AssertionError('Authoritative Notes path exposed')
export=Path.home()/'Documents'/'Quick Notes'/'Agenda.md'
assert not protected_notes_path(export)
assert assistant.system_tools.checked_path(str(export))==export.resolve()
with tempfile.TemporaryDirectory(prefix='modesty-notes-mask-') as temporary:
    state=Path(temporary)/'modesty';state.mkdir()
    current=state/'.notes-created-after-start';current.write_text('private-note-body')
    with patch.object(assistant.system_tools,'NOTES_STATE',state):
        call=assistant.system_tools.validated(dict(name='run_command',purpose='Check Notes isolation',argv=['cat',str(current)],cwd=temporary))
        result=assistant.system_tools.command(call,approved=True)
    assert not result['ok'] and 'private-note-body' not in result['stdout']+result['stderr'], result
calls=[]
def ipc(method,*args):
    calls.append(method)
    if method=='snapshot':return dict(notes=notes,reminders=[],audioOutputs=[])
    if method=='execute':
        action=json.loads(args[0]);assert action['args']['id']=='n1' and action['operationId']
        return dict(ok=True,status='requested',ticket='t1',id='n1',revision=3)
    if method=='receipt':return dict(status='persisted',id='n1',revision=3)
    raise AssertionError(method)
with patch.object(assistant.system_tools,'ipc',side_effect=ipc):
    result=assistant.native_system_action('note_append',valid['args'],[],[],[])
assert result['ok'] and result['status']=='persisted' and result['id']=='n1' and calls==['snapshot','execute','receipt'], (result,calls)
with patch.object(assistant.system_tools,'ipc',return_value=dict(status='failed',error='disk full')):
    result=assistant.system_tools.wait_receipt(dict(ok=True,status='requested',ticket='t2'))
assert not result['ok'] and result['error']=='disk full'
with patch.object(assistant.system_tools,'ipc',return_value=dict(status='pending')):
    result=assistant.system_tools.wait_receipt(dict(ok=True,status='requested',ticket='t3'),timeout=.01)
assert result['status']=='requested' and 'pending' in result['note']
receipt=clean_execution([dict(tool=dict(name='desktop_action'),result=dict(ok=True,status='persisted',id='n1',revision=3,ticket='t1'))])[0]
assert receipt['result']['id']=='n1' and receipt['result']['revision']==3
pending=dict(kind='reminder',title='Water',need='time',repeat=dict(kind='daily',interval=1),zone='Asia/Kolkata')
import time
context=clean_task_context(dict(pendingTask=pending,taskExpires=time.time()*1000+60000,recentTasks=[dict(name='note_create',args={},noteId='n1',revision=3)]))
assert context['pendingTask']['repeat']['kind']=='daily' and context['pendingTask']['zone']=='Asia/Kolkata'
assert context['recentTasks'][0]['noteId']=='n1'
for name in ('notes_list','notes_read','reminders_list','reminders_read'):
    args=dict(name=name,purpose='Read requested local item')
    if name.endswith('_read'):args['id']='n1'
    assert assistant.system_tools.observational(assistant.system_tools.validated(args))
assert local_note_action('take a note: Buy milk',{})['args']['body']=='Buy milk'
assert local_note_action('append eggs to this note',dict(notes=notes,activeNoteId='n1'))['args']['expectedRevision']==2
assert local_note_action('create a note about gardening',{}) is None
reminders=[dict(id='r1',title='Water',revision=2)]
recent=[dict(name='reminder',args={},status='scheduled',reminderId='r1',at=time.time()*1000)]
for query,expected in (
    ('cancel the reminder',dict(name='reminder_remove',args=dict(id='r1',expectedRevision=2),label='Remove reminder · Water',status='pending',review=True)),
    ('set volume to 41',dict(name='volume',args=dict(level=41),label='Volume · 41%',status='pending',review=False)),
):
    with patch('sys.stdout',new=io.StringIO()) as output:
        assistant.converse(dict(query=query,useJev=False,localFiles=False,context=dict(reminders=reminders),taskContext=dict(recentTasks=recent)))
    answer=json.loads(output.getvalue().splitlines()[-1])
    assert answer['actions']==[expected], (query,answer['actions'])
    assert answer['localTask'] is True
    assert validated_action(dict(expected,review=False),reminders=reminders)==expected
print('PASS mandatory proposal review survives offline answer serialization; safe volume automation remains available')
print('PASS native catalogue coverage, scoped Notes storage, dirty/revision guards, refreshed IDs and acknowledged receipts')
