#!/usr/bin/env python3
"""Drive production Luma and Chromium in a disposable nested Hyprland."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request

from PIL import Image, ImageChops
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--plugin', type=Path, required=True)
parser.add_argument('--output', type=Path)
args = parser.parse_args()
plugin = args.plugin.resolve(strict=True)
out = args.output.resolve() if args.output else ROOT/'output/luma-private'/time.strftime('run-%Y%m%d-%H%M%S')
out.mkdir(parents=True)
parent = dict(os.environ)
env = dict(parent, AQ_DRM_DEVICES='/dev/dri/modesty-no-kms', HYPRLAND_NO_SD_NOTIFY='1', HYPRLAND_NO_SD_VARS='1',
           XDG_CONFIG_HOME=str(out/'config'), XDG_STATE_HOME=str(out/'state'), XDG_CACHE_HOME=str(out/'cache'),
           QS_NO_RELOAD_POPUP='1', MODESTY_PREVIEW='0', MODESTY_COMPAT='0', MODESTY_PRIVATE_TEST='1',
           DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent-luma-test-bus',
           DBUS_SYSTEM_BUS_ADDRESS='unix:path=/nonexistent-luma-test-bus', NO_AT_BRIDGE='1')
binary_dir=out/'bin'
binary_dir.mkdir()
shutil.copyfile(ROOT/'tests/fixtures/luma-private-python.py',binary_dir/'python3')
(binary_dir/'python3').chmod(0o700)
env.update(PATH=str(binary_dir)+':'+env['PATH'],MODESTY_PRIVATE_TEST_OUTPUT=str(out))
env.pop("AT_SPI_BUS_ADDRESS",None)
processes, observations = [], []
ws = None
counter = 0
shell = None
original_plugins = None
original_window = None
paths=[ROOT/path for path in ('README.md','plugins/luma-capture/plugin.cpp','plugins/luma-capture/private-input.hpp',
    'modules/canvas/CommandCanvas.qml','modules/canvas/LumaConversation.qml','components/HintBubble.qml','services/Luma.qml',
    'scripts/luma-assistant.py','scripts/luma-window.py','scripts/window-toplevel.c','scripts/luma/protocol.py',
    'tests/luma-private-live.py','tests/luma-page.py','tests/luma-page-qml.py','tests/fixtures/luma-private-python.py',
    'tests/fixtures/luma-private-browser.html','tests/fixtures/luma-page-document.py')]+[plugin]
manifest={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


def run(command, environment=None, timeout=15):
    result = subprocess.run(command, env=environment or env, capture_output=True, text=True, timeout=timeout)
    assert result.returncode == 0, (command, result.stdout, result.stderr)
    return result.stdout.strip()


def launch(command, name):
    with (out/(name+'.log')).open('w') as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    processes.append(process)
    return process


def wait(operation, label, timeout=15):
    deadline = time.monotonic()+timeout
    error = None
    while time.monotonic()<deadline:
        assert all(p.poll() is None for p in processes), 'Fixture exited. '+str(out)
        try:
            value = operation()
            if value:
                return value
        except (OSError, ValueError, AssertionError, StopIteration) as caught:
            error = caught
        time.sleep(.08)
    raise AssertionError('Timed out '+label+' '+str(error))


def ipc(target, method, *values):
    return run(['qs', 'ipc', '--pid', str(shell.pid), 'call', target, method, *map(str, values)])


def state():
    return json.loads(ipc('canvas', 'status'))


def evaluate(expression):
    global counter
    counter += 1
    ws.send(json.dumps({'id':counter,'method':'Runtime.evaluate','params':{'expression':expression,'returnByValue':True}}))
    while True:
        message = json.loads(ws.recv(timeout=10))
        if message.get('id')==counter:
            assert 'error' not in message and 'exceptionDetails' not in message.get('result', {}), message
            return message['result']['result'].get('value')


def observe(name, focus=True):
    value = dict(name=name, canvas=state(), browser=evaluate('snapshot()'),
                 native=json.loads(run(['hyprctl','activewindow','-j'])))
    observations.append(value)
    (out/'observations.json').write_text(json.dumps(observations, indent=2)+'\n')
    if focus:
        assert value['browser']['focus'], value
        assert not any(event['type']=='blur' for event in value['browser']['events']), value
    print(name+' '+json.dumps({'query':value['canvas']['query'],'destination':value['canvas']['inputDestination'],
                              'browser':value['browser']['text'],'focus':value['browser']['focus']}), flush=True)
    return value


def device(command):
    driver.stdin.write(command+'\n');driver.stdin.flush()
    assert select.select([driver.stdout], [], [], 5)[0], 'Input helper blocked '+command
    assert driver.stdout.readline().strip()=='ok', 'Input helper failed '+command
    time.sleep(.035)


def key(code, down=None, keyboard=0):
    if down is None:
        device(f'key {keyboard} {code} 1');device(f'key {keyboard} {code} 0')
    else:
        device(f'key {keyboard} {code} {int(down)}')


def text(value):
    codes = dict(zip('qwertyuiopasdfghjklzxcvbnm', [16,17,18,19,20,21,22,23,24,25,30,31,32,33,34,35,36,37,38,44,45,46,47,48,49,50]))
    codes.update({' ':57,'1':2,'2':3,'3':4})
    for char in value:
        if char==':':
            key(42,True);device('mods 0 1 0 0 0');key(39);key(42,False);device('mods 0 0 0 0 0')
        else:
            key(codes[char])


def control(code):
    key(29, True);device('mods 0 4 0 0 0');key(code);key(29, False);device('mods 0 0 0 0 0')


def move(x, y):
    output.update(json.loads(run(["hyprctl","monitors","-j"]))[0])
    device(f'move {int(x)} {int(y)} {output["width"]} {output["height"]}')
    actual=json.loads(run(['hyprctl','cursorpos','-j']))
    with (out/'pointer.jsonl').open('a') as log: log.write(json.dumps(dict(wanted=[x,y],actual=actual,extent=[output['width'],output['height']]))+'\n')


def click(x, y):
    move(x,y);device('button 272 1');device('button 272 0')


def item(name):
    return json.loads(ipc('private-test','item',name))


def click_item(name):
    found = wait(lambda: (value if (value:=item(name)).get('visible') else None), 'visible '+name)
    click(found['x']+found['width']/2,found['y']+found['height']/2)


def capture(name, baseline=None):
    path=out/(name+'.png')
    run(['grim','-o',output['name'],str(path)])
    if baseline:
        difference=ImageChops.difference(Image.open(path).convert('RGB'),Image.open(out/(baseline+'.png')).convert('RGB'))
        assert max(max(pair) for pair in difference.getextrema())<=2,(name,difference.getextrema())
    return path


def open_private():
    ipc('canvas','open')
    return wait(lambda: (s if (s:=state())['open'] and s['inputDestination']=='luma' else None), 'private route '+json.dumps(state()))


def escape():
    key(1)
    wait(lambda: not state()['open'], 'Escape closes canvas')
    assert not any(e.get('key')=='Escape' for e in evaluate('events')),'Escape reached browser'


def browser_focus():
    run(['hyprctl','eval','hl.dispatch(hl.dsp.focus({window='+json.dumps('address:'+browser_address)+'}))'])
    wait(lambda: evaluate('document.hasFocus()'), 'browser focus')
    evaluate('editor.focus();events.length=0;editor.value=""')


print('Evidence '+str(out), flush=True)
execs=out/'config/hypr/hyprland/execs.lua'
execs.parent.mkdir(parents=True)
execs.write_text('local fn   = require("utils.functions")\n')
config = out/'hyprland.lua'
config.write_text('''hl.monitor({output="",mode="1100x800@60",position="0x0",scale=1})
hl.config({input={follow_mouse=0},misc={disable_watchdog_warning=true,disable_hyprland_logo=true,disable_splash_rendering=true},ecosystem={no_donation_nag=true,no_update_news=true},general={gaps_in=0,gaps_out=0,border_size=0},animations={enabled=false},decoration={rounding=0,blur={enabled=false},shadow={enabled=false}}})
''')
with config.open('a') as stream: stream.write('package.preload["utils.functions"]=function()return {}end\ndofile('+json.dumps(str(execs))+')\n')
marker = out/'state/modesty/luma-capture.json'
marker.parent.mkdir(parents=True)
marker.write_text(json.dumps({'plugin':str(plugin)}))
(marker.parent/'preferences.json').write_text(json.dumps({'companionEnabled':False,'welcomeAtLogin':False,'lumaAutoAnswer':False,
    'searchMotion':0,'searchTravelDuration':0,'motion':'instant','lumaEffects':False,'searchY':24}))
fixture = out/'production'
fixture.mkdir()
for name in ('services','scripts','modules','components','theme','assets'):
    (fixture/name).symlink_to(ROOT/name, target_is_directory=True)
source = (ROOT/'shell.qml').read_text().replace('import QtQuick\n','import QtQuick\nimport QtTest\nimport Quickshell.Wayland\nimport Quickshell.Hyprland\n',1)
extra = '''
    property bool grabWanted:false
    property bool siblingWanted:false
    PanelWindow {id:siblingWindow;visible:siblingWanted;implicitWidth:180;implicitHeight:80;anchors{top:true;right:true}color:"#222222";WlrLayershell.namespace:"luma-test-sibling";WlrLayershell.keyboardFocus:WlrKeyboardFocus.Exclusive
        TextInput {id:siblingEditor;focus:true;anchors.fill:parent}
    }
    PanelWindow {id:grabWindow;visible:grabWanted;implicitWidth:80;implicitHeight:80;anchors{top:true;left:true}color:"#222222";WlrLayershell.namespace:"luma-test-grab"}
    HyprlandFocusGrab {active:grabWanted;windows:[grabWindow]}
    TestCase {id:probe;when:false}
    WlSessionLock {id:testLock;locked:false;WlSessionLockSurface {color:"#330000"}}
    IpcHandler {
        target:"private-test"
        function refresh():void {LumaCapture.refresh();}
        function assistantState():string {return JSON.stringify({busy:Luma.busy,messages:Luma.messages,currentWindow:Luma.currentWindow,error:Luma.error});}
        function pagePermission(value:bool):void {Preferences.lumaWindowContext=value;}
        function pageAi(value:bool):void {Preferences.searchAiEnabled=value;}
        function pageAttachments():void {Luma.attachments=["/fixture-pending-attachment"];Luma.sharedText="FIXTURE CLIPBOARD OMIT";Luma.pendingTask={text:"FIXTURE TASK OMIT"};}
        function pageGeneration(value:double):void {LumaCapture.generation=value;}
        function pageRetry():bool {return Luma.retry();}
        function pageWidth(value:int):void {Preferences.searchWidth=value;}
        function pageTooltipDelay(value:int):void {Preferences.tooltipDelay=value;}
        function savedStatus():string {return JSON.stringify({busy:LumaCapture.busy,state:LumaCapture.state,error:LumaCapture.error});}
        function safetyClose():void {CanvasState.close("mode-change");}
        function lock(value:bool):void {testLock.locked=value;}
        function grab(value:bool):void {grabWanted=value;}
        function protection(value:bool):void {LumaCapture.setEnabled(value);}
        function settings(value:bool):void {IslandState.settingsOpen=value;}
        function sibling(value:bool):void {siblingWanted=value;}
        function siblingText():string {return siblingEditor.text;}
        function armingDelay(value:int):void {probe.findChild(commandCanvas,"lumaPrivateArming").interval=value;}
        function item(name:string):string {
            function findLabel(root){
                if((root.label===name||root.text===name)&&root.visible)return root;
                for(const child of root.children??[]){const found=findLabel(child);if(found)return found;}
                return null;
            }
            const child=probe.findChild(commandCanvas.contentItem,name)??findLabel(commandCanvas.contentItem);
            if(!child)return "{}";
            const target=child.mapToItem?child:child.contentItem;
            const at=target.mapToItem(commandCanvas.contentItem,target.width/2,target.height/2);
            return JSON.stringify({x:at.x-target.width/2,y:at.y-target.height/2,width:target.width,height:target.height,text:child.text??child.heldText??"",visible:child.opened??child.visible,enabled:child.enabled,label:child.label??"",activeFocus:child.activeFocus});
        }
    }
'''
(fixture/'shell.qml').write_text(source[:source.rfind('}')]+extra+'}\n')
try:
    original_plugins = json.loads(run(['hyprctl','plugin','list','-j'],parent))
    original_window = json.loads(run(['hyprctl','activewindow','-j'],parent)).get('address')
    compositor = launch(['Hyprland','-c',str(config)],'compositor')
    instance = wait(lambda: next(i for i in json.loads(run(['hyprctl','instances','-j'],parent)) if i['pid']==compositor.pid),'nested compositor')
    assert instance['instance'] != parent.get('HYPRLAND_INSTANCE_SIGNATURE')
    env.update(WAYLAND_DISPLAY=instance['wl_socket'],HYPRLAND_INSTANCE_SIGNATURE=instance['instance'])

    def monitor():
        monitors = json.loads(run(['hyprctl','monitors','-j']))
        if not monitors:
            nested = next((c for c in json.loads(run(['hyprctl','clients','-j'],parent)) if c['pid']==compositor.pid), None)
            if nested:
                run(['hyprctl','eval','hl.dispatch(hl.dsp.focus({window='+json.dumps('address:'+nested['address'])+'}))'],parent)
            subprocess.run(['grim','-g','0,0 1x1','-'],env=parent,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=3)
        return next(iter(monitors),None)

    output = wait(monitor,'nested output')
    assert output['hardwareDetails']['backend']=='wayland', output
    assert run(['hyprctl','plugin','load',str(plugin)])=='ok'
    print('Native API '+run(['hyprctl','luma-private','status']), flush=True)
    run(['cc',str(ROOT/'tests/fixtures/luma-private-input.c'),'-o',str(out/'input'),*shlex.split(run(['pkg-config','--cflags','--libs','wayland-client','xkbcommon']))])
    driver = subprocess.Popen([str(out/'input')],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(out/'input.log').open('w'),text=True,start_new_session=True)
    processes.append(driver)
    assert driver.stdout.readline().strip()=='ready'
    bus_address='unix:path='+str(out/'session-bus')
    launch(['dbus-daemon','--session','--nofork','--address='+bus_address],'session-bus')
    env['DBUS_SESSION_BUS_ADDRESS']=bus_address
    env.pop('NO_AT_BRIDGE',None)
    wait(lambda:(out/'session-bus').exists(),'private session bus')
    env['AT_SPI_BUS_ADDRESS']='unix:path='+str(out/'a11y')
    launch(['dbus-daemon','--session','--nofork','--address='+env['AT_SPI_BUS_ADDRESS']],'accessibility-bus')
    wait(lambda:(out/'a11y').exists(),'private accessibility bus')
    launch(['/usr/lib/at-spi2-registryd'],'accessibility-registry')
    env['ACCESSIBILITY_ENABLED']='1'
    browser = launch([str(Path.home()/'.cache/ms-playwright/chromium-1243/chrome-linux64/chrome'),
                      '--ozone-platform=wayland','--no-first-run','--no-default-browser-check','--disable-background-networking',
                      '--disable-extensions','--force-renderer-accessibility=complete','--disable-component-update','--password-store=basic','--remote-debugging-port=0',
                      '--user-data-dir='+str(out/'browser'),(ROOT/'tests/fixtures/luma-private-browser.html').as_uri()],'browser')
    browser_started=time.monotonic()
    port = wait(lambda: int((out/'browser/DevToolsActivePort').read_text().splitlines()[0]),'browser CDP')
    def page():
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list', timeout=2) as response:
            return next(p['webSocketDebuggerUrl'] for p in json.load(response) if p['type']=='page')
    ws = connect(wait(page,'browser page'))
    wait(lambda: evaluate('typeof snapshot==="function"'),'browser script')
    browser_address = wait(lambda: next(c['address'] for c in json.loads(run(['hyprctl','clients','-j'])) if 'Luma private browser probe' in c['title']), 'browser window')
    shell = launch(['qs','-p',str(fixture/'shell.qml')],'production')
    wait(state,'production IPC')
    browser_focus()
    wait(lambda:time.monotonic()-browser_started>30,'browser startup promotions settled',timeout=35)
    shortcut_command=shlex.join(['qs','ipc','--pid',str(shell.pid),'call','canvas','toggle'])
    assert run(['hyprctl','eval','hl.bind("SUPER+SPACE",hl.dsp.exec_cmd('+json.dumps(shortcut_command)+'),{description="Luma private test"})'])=='ok'
    assert not item('lumaAnalyzePage').get('visible'),'Page icon visible outside private session'
    open_private()
    wait(lambda:item('lumaAnalyzePage').get('enabled'),'Analyze Page ready')
    button=item('lumaAnalyzePage');handle=item('lumaDragHandle')
    assert button['x']+button['width']+12<=handle['x'],(button,handle)
    assert 'AI provider' in button['label'] and not button['text'],button
    for method in ('pagePermission','pageAi'):
        ipc('private-test',method,'false')
        assert not item('lumaAnalyzePage')['enabled'],method
        ipc('private-test',method,'true')
        wait(lambda:item('lumaAnalyzePage')['enabled'],method+' restored')
    generation=json.loads(run(['hyprctl','luma-private','status']))['generation']
    ipc('private-test','pageGeneration',str(generation+1))
    assert not item('lumaAnalyzePage')['enabled'],'Mismatched generation enabled action'
    ipc('private-test','pageGeneration',str(generation))
    wait(lambda:item('lumaAnalyzePage')['enabled'],'generation restored')
    text('web: explain page')
    for width in (420,960,700):
        ipc('private-test','pageWidth',width)
        wait(lambda:abs(state()['width']-min(width,state()['screenWidth']-24))<1,'page width '+str(width))
        entry=item('commandCanvasSearch');button=item('lumaAnalyzePage');handle=item('lumaDragHandle');send=item('Ask Luma · Ctrl+Enter')
        assert entry['width']>120 and entry['x']+entry['width']<=button['x']
        assert button['x']+button['width']<=send['x'] and send['x']+send['width']<=handle['x'],(width,entry,button,send,handle)
    ipc('private-test','pageAttachments')
    before=evaluate('snapshot()');native_before=json.loads(run(['hyprctl','activewindow','-j']))
    ipc('private-test','pageTooltipDelay','1500')
    button=item('lumaAnalyzePage');move(button['x']+button['width']/2,button['y']+button['height']/2)
    capture('page-before-tooltip');assert not item('lumaPageHint')['visible']
    wait(lambda:item('lumaPageHint').get('visible') and 'AI provider' in item('lumaPageHint').get('text',''),'page tooltip')
    assert item('lumaPageHint')['height']>30
    assert evaluate('snapshot()')==before
    (out/'page-tooltip-state.json').write_text(json.dumps(item('lumaPageHint'),indent=2)+'\n')
    capture('page-tooltip-private','page-before-tooltip')
    ipc('private-test','pageTooltipDelay','500')
    move(1,1);wait(lambda:not item('lumaPageHint')['visible'],'page tooltip hidden')
    click_item('lumaAnalyzePage')
    wait(lambda:not json.loads(ipc('private-test','assistantState'))['busy'] and (out/'page-provider.json').exists(),'real page acquisition',timeout=45)
    page_state=json.loads(ipc('private-test','assistantState'))
    assert not page_state['error'],page_state
    if page_state['currentWindow']['scope']!='document_text':
        probe_script=out/'document-probe.py'
        probe_script.write_text("""import gi,json,traceback,importlib.util,sys
