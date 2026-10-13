#!/usr/bin/env python3
import importlib.util
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('assistant', ROOT / 'scripts/luma-assistant.py')
assistant = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assistant)

with tempfile.TemporaryDirectory(prefix='modesty-luma-native-') as temporary:
    workspace = Path(temporary)
    services = workspace / 'services'
    services.mkdir()
    (workspace / 'scripts').symlink_to(ROOT / 'scripts', target_is_directory=True)
    theme = workspace / 'theme'
    theme.mkdir()
    (theme / 'Theme.qml').write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton {property string mode:"dark";readonly property bool light:mode==="light";property string paletteName:"Blue";property var palettes:({Blue:{}});property string syncError:"";function setMode(value):void{mode=value;}function setPalette(value):void{paletteName=value;}}
''')
    (theme / 'qmldir').write_text('singleton Theme 1.0 Theme.qml\n')
    stubs = {
        'Session': 'property bool locked:false;function isLocked():bool{return locked;}function lock(value):void{locked=true;}function requestSleep(mode):void{locked=true;}',
        'Audio': '''property QtObject sink:QtObject {property int id:1;property string description:"Fixture speaker";property string name:"speaker";property QtObject audio:QtObject {property bool muted:true;property real volume:.5}}
property QtObject source:QtObject {property int id:3;property string description:"Fixture microphone";property string name:"microphone";property QtObject audio:QtObject {property bool muted:false;property real volume:.5}}
property QtObject secondary:QtObject {property int id:2;property string description:"Second speaker";property string name:"second";property QtObject audio:QtObject {property bool muted:false;property real volume:.3}}
property var outputs:[sink,secondary];property var inputs:[source];readonly property real volume:sink.audio.volume;readonly property bool muted:sink.audio.muted
function setVolume(value):void{sink.audio.volume=value;}function setNodeVolume(node,value):void{node.audio.volume=value;}function setDefault(node,output):void{if(output)sink=node;else source=node;}''',
        'SystemInfo': 'property real brightness:.5;property bool brightnessAvailable:false;property bool brightnessDirty:false;property bool brightnessInFlight:false;property int brightnessSequence:0;property int brightnessAcknowledgedSequence:0;property string error:"";property bool busy:false;property string wallpaper:"";property var wallpapers:[];function action(name,value):void{throw new Error("Unexpected system mutation");}function applyWallpaper(path):void{wallpaper=path;}',
        'Wireless': 'property bool available:false;property bool hardwareEnabled:false;property bool enabled:false;property string connectedName:"";property bool busy:false;property string error:"";property var networks:[];property var device:null;',
        'Radio': 'property bool available:false;property bool enabled:false;property bool blocked:false;property bool busy:false;property string error:"";property var devices:[];property var adapter:null;',
        'Media': 'property var players:[];property var active:null;property string title:"";property string artist:"";property bool playing:false;property bool hasSession:false;function play(player):bool{return false;}function pause(player):bool{return false;}',
        'Recorder': 'property string phase:"idle";property bool active:false;property bool recording:false;property var status:({});function start(region,sound):void{phase="recording";active=true;recording=true;}function pause():void{phase=phase==="paused"?"recording":"paused";}function stop():void{phase="saved";active=false;recording=false;}',
        'Notifications': 'property var list:[];property bool dnd:false;function close(notification):void{list=list.filter(n=>n!==notification);}function clearAll():void{list=[];}function remind(id,title,body,open,complete):void{}',
        'Display': 'property var monitors:[];property var pending:null;property bool busy:false;property bool nightLight:false;property bool nightDirty:false;property bool nightInFlight:false;property bool nightAcknowledged:false;property string error:"";function setNightLight(value):void{nightLight=value;nightAcknowledged=true;}',
        'FocusTimer': 'property bool loaded:true;property string phase:"idle";property int duration:0;property int remaining:0;function start(minutes,rest):void{duration=minutes*60;remaining=duration;phase="running";}function pause():void{phase=phase==="paused"?"running":"paused";}function cancel():void{phase="idle";}',
        'KeepAwake': 'property bool active:false;property real until:0;property string error:"";function setActive(value):void{active=value;until=0;}function setFor(seconds):bool{active=true;until=Date.now()+seconds*1000;return true;}',
        'Updates': 'property bool busy:false;property var state:({phase:"idle"});function run(action):void{state={phase:action==="check"?"ready":action==="download"?"staged":"idle"};}',
        'Apps': 'property var apps:[];property bool launching:false;property string error:"";signal closed(string appId,bool succeeded,string status)',
        'IslandDrop': 'function perform(paths,operation,args):bool{return false;}',
        'IslandState': 'property string menu:"";readonly property bool menuOpen:!!menu;property bool settingsOpen:false;function openMenu(name):void{menu=name;}function closeMenu():void{menu="";}',
        'CanvasState': 'property bool opened:false;function close():void{opened=false;}',
        'AgentWork': 'property var tasks:[]',
        'Context': 'function show(kind,text,icon,timeout):void{}',
        'Time': 'property date date:new Date()',
    }
    production = ['Preferences', 'Notes', 'Reminders', 'DesktopActions', 'Luma']
    for name in production:
        (services / (name + '.qml')).write_text((ROOT / 'services' / (name + '.qml')).read_text())
    (services / 'Calendar.js').write_text((ROOT / 'services/Calendar.js').read_text())
    for name, body in stubs.items():
        (services / (name + '.qml')).write_text('pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {' + body + '}\n')
    (services / 'qmldir').write_text('\n'.join('singleton ' + name + ' 1.0 ' + name + '.qml' for name in [*production, *stubs]) + '\n')
    (workspace / 'shell.qml').write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import "services" as Audit
ShellRoot {
    property bool loaded:Audit.Luma.loaded
    property int fixtures:0
    IpcHandler {target:"island";function health():string{return JSON.stringify({locked:Audit.Session.locked});}}
    IpcHandler {
        target:"audit"
        function state():string{return JSON.stringify({notes:Audit.Notes.loaded,reminders:Audit.Reminders.loaded,luma:Audit.Luma.loaded});}
        function edit(id:string,body:string):bool{if(!Audit.Notes.select(id))return false;Audit.Notes.edit({title:Audit.Notes.draft.title,body},body.length,0);return true;}
        function lock(value:bool):void{Audit.Session.locked=value;}
        function disappear():void{Audit.Audio.outputs=[Audit.Audio.sink];}
        function propose(action:string):void{Audit.Luma.proposalBatch="fixture-"+(++fixtures);Audit.Luma.proposals=[Object.assign(JSON.parse(action),{status:"pending",label:"Native fixture"})];Audit.Luma.apply(0);}
        function canUndo():bool{return Audit.Luma.canUndo(0);}
        function undo():string{Audit.Luma.undoAction(0);return JSON.stringify(Audit.Luma.proposals[0]);}
        function proposal():string{return JSON.stringify({actions:Audit.Luma.proposals,execution:Audit.Luma.receipts(Audit.Luma.execution)});}
    }
}
''')
    environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software',
                       MODESTY_PREVIEW='0', QS_NO_RELOAD_POPUP='1', XDG_STATE_HOME=str(workspace / 'state'),
                       XDG_CONFIG_HOME=str(workspace / 'config'), XDG_CACHE_HOME=str(workspace / 'cache'))
    with (workspace / 'log').open('w+') as log:
        process = subprocess.Popen(['qs', '--no-color', '-p', str(workspace)], env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)

        def call(target, method, *args, raw=False):
            result = subprocess.run(['qs', 'ipc', '--pid', str(process.pid), 'call', target, method, *map(str, args)], capture_output=True, text=True, timeout=4)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            return result.stdout.strip() if raw else json.loads(result.stdout)

        def wait(predicate, label, timeout=8):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    log.seek(0)
                    raise AssertionError(log.read())
                try:
                    value = predicate()
                    if value:
                        return value
                except AssertionError:
                    pass
                time.sleep(.03)
            log.seek(0)
            raise AssertionError(label + '\n' + log.read()[-4000:])

        def native(name, args):
            return assistant.native_system_action(name, args, [], [], [])

        def mutation(name, args, operation):
            return call('luma', 'execute', json.dumps(dict(name=name, args=args, operationId=operation), ensure_ascii=False))

        try:
            wait(lambda: all(call('audit', 'state').values()), 'Native services load')
            with patch.object(assistant.system_tools, 'ROOT', workspace), patch.object(assistant.system_tools, 'service_ipc', side_effect=lambda target, method, *args: call(target, method, *args)):
                created = native('note_create', dict(title='Agenda', body='पहला 📝\nFirst body'))
                assert created['ok'] and created['status'] == 'persisted' and created['revision'] == 1, created
                identifier = created['id']
                read = assistant.system_tools.execute(dict(name='notes_read', id=identifier, purpose='Read captured note'), native)
                assert read['note']['body'] == 'पहला 📝\nFirst body' and read['note']['revision'] == 1
                metadata = call('luma', 'snapshot')['notes']
                assert metadata[0]['id'] == identifier and 'body' not in metadata[0] and 'preview' not in metadata[0]
                appended = native('note_append', dict(id=identifier, expectedRevision=1, body='\nAppended once'))
                assert appended['status'] == 'persisted' and appended['revision'] == 2
                for name, extra, status in [('note_pin', dict(pinned=True), 'active'), ('note_update', dict(title='Renamed'), 'active'), ('note_archive', {}, 'archived'), ('note_restore', {}, 'active')]:
                    revision = call('notes', 'read', identifier)['note']['revision']
                    result = native(name, dict(id=identifier, expectedRevision=revision, **extra))
                    assert result['status'] == 'persisted' and result['revision'] == revision + 1
                    assert call('notes', 'read', identifier)['note']['status'] == status
                stale = mutation('note_append', dict(id=identifier, expectedRevision=1, body='Unsafe'), 'stale')
                assert not stale['ok'] and stale['status'] == 'conflict', stale
                revision = call('notes', 'read', identifier)['note']['revision']
                command = dict(id=identifier, expectedRevision=revision, body='\nStable retry')
                first = assistant.system_tools.wait_receipt(mutation('note_append', command, 'same-append'))
                second = assistant.system_tools.wait_receipt(mutation('note_append', command, 'same-append'))
                assert first['status'] == second['status'] == 'persisted' and first['revision'] == second['revision'] == revision + 1
                assert call('notes', 'read', identifier)['note']['body'].count('Stable retry') == 1
                assert call('audit', 'edit', identifier, 'Unsaved typing')
                dirty = mutation('note_append', dict(id=identifier, expectedRevision=first['revision'], body='Overwrite'), 'dirty')
                assert not dirty['ok'] and dirty['status'] == 'refused', dirty
                call('notes', 'flush', 'fixture')
                wait(lambda: not call('notes', 'status')['dirty'] and not call('notes', 'status')['saving'], 'Typing persists')
                revision = call('notes', 'read', identifier)['note']['revision']
                call('audit', 'propose', json.dumps(dict(name='note_append', args=dict(id=identifier, expectedRevision=revision, body='\nApplied through Luma'))), raw=True)
                proposal = wait(lambda: (value if value['actions'][0]['status'] == 'persisted' else None) if (value := call('audit', 'proposal')) else None, 'Luma proposal acknowledges save')
                assert proposal['execution'][-1]['result']['id'] == identifier and proposal['execution'][-1]['result']['revision'] == revision + 1
                day = datetime.now(ZoneInfo('Asia/Kolkata')).date() + timedelta(days=2)
                repeated = dict(title='Morning water', date=day.isoformat(), time='09:00', repeat=dict(kind='daily', interval=1), zone='Asia/Kolkata')
                reminder = native('reminder', repeated)
                assert reminder['status'] == 'persisted' and reminder['revision'] == 1, reminder
                reminder_id = reminder['id']
                row = call('reminders', 'read', reminder_id)['reminder']
                assert row['repeat']['kind'] == 'daily' and row['zone'] == 'Asia/Kolkata'
                updated = native('reminder_update', dict(id=reminder_id, title='Drink water', dueAt=row['at'], expectedRevision=row['revision']))
                assert updated['status'] == 'persisted' and updated['revision'] == 2, updated
                completed = native('reminder_complete', dict(id=reminder_id, expectedRevision=2))
                assert completed['status'] == 'persisted' and completed['revision'] == 3
                row = call('reminders', 'read', reminder_id)['reminder']
                assert row['date'] == (day + timedelta(days=1)).isoformat() and not row['done'], row
                removed = native('reminder_remove', dict(id=reminder_id, expectedRevision=3))
                assert removed['status'] == 'persisted' and not call('reminders', 'read', reminder_id)['ok']
                def propose_reminder(title):
                    call('audit', 'propose', json.dumps(dict(name='reminder', args=dict(repeated, title=title))), raw=True)
                    proposal = wait(lambda: (value if value['actions'][0]['status'] == 'persisted' else None) if (value := call('audit', 'proposal')) else None, 'Reminder creation acknowledged')
                    action = proposal['actions'][0]
                    assert action['revision'] == 1 and call('audit', 'canUndo'), action
                    return action

                action = propose_reminder('Edited reminder')
                due_at = call('reminders', 'read', action['reminderId'])['reminder']['at']
                changed = native('reminder_update', dict(id=action['reminderId'], title='Keep edited reminder', dueAt=due_at, expectedRevision=action['revision']))
                assert changed['status'] == 'persisted' and not call('audit', 'canUndo'), changed
                refused_undo = call('audit', 'undo')
                assert refused_undo['status'] == 'persisted' and call('reminders', 'read', action['reminderId'])['reminder']['title'] == 'Keep edited reminder', refused_undo

                action = propose_reminder('Concurrent reminder')
                external = subprocess.run([sys.executable, str(ROOT / 'scripts/reminders.py'), '--stdin'],
                                          input=json.dumps(dict(kind='update', id=action['reminderId'], title='Concurrent winner', expectedRevision=action['revision'])) + '\n',
                                          env=environment, capture_output=True, text=True, timeout=5)
                assert external.returncode == 0, external.stdout + external.stderr
                assert call('audit', 'canUndo'), 'Service snapshot unexpectedly reloaded'
                pending_undo = call('audit', 'undo')
                assert pending_undo['status'] == 'requested' and pending_undo['name'] == 'reminder_remove', pending_undo
                conflict = wait(lambda: (value if value['actions'][0]['status'] == 'conflict' else None) if (value := call('audit', 'proposal')) else None, 'Concurrent undo conflict acknowledged')
                assert conflict['execution'][-1]['tool']['action_name'] == 'reminder_remove', conflict
                assert call('reminders', 'read', action['reminderId'])['reminder']['title'] == 'Concurrent winner'

                action = propose_reminder('Failed undo')
                reminder_path = workspace / 'state/modesty/reminders.json'
                before = reminder_path.read_bytes()
                backup = reminder_path.with_suffix('.json.bak')
                backup.unlink()
                backup.mkdir()
                pending_undo = call('audit', 'undo')
                assert pending_undo['status'] == 'requested', pending_undo
                failed = wait(lambda: (value if value['actions'][0]['status'] == 'failed' else None) if (value := call('audit', 'proposal')) else None, 'Failed undo acknowledged')
                assert failed['execution'][-1]['tool']['action_name'] == 'reminder_remove' and not failed['execution'][-1]['result']['ok'], failed
                assert call('reminders', 'read', action['reminderId'])['ok'] and reminder_path.read_bytes() == before
                backup.rmdir()

                action = propose_reminder('Successful undo')
                pending_undo = call('audit', 'undo')
                assert pending_undo['status'] == 'requested', pending_undo
                persisted_undo = wait(lambda: (value if value['actions'][0]['status'] == 'persisted' else None) if (value := call('audit', 'proposal')) else None, 'Successful undo acknowledged')
                assert persisted_undo['execution'][-1]['tool']['action_name'] == 'reminder_remove' and persisted_undo['execution'][-1]['result']['ok'], persisted_undo
                assert not call('audit', 'canUndo') and not call('reminders', 'read', action['reminderId'])['ok']
                assert not any(item['id'] == action['reminderId'] for item in json.loads(reminder_path.read_text())['items'])
                print('PASS reminder undo respects creation revision, awaits durable receipts, and preserves conflict and write-failure winners')
                gone = mutation('audio_mute', dict(id='2', muted=True), 'gone-audio')
                assert gone['status'] == 'verified'
                call('audit', 'disappear', raw=True)
                vanished = call('luma', 'receipt', gone['ticket'])
                assert not vanished['ok'] and vanished['status'] == 'failed' and 'no longer' in vanished['error'], vanished
                for name, args in [('wifi', dict(enabled=True)), ('bluetooth', dict(enabled=True)), ('media_stop', {}), ('brightness', dict(level=60))]:
                    result = mutation(name, args, 'unavailable-' + name)
                    assert not result['ok'] and result['status'] == 'refused', result
                for name, args in [('focus', dict(minutes=20)), ('focus_pause', dict(paused=True)), ('focus_pause', dict(paused=False)), ('focus_cancel', {}), ('recording_start', dict(region=False, sound=False)), ('recording_pause', dict(paused=True)), ('recording_pause', dict(paused=False)), ('recording_stop', {})]:
                    assert mutation(name, args, 'fixture-' + name)['status'] == 'verified'
                invalid = mutation('preference', dict(key='focusMinutes', value=25.5), 'invalid-pref')
                assert not invalid['ok'] and invalid['status'] == 'refused'
                forbidden = mutation('preference', dict(key='lumaAccess', value='full'), 'permission-pref')
                assert not forbidden['ok'] and forbidden['status'] == 'refused'
                call('audit', 'lock', 'true', raw=True)
                assert call('luma', 'snapshot') == dict(ok=False, error='Unlock before reading desktop context')
                assert not call('notes', 'read', identifier)['ok'] and not call('reminders', 'read', reminder_id)['ok']
                locked = mutation('note_create', dict(body='Locked content'), 'locked')
                assert not locked['ok']
            persisted = json.loads((workspace / 'state/modesty/notes.json').read_text())
            assert persisted['items'][0]['body'] == 'Unsaved typing\nApplied through Luma'
            log.seek(0)
            output = log.read()
            assert not any(error in output for error in ('ReferenceError', 'TypeError', 'SyntaxError')), output
        finally:
            process.terminate()
            process.wait(timeout=5)

