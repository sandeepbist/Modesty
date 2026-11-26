#!/usr/bin/env python3
import base64
import ctypes
from contextlib import ExitStack
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
assistant = load('assistant', ROOT/'scripts/luma-assistant.py')
window = load('window', ROOT/'scripts/luma-window.py')
TARGET = dict(address='0xabc', pid=123, **{'class':'fixture'}, title='Fixture document', stableId='one')
CONTEXT = dict(kind='analyze_page', generation=42)
PAYLOAD = dict(query='Explain this', requestContext=CONTEXT, aiEnabled=True, currentWindowAllowed=True)
STATUS = dict(protocol=1, generation=42, destination='luma')
PNG = b'\x89PNG\r\n\x1a\nfixture'


def rejects(operation):
    try:
        operation()
    except ValueError:
        return
    raise AssertionError('Expected refusal')


class Node:
    def __init__(self, role='PANEL', name='', children=(), text='', visible=True, showing=True, attrs=None, pid=123, links=None):
        self.role, self.name, self.children, self.text = role, name, list(children), text
        self.visible, self.showing, self.attrs, self.pid = visible, showing, attrs or {}, pid
        self.links=links
    def get_child_count(self): return len(self.children)
    def get_child_at_index(self, index): return self.children[index]
    def get_process_id(self): return self.pid
    def get_name(self): return self.name
    def get_role(self): return self.role
    def get_state_set(self): return self
    def contains(self, state): return {'VISIBLE':self.visible, 'SHOWING':self.showing}.get(state, False)
    def get_attributes(self): return self.attrs
    def get_interfaces(self): return (['Text'] if self.text else [])+(['Hypertext'] if self.links is not None else [])
    def get_text(self): raise AssertionError('Accessible.get_text collides with Atspi.Text.get_text')


class Text:
    @staticmethod
    def get_character_count(node): return len(node.text)
    @staticmethod
    def get_text(node, start, end):
        assert node.role != 'PASSWORD_TEXT' and node.visible and not node.attrs
        return node.text[start:end]


Atspi = SimpleNamespace(Role=SimpleNamespace(**{key:key for key in ('FRAME','WINDOW','PASSWORD_TEXT','DOCUMENT_WEB')}),
                        StateType=SimpleNamespace(VISIBLE='VISIBLE', SHOWING='SHOWING', DEFUNCT='DEFUNCT'), Text=Text,
                        Hypertext=SimpleNamespace(get_link_index=lambda node,offset:offset if offset in node.links else -1,
                            get_link=lambda node,index:node.links.get(index)),
                        Hyperlink=SimpleNamespace(get_n_anchors=lambda link:1,get_object=lambda link,index:link))
def tree(documents=None, frames=None):
    if documents is None:
        documents = [Node('DOCUMENT_WEB', children=[Node(text='Visible explanation'),
            Node(text='BELOW-FOLD marker', showing=False), Node('PASSWORD_TEXT', text='SECRET'),
            Node(text='HIDDEN', visible=False), Node(text='PROTECTED', attrs={'protected':'true'})])]
    if frames is None:
        frames = [Node('FRAME', TARGET['title'], documents)]
    return Node(children=[Node(children=frames), Node(children=[Node('FRAME',TARGET['title'],[Node('DOCUMENT_WEB',text='OTHER APP')])],pid=999)])

result = window.document_text(TARGET, tree(), Atspi)
assert result['text'] == 'Visible explanation\nBELOW-FOLD marker' and not result['truncated'], result
aggregate = Node('DOCUMENT_WEB', text='Question above and answer BELOW-FOLD', children=[Node(text='Link label')])
result = window.document_text(TARGET, tree(documents=[aggregate]), Atspi)
assert 'Question above and answer BELOW-FOLD' in result['text'] and 'Link label' in result['text']
aggregate = Node('DOCUMENT_WEB', text='PUBLIC AND SECRET', children=[Node(text='PUBLIC'),Node('PASSWORD_TEXT',text='SECRET')])
result = window.document_text(TARGET, tree(documents=[aggregate]), Atspi)
assert result['text']=='PUBLIC'
embedded = Node('DOCUMENT_WEB', text='Before \ufffc after', children=[Node(text='inline link')])
rejects(lambda:window.document_text(TARGET,tree(documents=[embedded]),Atspi))
swapped=Node('DOCUMENT_WEB',text='Question: \ufffc Answer: \ufffc',children=[Node(text='ANSWER 42'),Node(text='QUESTION 6*7')])
rejects(lambda:window.document_text(TARGET,tree(documents=[swapped]),Atspi))
with patch.object(window.subprocess,'run',side_effect=lambda *a,**k:window.document_text(TARGET,tree(documents=[swapped]),Atspi)):
    assert window.read_document(TARGET)[0] is None
