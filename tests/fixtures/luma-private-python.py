#!/usr/bin/python3
import json
import os
from pathlib import Path
import sys
import time

gate=Path(os.environ.get('MODESTY_PRIVATE_TEST_OUTPUT','/nonexistent'))/'hold-enable'
if (os.environ.get('MODESTY_PRIVATE_TEST') and len(sys.argv)>2 and
        Path(sys.argv[1]).name=='luma-capture.py' and sys.argv[2]=='enable'):
    deadline=time.monotonic()+10
    while gate.exists() and time.monotonic()<deadline:
        time.sleep(.02)

if (os.environ.get('MODESTY_PRIVATE_TEST') and len(sys.argv)>2 and
        Path(sys.argv[1]).name=='luma-assistant.py' and sys.argv[2]=='chat'):
    payload=json.loads(sys.stdin.readline())
    Path(os.environ['MODESTY_PRIVATE_TEST_OUTPUT'],'answer-request.json').write_text(json.dumps(payload,indent=2)+'\n')
    if payload.get('requestContext',{}).get('kind')=='analyze_page':
        import base64
        import importlib.util
        import io
        import urllib.request
        sys.path.insert(0,str(Path(sys.argv[1]).parent))
        spec=importlib.util.spec_from_file_location('assistant',sys.argv[1])
        assistant=importlib.util.module_from_spec(spec);spec.loader.exec_module(assistant)
        output=Path(os.environ['MODESTY_PRIVATE_TEST_OUTPUT'])
        assistant.secret=lambda provider:'isolated-fixture'
        def provider(request,**kwargs):
            assert request.full_url.startswith('https://generativelanguage.googleapis.com/')
            body=json.loads(request.data)
            parts=body['contents'][0]['parts']
            image=next(part['inlineData'] for part in parts if 'inlineData' in part)
            (output/'page-provider.png').write_bytes(base64.b64decode(image['data']))
            (output/'page-provider.json').write_text(json.dumps(body,indent=2)+'\n')
            if (output/'page-fail-once').exists():
                (output/'page-fail-once').unlink()
                raise ValueError('Fixture page provider failure')
            result={'answer':'Fixture page analyzed.'}
            chunk={'candidates':[{'content':{'parts':[{'text':json.dumps(result)}]},'finishReason':'STOP'}]}
            return io.BytesIO(b'data: '+json.dumps(chunk).encode()+b'\n')
        assistant.urlopen=provider
        urllib.request.urlopen=lambda *a,**k:(_ for _ in ()).throw(AssertionError('Unexpected network'))
        try:
            assistant.converse(payload)
        except Exception as error:
            assistant.emit(event='error',text=str(error));raise
    else:
        print(json.dumps({'event':'answer','text':'Private answer.\n\n```text\ncopy proof\n```',
                          'intent':'conversation','model':'isolated-fixture','requests':0}),flush=True)
else:
    os.execv(sys.executable,[sys.executable,*sys.argv[1:]])