from pathlib import Path
gi.require_version('Atspi','2.0')
from gi.repository import Atspi
Atspi.set_timeout(350,350)
selected=json.loads(sys.stdin.readline())
desktop=Atspi.get_desktop(0)
def dump(node,depth=0):
 if depth>7:return
 state=node.get_state_set()
 print(json.dumps(dict(depth=depth,pid=node.get_process_id(),name=node.get_name(),role=node.get_role_name(),states=[s.value_nick for s in state.get_states()],interfaces=node.get_interfaces())))
 for i in range(min(node.get_child_count(),40)):dump(node.get_child_at_index(i),depth+1)
for i in range(desktop.get_child_count()):
 app=desktop.get_child_at_index(i)
 if app.get_process_id()==selected['pid']:dump(app)
spec=importlib.util.spec_from_file_location('window',sys.argv[1]);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
try:print(module.document_text(selected,desktop,Atspi))
except Exception:traceback.print_exc()
""")
        probe_result=subprocess.run([sys.executable,str(probe_script),str(ROOT/'scripts/luma-window.py')],input=json.dumps(native_before),env=env,text=True,capture_output=True,timeout=10)
        (out/'document-probe.log').write_text(probe_result.stdout+probe_result.stderr)
    assert page_state['currentWindow']['scope']=='document_text',page_state
    body=json.loads((out/'page-provider.json').read_text())
    assert 'LUMA BELOW-FOLD DOCUMENT MARKER 7319' in json.dumps(body),body
    assert all(value in json.dumps(body) for value in ('LUMA MIXED PARAGRAPH START','INLINE LINK','MIXED PARAGRAPH END'))
    assert not any(value in json.dumps(body) for value in ('LUMA PASSWORD MUST NOT SHARE','LUMA HIDDEN MUST NOT SHARE','FIXTURE CLIPBOARD OMIT','FIXTURE TASK OMIT','fixture-pending-attachment'))
    assert state()['query']=='web: explain page' and state()['scope']=='ask',state()
    assert item('lumaPageScope')['text'].startswith('Exposed document text'),item('lumaPageScope')
    after=evaluate('snapshot()')
    assert after==before and after['scrollY']==0,(before,after)
    assert json.loads(run(['hyprctl','activewindow','-j']))==native_before,'Analyze Page changed native target'
    scope=page_state['currentWindow']
    source=Image.open(out/'page-provider.png').convert('RGB')
    visible=Image.open(capture('page-visible-window')).convert('RGB')
    x,y=native_before['at'];width,height=native_before['size']
    visible=visible.crop((x,y,x+width,y+height))
    assert source.size==visible.size
    assert max(max(pair) for pair in ImageChops.difference(source,visible).getextrema())<=2
    (out/'page-document-scope.json').write_text(json.dumps(scope,indent=2)+'\n')
    (out/'page-document-provider.json').write_text(json.dumps(body,indent=2)+'\n')
    shutil.copyfile(out/'page-provider.png',out/'page-document-provider.png')
    (out/'page-provider.json').unlink()
    (out/'page-fail-once').touch()
    click_item('lumaAnalyzePage')
    wait(lambda:not json.loads(ipc('private-test','assistantState'))['busy'] and json.loads(ipc('private-test','assistantState'))['error'],'page failure')
    failed=json.loads(ipc('private-test','assistantState'))
    assert failed['messages'][-2]['requestKind']=='analyze_page',failed
    (out/'page-provider.json').unlink()
    ipc('private-test','pagePermission','false')
    assert ipc('private-test','pageRetry')=='false'
    assert not (out/'page-provider.json').exists()
    ipc('private-test','pagePermission','true')
    click_item('Retry')
    wait(lambda:not json.loads(ipc('private-test','assistantState'))['busy'] and (out/'page-provider.json').exists(),'isolated page retry',timeout=45)
    retried=json.loads((out/'answer-request.json').read_text())
    assert retried['requestContext']['kind']=='analyze_page' and set(retried)=={'query','requestContext','model','aiEnabled','currentWindowAllowed'},retried
    assert not json.loads(ipc('private-test','assistantState'))['error']
    (out/'page-retry-request.json').write_text(json.dumps(retried,indent=2)+'\n')
    assert evaluate('snapshot()')==before
    (out/'page-provider.json').unlink()
    escape()
    native_document=launch([sys.executable,str(ROOT/'tests/fixtures/luma-page-document.py')],'native-document')
    native_target=wait(lambda:next(c for c in json.loads(run(['hyprctl','clients','-j'])) if c['title']=='Luma native document probe'),'native document window')
    run(['hyprctl','eval','hl.dispatch(hl.dsp.focus({window='+json.dumps('address:'+native_target['address'])+'}))'])
    open_private();wait(lambda:item('lumaAnalyzePage')['enabled'],'native page ready')
    click_item('lumaAnalyzePage')
    wait(lambda:not json.loads(ipc('private-test','assistantState'))['busy'] and (out/'page-provider.json').exists(),'native document acquisition',timeout=45)
    native_page=json.loads(ipc('private-test','assistantState'))
    native_body=json.loads((out/'page-provider.json').read_text())
    assert not native_page['error'] and native_page['currentWindow']['scope']=='document_text',native_page
    assert 'LUMA NATIVE BELOW-FOLD 9427' in json.dumps(native_body)
    assert json.loads(run(['hyprctl','activewindow','-j']))['address']==native_target['address']
    (out/'page-native-scope.json').write_text(json.dumps(native_page['currentWindow'],indent=2)+'\n')
    (out/'page-native-provider.json').write_text(json.dumps(native_body,indent=2)+'\n')
    shutil.copyfile(out/'page-provider.png',out/'page-native-provider.png')
    (out/'page-provider.json').unlink()
    escape();processes.remove(native_document);os.killpg(native_document.pid,signal.SIGTERM);native_document.wait(timeout=5)
    browser_focus();open_private()
    before=evaluate('snapshot()')
    registry=next(p for p in processes if p.args[0]=='/usr/lib/at-spi2-registryd')
    processes.remove(registry);registry.terminate();registry.wait(timeout=5)
    accessibility=next(p for p in processes if p.args[0]=='dbus-daemon' and '--address='+env['AT_SPI_BUS_ADDRESS'] in p.args)
    processes.remove(accessibility);os.killpg(accessibility.pid,signal.SIGTERM);accessibility.wait(timeout=5)
    click_item('lumaAnalyzePage')
    wait(lambda:not json.loads(ipc('private-test','assistantState'))['busy'] and (out/'page-provider.json').exists(),'visible page fallback',timeout=45)
    fallback=json.loads(ipc('private-test','assistantState'))
    assert not fallback['error'] and fallback['currentWindow']['scope']=='visible_window',fallback
    assert item('lumaPageScope')['text'].startswith('Visible window only'),item('lumaPageScope')
    assert evaluate('snapshot()')==before
    (out/'page-fallback-scope.json').write_text(json.dumps(fallback['currentWindow'],indent=2)+'\n')
    assert not list((out/'cache/modesty/window-context').glob('*.png')),'Capture image leaked'
    observe('analyze-page-document-and-fallback')
    ipc('luma','clear');escape();browser_focus()
    capture('clean-initial')
    ipc('private-test','armingDelay','1000')
    ipc('canvas','open')
    assert state()['privateSession'] and not state()['presented'],'Private editor was exposed before native reservation'
    assert evaluate('document.hasFocus()') and not evaluate('events.length'),'Arming moved browser focus'
    wait(lambda: state()['presented'] and state()['inputDestination']=='luma','private presentation after arming')
    text('armed');assert state()['query']=='armed' and evaluate('editor.value')==''
    observe('hidden-until-native-arming')
    escape();browser_focus();ipc('private-test','armingDelay','80')
    open_private()
    assert state()['privateSession'] and state()['privateReady'], state()
    text('hello luma')
    assert state()['query']=='hello luma', state()
    first = observe('startup-private-typing')
    capture('capture-while-typing','clean-initial')
    assert first['browser']['text']=='' and first['browser']['events']==[], first
    key(14);text('a')
    control(30);text('replacement')
    assert state()['query']=='replacement', state()
    observe('editing-and-selection')
    click(70,90)
    wait(lambda: state()['inputDestination']=='native','browser handoff')
    text('browser')
    assert evaluate('editor.value')=='browser' and state()['query']=='replacement'
    observe('browser-handoff')
    click_item('commandCanvasSearch')
    wait(lambda: state()['inputDestination']=='luma','Luma resume')
    key(107);text(' again')
    assert state()['query']=='replacement again', state()
    observe('canvas-resume')
    control(30);control(46)
    click(70,90);control(30);control(47)
    wait(lambda: evaluate('editor.value')=='replacement again','copy Luma to browser')
    evaluate('editor.value="browser clipboard";editor.focus()')
    control(30);control(46)
    click_item('commandCanvasSearch');control(30);control(47)
    wait(lambda: state()['query']=='browser clipboard','clipboard transfer into Luma')
    observe('clipboard-both-directions')
    s = state();handle = item('lumaDragHandle')
    move(handle['x']+16,handle['y']+16);device('button 272 1')
    move(handle['x']+45,handle['y']+30);move(handle['x']+160,handle['y']+110);device('button 272 0')
    wait(lambda: abs(state()['x']-s['x'])>40,'handle drag')
    s=state();assert s['normalX']==50 and s['normalY']==24,s
    handle=item('lumaDragHandle');move(handle['x']+16,handle['y']+16);device('button 272 1')
    move(output['width']-1,output['height']-1);device('button 272 0')
    s=state();assert s['x']>=12 and s['y']>=12 and s['x']+s['width']<=output['width']-11 and s['y']+s['height']<=output['height']-15,s
    observe('drag-and-bounds')
    capture('capture-after-drag')
    for _ in range(8):
        key(15)
        if item('lumaDragHandle').get('activeFocus'):break
    assert item('lumaDragHandle').get('activeFocus'),'Drag handle is not reachable by Tab'
    previous_x=state()['x'];key(105)
    assert state()['x']<previous_x,'Focused handle did not move with arrow key'
    key(125,True);device('mods 0 64 0 0 0');key(57);key(125,False);device('mods 0 0 0 0 0')
    wait(lambda: state()['inputDestination']=='luma','real US-map shortcut')
    assert state()['open'] and state()['query']=='browser clipboard','Repeated shortcut dismissed or cleared private Luma'
    click(70,90);escape()
    observe('escape-while-paused')
    time.sleep(.2)
    capture('clean-clipboard','capture-after-drag')
    ended=json.loads(run(['hyprctl','luma-private','status']))
    stale=json.loads(run(['hyprctl','luma-private','open',str(ended['generation']),str(shell.pid),output['name']]))
    assert 'error' in stale and not state()['open'],'Closed generation reopened'
    open_private();escape();observe('escape-while-routed')
    open_private()
    click_item('Filter · Auto')
    wait(lambda: state()['scopeMenuOpen'],'scope menu')
    observe('scope-menu')
    capture('capture-menu','clean-clipboard')
    menu=state()['scopeMenuBox']
    click(menu['x']+60,menu['y']+39*6+19)
    wait(lambda: state()['scope']=='ask','scope menu conversation choice')
    click_item('commandCanvasSearch');text('question')
    click_item('Ask Luma · Ctrl+Enter')
    wait(lambda: any(m['role']=='assistant' and 'copy proof' in m['text'] for m in json.loads(ipc('private-test','assistantState'))['messages']),'submitted production answer')
    assert json.loads((out/'answer-request.json').read_text())['query']=='question'
    click_item('Copy code')
    assert run(['wl-paste','--no-newline']).strip()=='copy proof'
    observe('submit-and-response-control')
    capture('capture-response','clean-clipboard')
    click_item('New conversation');assert state()['open']
    click_item('Attach file · sent to answer provider')
    wait(lambda: state()['attachmentPicker'],'attachment picker')
    click_item('lumaAttachmentFilter');text('test')
    assert item('lumaAttachmentFilter')['text']=='test',item('lumaAttachmentFilter')
    observe('attachment-filter')
    capture('capture-picker','clean-clipboard')
    escape();observe('escape-inside-picker')
    open_private();click_item('Filter · Auto');escape();observe('escape-inside-menu')
    open_private();ipc('canvas','close');assert state()['open'],'Incidental close dismissed private Luma'
    ipc('private-test','settings','true');time.sleep(.3)
    assert state()['open'],'Settings notification dismissed private Luma'
    ipc('private-test','settings','false');browser_focus()
    ipc('canvas','toggle');wait(lambda: state()['inputDestination']=='luma','same-client focus recovery')
    text('sibling');assert state()['query']=='sibling',state()
    observe('same-client-settings-focus')
    escape()
    browser_focus();open_private()
    ipc('private-test','sibling','true')
    wait(lambda: state()['inputDestination']=='native','same-client native focus')
    ipc('canvas','toggle')
    wait(lambda: not state()['open'],'same-client resume refuses explicitly')
    assert 'same-client-focus' in state()['captureError'] and ipc('private-test','siblingText')==''
    observe('same-client-resume-refusal',focus=False)
    ipc('private-test','sibling','false')
    browser_focus();key(30,True)
    ipc('canvas','open')
    wait(lambda: state()['inputDestination']=='waiting-luma','opening held native key')
    assert state()['presented'],'Waiting canvas never became available'
    key(48)
    assert evaluate('editor.value')=='a','New key leaked during neutral waiting'
    key(30,False)
    wait(lambda: state()['inputDestination']=='luma','native held key drains')
    text('b');assert state()['query']=='b' and evaluate('editor.value')=='a'
    observe('held-key-on-open')
    escape();browser_focus();key(29,True);device('mods 0 4 0 0 0')
    ipc('canvas','open')
    wait(lambda: state()['inputDestination']=='waiting-luma','native Ctrl on open')
    key(47)
    assert not any(event.get('key','').lower()=='v' for event in evaluate('events')),'Ctrl+V reached native client during private wait'
    escape();key(29,False);device('mods 0 0 0 0 0')
    assert not state()['open']
    observe('escape-and-paste-during-neutral-wait')
    browser_focus();open_private();text('b')
    key(42,True);device('mods 0 1 0 0 0');key(30,True)
    time.sleep(.75)
    click(70,90)
    stopped_query=state()['query'];time.sleep(.65);assert state()['query']==stopped_query,'Private repeat continued after handoff'
    wait(lambda: state()['inputDestination']=='waiting-native','held modifier handoff gating')
    key(48);key(30,False);key(42,False);device('mods 0 0 0 0 0')
    wait(lambda: state()['inputDestination']=='native','held modifier neutral handoff')
    text('c');assert evaluate('editor.value').endswith('c') and 'B' not in evaluate('editor.value')
    observe('held-modifier-handoff')
    ipc('canvas','toggle');wait(lambda: state()['inputDestination']=='luma','shortcut resume')
    key(30,True);escape();key(30,False)
    observe('held-key-escape')
    browser_focus();open_private();key(1,True)
    wait(lambda: not state()['open'],'Escape press closes before release')
    assert run(['hyprctl','plugin','unload',str(plugin)])=='ok'
    key(1,False);text('e')
    assert evaluate('editor.value')=='e' and not any(e.get('key')=='Escape' for e in evaluate('events'))
    assert run(['hyprctl','plugin','load',str(plugin)])=='ok'
    ipc('private-test','refresh');wait(lambda: state()['privateReady'],'capability after Escape-owner unload')
    observe('escape-release-after-unload')
    browser_focus();open_private();device('map 1 us')
    key(30,True,0);key(30,True,1);key(30,False,0);key(30,False,1)
    assert state()['query']=='a',state()
    device('map 1 de');key(21,keyboard=1)
    assert state()['query'].endswith('z'),state()
    observe('multiple-keyboards-and-layout')
    key(30,True,1);device('remove 1')
    wait(lambda: not state()['open'],'held keyboard removal ends private input')
    text('native');assert evaluate('editor.value')=='native'
    observe('held-keyboard-removal')
    browser_focus();open_private()
    pinned=state()['screenName']
    assert run(['hyprctl','output','create','headless','LUMA-TEST'])=='ok'
    run(['hyprctl','eval','hl.monitor({output="LUMA-TEST",mode="800x600@60",position="1100x0",scale=1})'])
    wait(lambda: len(json.loads(run(['hyprctl','monitors','-j'])))==2,'second nested output')
    run(['hyprctl','eval','hl.dispatch(hl.dsp.focus({monitor="LUMA-TEST"}))'])
    time.sleep(.2)
    assert state()['open'] and state()['screenName']==pinned,'Private canvas followed monitor focus'
    run(['hyprctl','eval','hl.monitor({output='+json.dumps(pinned)+',disabled=true})'])
    wait(lambda: not state()['open'],'pinned monitor removal closes private canvas')
    run(['hyprctl','eval','hl.monitor({output='+json.dumps(pinned)+',disabled=false,mode="1100x800@60",position="0x0",scale=1})'])
    wait(lambda: any(m['name']==pinned for m in json.loads(run(['hyprctl','monitors','-j']))),'pinned monitor restore')
    assert run(['hyprctl','output','remove','LUMA-TEST'])=='ok'
    browser_focus();open_private();observe('monitor-pin-and-removal')
    device('ime-key');device('ime-empty')
    wait(lambda: not state()['open'],'transient IME closes private canvas')
    assert evaluate('editor.value')=='' and not any(event.get('key')=='a' for event in evaluate('events')),'First unsafe key leaked'
    device('ime-off');browser_focus();open_private()
    observe('first-unsafe-key-consumed')
    device('ime-on')
    wait(lambda: not state()['open'],'active IME grab terminates private input')
    ipc('canvas','open')
    wait(lambda: not state()['open'] and 'IME' in state()['captureError'],'active IME refuses private opening')
    observe('ime-fail-closed')
    device('ime-off');browser_focus();open_private()
    ipc('private-test','grab','true')
    wait(lambda: not state()['open'],'native seat grab terminates private input')
    ipc('canvas','open');time.sleep(.2);assert not state()['open']
    ipc('private-test','grab','false');browser_focus();open_private()
    ipc('private-test','lock','true')
    wait(lambda: not state()['open'],'native session lock ends private input')
    text('lock')
    ipc('canvas','open');time.sleep(.2)
    assert not state()['open'],'Native lock allowed private opening'
    ipc('private-test','lock','false');browser_focus()
    open_private();key(30,True)
    assert run(['hyprctl','plugin','unload',str(plugin)])=='ok'
    key(30,False);text('native')
    wait(lambda: not state()['open'],'unload closes canvas')
    assert evaluate('editor.value')=='native',evaluate('snapshot()')
    observe('held-key-plugin-unload')
    assert run(['hyprctl','plugin','load',str(plugin)])=='ok'
    ipc('private-test','refresh')
    wait(lambda: state()['privateReady'],'reload capability')
    open_private();key(30,True)
    shell.terminate();shell.wait(timeout=5);processes.remove(shell)
    key(30,False);text(' after')
    assert evaluate('editor.value')=='native after',evaluate('snapshot()')
    shell=launch(['qs','-p',str(fixture/'shell.qml')],'production-restarted')
    wait(state,'restarted production IPC');browser_focus();open_private()
    observe('shell-target-destruction-recovery')
    for code,mask in ((42,1),(29,4)):
        escape();browser_focus();open_private()
        key(code,True);device(f'mods 0 {mask} 0 0 0')
        ipc('private-test','protection','false')
        wait(lambda: 'Release all keys and modifiers' in state()['captureError'],'held modifier prevents disable')
        assert state()['captureState']['enabled'] and state()['captureState']['loaded']
        key(48)
        assert evaluate('editor.value')=='','Private modifier handoff leaked native text'
        key(code,False);device('mods 0 0 0 0 0')
        text('c');assert evaluate('editor.value')=='c',evaluate('snapshot()')
        observe('disable-waits-for-modifier-'+str(code))
        open_private()
    ipc('private-test','protection','false')
    wait(lambda: state()['captureState'] is not None and not state()['captureState']['enabled'],'saved off')
    ipc('canvas','open');wait(lambda: state()['open'] and not state()['privateSession'],'ordinary open')
    assert not item('lumaAnalyzePage').get('visible'),'Page icon visible in ordinary mode'
    text('normal')
    assert state()['query']=='normal' and not evaluate('document.hasFocus()'),state()
    observe('off-restores-focus',focus=False)
    click(70,90);wait(lambda: not state()['open'],'ordinary outside dismissal')
    browser_focus()
    gate=out/'hold-enable';gate.touch()
    ipc('private-test','protection','true')
    wait(lambda: json.loads(ipc('private-test','savedStatus'))['busy'],'enable transaction pending')
    ipc('canvas','open')
    time.sleep(.2)
    assert not state()['open'] and evaluate('document.hasFocus()'),'Enable transaction admitted ordinary focus'
    gate.unlink()
    wait(lambda: state()['privateReady'],'real protection enable',timeout=150)
    wait(lambda: state()['open'] and state()['privateSession'] and state()['inputDestination']=='luma','deferred private open after enable')
    text('enabled');observe('real-toggle-enable')
    ipc('private-test','safetyClose')
    recorded=Path(json.loads(marker.read_text())['plugin'])
    assert run(['hyprctl','plugin','unload',str(recorded)])=='ok'
    ipc('private-test','refresh')
    wait(lambda: state()['captureState'] is not None and state()['captureState']['enabled'] and not state()['captureState']['loaded'],'unavailable saved-on')
    ipc('canvas','open');time.sleep(.3)
    assert not state()['open'] and evaluate('document.hasFocus()'),'Unavailable privacy took focus'
    observe('unavailable-refuses-focusing-fallback')
    print('PASS production private input, focus, clipboard, handoff, drag, menus, picker, Escape, held keys, IME refusal, lock, unload, target loss and off', flush=True)
except BaseException:
    if shell and shell.poll() is None:
        try:
            (out/'failure.json').write_text(json.dumps({'canvas':state(),'browser':evaluate('snapshot()'),'devices':json.loads(run(['hyprctl','devices','-j'])),'item':item('commandCanvasSearch'),'menu':item('lumaFilters'),'filterButton':item('Filter · Auto'),
                'monitors':json.loads(run(['hyprctl','monitors','-j'])),'layers':json.loads(run(['hyprctl','layers','-j'])),
                'cursor':run(['hyprctl','cursorpos','-j']),'native':run(['hyprctl','luma-private','status'])},indent=2))
        except Exception:
            pass
    raise
finally:
    if ws: ws.close()
    for process in reversed(processes):
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=4)
    if original_window:
        subprocess.run(['hyprctl','eval','hl.dispatch(hl.dsp.focus({window='+json.dumps('address:'+original_window)+'}))'],env=parent,capture_output=True,timeout=5)
    if original_plugins is not None:
        final_plugins=json.loads(run(['hyprctl','plugin','list','-j'],parent))
        isolation=dict(parentPluginsUnchanged=original_plugins==final_plugins,processesStopped=all(p.poll() is not None for p in processes))
        (out/'isolation.json').write_text(json.dumps(isolation,indent=2)+'\n')
        assert all(isolation.values()), isolation
    assert manifest=={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},'Source changed during live verification'
    print('Stopped isolated processes. Evidence '+str(out),flush=True)