before,link,after=Node(text='Before '),Node(text='inline link'),Node(text=' after')
embedded=Node('DOCUMENT_WEB',text='Before \ufffc after',children=[before,link,after],links={7:link})
assert window.document_text(TARGET,tree(documents=[embedded]),Atspi)['text']=='Before inline link after'
embedded.links={7:Node(text='OUTSIDE DOCUMENT')}
rejects(lambda:window.document_text(TARGET,tree(documents=[embedded]),Atspi))
for attrs in ({'aria-hidden':'true'},{'protected':'true'}):
    hidden=Node(children=[Node('DOCUMENT_WEB',text='SECRET')],attrs=attrs)
    rejects(lambda:window.document_text(TARGET,tree(documents=[hidden]),Atspi))
    hidden_app=tree();hidden_app.children[0].attrs=attrs
    rejects(lambda:window.document_text(TARGET,hidden_app,Atspi))
assert window.document_text(TARGET, tree(documents=[Node('DOCUMENT_WEB',text='Aggregate only',children=[Node()])]), Atspi)['text']=='Aggregate only'
rejects(lambda:window.document_text(TARGET,tree(documents=[Node('DOCUMENT_WEB',text='one'),Node('DOCUMENT_WEB',text='two')]),Atspi))
rejects(lambda:window.document_text(TARGET,tree(frames=[Node('FRAME',TARGET['title']),Node('FRAME',TARGET['title'])]),Atspi))
rejects(lambda:window.document_text(dict(TARGET,pid=55),tree(),Atspi))
result = window.document_text(TARGET,tree(documents=[Node('DOCUMENT_WEB',text='active'),Node('DOCUMENT_WEB',text='inactive',showing=False)]),Atspi)
assert result['text']=='active'
with patch.object(window,'MAX_TEXT',8):
    result=window.document_text(TARGET,tree(),Atspi)
    assert result['truncated'] and len(result['text'])==8
with patch.object(window,'MAX_NODES',7):
    result=window.document_text(TARGET,tree(),Atspi)
    assert result['truncated'] and 'SECRET' not in result['text']
print('PASS scoped PID/frame/document, below-fold text, hidden/password/protected exclusions and caps')


def metadata(command, **kwargs):
    if command[1:]==['clients','-j']: return json.dumps([TARGET])
    if command[1:]==['activewindow','-j']: return json.dumps(TARGET)
    if command[1:]==['luma-private','status']: return json.dumps(STATUS)
    return 'capture-id'

with patch.object(window.subprocess,'check_output',side_effect=metadata):
    window.validate_target(TARGET)
    for field, value in [('address','0xnew'),('pid',321),('class','other'),('title','changed'),('stableId','replacement')]:
        rejects(lambda:window.validate_target(dict(TARGET,**{field:value})))
    with patch.object(window.subprocess,'check_output',side_effect=lambda cmd,**kw:json.dumps([TARGET,TARGET]) if cmd[1]=='clients' else metadata(cmd,**kw)):
        rejects(lambda:window.validate_target(TARGET))
for status in ({},dict(STATUS,protocol=2),dict(STATUS,generation=41),dict(STATUS,destination='closed')):
    with patch.object(window.subprocess,'check_output',return_value=json.dumps(status)):
        rejects(lambda:window.native_private(42))
print('PASS target replacement, duplicate and native protocol/generation/privacy refusal')

for output in ('{}','[]',json.dumps(dict(text='x',truncated=False,characters=99,nodes=1)), 'x'*600001):
    with patch.object(window.subprocess,'run',return_value=subprocess.CompletedProcess([],0,output,'')):
        assert window.read_document(TARGET)[0] is None
with patch.object(window.subprocess,'run',side_effect=subprocess.TimeoutExpired([],3)):
    assert 'timed out' in window.read_document(TARGET)[1]