print('PASS production Luma IPC chains, Notes persistence, recurrence receipts, lock guards and safe native controls')

with tempfile.TemporaryDirectory(prefix='modesty-native-ack-') as temporary:
    workspace = Path(temporary)
    for name in ('services','scripts','theme'):
        (workspace/name).mkdir()
    mode = workspace/'mode'
    mode.write_text('success')
    fixture_stubs = dict(stubs)
    for name in ('SystemInfo','Display'):
        del fixture_stubs[name]
    fixture_stubs.update(
        Preferences='property bool preview:false;property bool lumaDesktop:true;property bool wallpaperColors:false;property bool matugenAutomatic:false;property string matugenScheme:"scheme-tonal-spot";property real matugenContrast:0;property int matugenSource:0',
        Notes='function receipt(id):var{return {};}', Reminders='function receipt(id):var{return {};}',
        IslandState='property string menu:"";property string state:"";')
    production = ('SystemInfo','Display','DesktopActions')
    for name in production:
        (workspace/'services'/f'{name}.qml').write_text((ROOT/'services'/f'{name}.qml').read_text())
    for name, body in fixture_stubs.items():
        (workspace/'services'/f'{name}.qml').write_text('pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {'+body+'}\n')
    (workspace/'services/qmldir').write_text('\n'.join(f'singleton {name} 1.0 {name}.qml' for name in (*production,*fixture_stubs))+'\n')
    (workspace/'theme/Theme.qml').write_text('pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {}\n')
    (workspace/'theme/qmldir').write_text('singleton Theme 1.0 Theme.qml\n')
    (workspace/'scripts/system.py').write_text('import json,sys\nprint(json.dumps([] if sys.argv[1]=="wallpapers" else {"brightness":.4,"maxBrightness":100,"brightnessAvailable":True}))\n')
    (workspace/'scripts/display.py').write_text('print(\'{"monitors":[]}\')\n')
    helper = f'''import json,sys,time
from pathlib import Path
if len(sys.argv)>1 and sys.argv[1]=='snapshot':
    print(json.dumps({{"nightLight":False,"temperature":4000}}));sys.exit()
for line in sys.stdin:
    request=json.loads(line)
    mode=Path({str(mode)!r}).read_text()
    time.sleep(.3)
    if mode=='no-ack':sys.exit()
    if mode=='failure':result={{'ok':False,'error':'Fixture permission denied'}}
    elif 'sequence' in request:result={{'ok':True,'sequence':request['sequence'],'value':.45 if mode=='mismatch' else request['value']/100}}
    else:result={{'ok':True,'nightLight':False if mode=='mismatch' else request['enabled']}}
    print(json.dumps(result),flush=True)
'''
    for name in ('brightness-stream.py','night-light.py'):
        (workspace/'scripts'/name).write_text(helper)
    (workspace/'shell.qml').write_text('''import QtQuick
import Quickshell
import Quickshell.Io
import "services" as Audit
ShellRoot {
    IpcHandler {target:"audit"
        function ready():bool{return Audit.SystemInfo.brightnessAvailable;}
        function execute(name:string,value:string):string{return JSON.stringify(Audit.DesktopActions.execute({name,args:name==="brightness"?{level:Number(value)}:{enabled:value==="true"}},"ack-fixture"));}
        function receipt(id:string):string{return JSON.stringify(Audit.DesktopActions.receipt(id));}
        function settled(name:string):bool{return name==="brightness"?!Audit.SystemInfo.brightnessDirty&&!Audit.SystemInfo.brightnessInFlight:!Audit.Display.nightDirty&&!Audit.Display.nightInFlight;}
    }
}
''')
    environment = dict(os.environ,QT_QPA_PLATFORM='offscreen',QSG_RHI_BACKEND='software',MODESTY_PREVIEW='0',
                       XDG_STATE_HOME=str(workspace/'state'),XDG_CONFIG_HOME=str(workspace/'config'),XDG_CACHE_HOME=str(workspace/'cache'))
    with (workspace/'log').open('w+') as log:
        process = subprocess.Popen(['qs','--no-color','-p',str(workspace)],env=environment,stdout=log,stderr=subprocess.STDOUT)
        try:
            wait(lambda:call('audit','ready'),'Brightness fixture loads')
            for name, target in (('brightness','60'),('nightlight','true')):
                for behavior, expected in (('success','verified'),('failure','failed'),('no-ack','failed'),('mismatch','requested')):
                    mode.write_text(behavior)
                    initial=call('audit','execute',name,target)
                    assert initial['status']=='requested', (name,behavior,initial)
                    assert call('audit','receipt',initial['ticket'])['status']=='requested', (name,behavior)
                    wait(lambda:call('audit','settled',name),name+' '+behavior+' response')
                    receipt=call('audit','receipt',initial['ticket'])
                    assert receipt['status']==expected, (name,behavior,receipt)
                    if behavior=='no-ack':assert 'without a response' in receipt['error'], receipt
                    print(f'PASS {name} {behavior} receipt requested then {expected}')
            log.seek(0)
            output=log.read()
            assert not any(error in output for error in ('ReferenceError','TypeError','SyntaxError')), output
        finally:
            process.terminate();process.wait(timeout=5)