with tempfile.TemporaryDirectory() as temporary:
    folder=Path(temporary)
    cache=folder/'modesty/window-context';cache.mkdir(parents=True)
    source=ROOT/'scripts/window-toplevel.c'
    (cache/('toplevel-'+hashlib.sha256(source.read_bytes()).hexdigest()[:16])).touch()
    def grim(command, **kwargs):
        assert command[:2]==['grim','-T'] and command[2]=='capture-id'
        Path(command[-1]).write_bytes(PNG)
    with patch.dict(os.environ,XDG_CACHE_HOME=temporary),patch.object(window.subprocess,'run',side_effect=grim),patch.object(window.subprocess,'check_output',side_effect=metadata),patch.object(window,'read_document',return_value=(None,'Unsupported fixture')):
        result=window.capture(TARGET,True,42)
        assert result['scope']=='visible_window' and result['fallbackReason']=='Unsupported fixture'
        Path(result['path']).unlink()
        with patch.object(window,'validate_target',side_effect=[None,None,ValueError('Target gone')]):
            rejects(lambda:window.capture(TARGET,True,42))
        assert not list(cache.glob('*.png'))
        with patch.object(window,'native_private',side_effect=[None,None,ValueError('Revoked after screenshot')]),patch.object(window,'read_document') as read:
            rejects(lambda:window.capture(TARGET,True,42))
            assert not read.called and not list(cache.glob('*.png'))
        ids=iter(['capture-id','replacement-id'])
        def replaced(command,**kwargs):
            return next(ids) if command[0]!='hyprctl' else metadata(command,**kwargs)
        with patch.object(window.subprocess,'check_output',side_effect=replaced):
            rejects(lambda:window.capture(TARGET,True,42))
        assert not list(cache.glob('*.png'))
print('PASS bounded malformed/timeout fallback, exact grim target and failure cleanup')

with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
    folder=Path(temporary)
    events=[];requests=[];order=[]
    stack.enter_context(patch.object(assistant,'emit',side_effect=lambda **v:events.append(v)))
    stack.enter_context(patch.object(assistant,'secret',return_value='fixture-only'))
    stack.enter_context(patch.object(assistant,'check_cooldown'))
    stack.enter_context(patch.object(assistant,'record_usage'))
    stack.enter_context(patch.object(assistant.subprocess,'check_output',side_effect=metadata))
    for name in ('route','answer_cache_path','cached_answer','private_write','native_system_action'):
        stack.enter_context(patch.object(assistant,name,side_effect=AssertionError(name+' reached')))
    stack.enter_context(patch.object(assistant.canvas,'knowledge_adapter',side_effect=AssertionError('Knowledge reached')))
    stack.enter_context(patch.object(assistant.tasks,'commands',side_effect=AssertionError('Local shortcut reached')))
    def evidence(selected, page=False, generation=None):
        assert selected==TARGET and page and generation==42
        order.append('capture')
        return [{'text':'BELOW-FOLD fixture evidence'},{'inlineData':{'mimeType':'image/png','data':base64.b64encode(PNG).decode()}}]
    capture=stack.enter_context(patch.object(assistant,'window_context',side_effect=evidence))
    result={'answer':'Explained fixture'}
    def provider(request,**kwargs):
        order.append('provider');requests.append(json.loads(request.data))
        return io.BytesIO(b'data: '+json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(result)}]},'finishReason':'STOP'}]}).encode()+b'\n')
    network=stack.enter_context(patch.object(assistant,'urlopen',side_effect=provider))
    for changes in ({'preview':True},{'currentWindowAllowed':False},{'aiEnabled':False},{'requestContext':None},
                    {'requestContext':{}},{'requestContext':dict(CONTEXT,kind='other')},{'requestContext':dict(CONTEXT,generation=True)}):
        rejects(lambda:assistant.converse(dict(PAYLOAD,**changes)))
    assert not capture.called and not network.called
    malicious=dict(PAYLOAD,history=[{'role':'user','text':'HISTORY SECRET'}],attachments=['ATTACHMENT SECRET'],sharedText='CLIPBOARD SECRET',context={'text':'DESKTOP SECRET'},pendingTask='TASK SECRET')
    assistant.converse(malicious)
    assert order==['capture','provider'] and len(requests)==1
    assert not any(secret in json.dumps(requests) for secret in ('HISTORY SECRET','ATTACHMENT SECRET','CLIPBOARD SECRET','DESKTOP SECRET','TASK SECRET'))
    assert events[-1]['actions']==[] and events[-1]['router']=='analyze_page'
    for forbidden in ('actions','system_tools','read_tools','search_queries','file_queries'):
        result={'answer':'Unsafe output',forbidden:[{'name':'open_app'}]}
        rejects(lambda:assistant.converse(PAYLOAD))
        assert not any(e.get('event')=='text' for e in events)
    network.reset_mock()
    with patch.object(assistant,'window_context',side_effect=ValueError('capture failed')):
        rejects(lambda:assistant.converse(PAYLOAD))
    assert not network.called
    with patch.object(assistant,'page_private',side_effect=[None,ValueError('privacy lost')]):
        rejects(lambda:assistant.converse(PAYLOAD))
    assert not network.called
print('PASS context/permission/preview denial, deterministic source, cache/router/read isolation, action rejection and pre-provider privacy recheck')

with tempfile.TemporaryDirectory() as temporary:
    folder=Path(temporary);image=folder/'fixture.png';image.write_bytes(PNG);events=[]
    result=dict(path=str(image),scope='document_text',text='REQUEST-LOCAL-SECRET',app='fixture',truncated=False)
    class Process:
        pid=0;returncode=0
        def communicate(self,*args,**kwargs):return json.dumps(result),''
        def poll(self):return 0
        def wait(self,**kwargs):return 0
    with patch.object(assistant.subprocess,'Popen',return_value=Process()),patch.object(assistant.os,'killpg'),patch.object(assistant,'emit',side_effect=lambda **v:events.append(v)):
        parts=assistant.window_context(TARGET,True,42)
    assert 'REQUEST-LOCAL-SECRET' in json.dumps(parts) and 'REQUEST-LOCAL-SECRET' not in json.dumps(events)
    assert not image.exists()
    image.write_bytes(PNG)
    with patch.object(assistant.subprocess,'Popen',return_value=Process()),patch.object(assistant.os,'killpg'),patch.object(assistant,'emit',side_effect=ValueError('event failed')):
        rejects(lambda:assistant.window_context(TARGET,True,42))
    assert not image.exists()
print('PASS text removed before UI event and PNG cleanup on success/failure')

history=assistant.conversation_state({'active':'page','threads':[{'id':'page','messages':[
    {'role':'user','text':'Analyze fixture','requestKind':'analyze_page'},
    {'role':'assistant','text':'Failed','failed':True}]}]})
assert history['messages'][0]['requestKind']=='analyze_page'
assert 'requestKind' not in assistant.clean_messages([{'role':'user','text':'Chat','requestKind':'other'}])[0]
print('PASS page request identity survives saved conversation validation')

with tempfile.TemporaryDirectory() as temporary:
    pidfile=Path(temporary)/'descendant.pid'
    libc=ctypes.CDLL(None)
    previous=ctypes.c_int()
    assert libc.prctl(37,ctypes.byref(previous),0,0,0)==0
    assert libc.prctl(36,1,0,0,0)==0
    real_popen=subprocess.Popen
    child=None
    try:
        program="import os,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);open("+repr(str(pidfile))+",'w').write(str(os.getpid()));time.sleep(60)"
        leader="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',"+repr(program)+"]);time.sleep(.1)"
        def process(*args,**kwargs):
            value=real_popen([sys.executable,'-c',leader],**kwargs)
            communicate=value.communicate
            value.communicate=lambda *a,**k:communicate(*a,**dict(k,timeout=min(k.get('timeout',1),.3)))
            return value
        with patch.object(assistant.subprocess,'Popen',side_effect=process):
            try:assistant.window_context(TARGET,True,42)
            except subprocess.TimeoutExpired:pass
            else:raise AssertionError('Expected capture timeout')
        child=int(pidfile.read_text())
        deadline=time.monotonic()+2
        stopped,status=os.waitpid(child,os.WNOHANG)
        while not stopped and time.monotonic()<deadline:
            time.sleep(.02)
            stopped,status=os.waitpid(child,os.WNOHANG)
        assert stopped==child,'Capture descendant survived timeout cleanup'
        child=None
        assert os.WIFSIGNALED(status) and os.WTERMSIG(status)==signal.SIGKILL
    finally:
        if child:
            os.kill(child,signal.SIGKILL);os.waitpid(child,0)
        assert libc.prctl(36,previous.value,0,0,0)==0
print('PASS timeout kills SIGTERM-resistant descendant after capture leader exits')
