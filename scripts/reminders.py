#!/usr/bin/env python3
"""Private, atomic storage for calendar reminders. Scheduling stays in the shell."""
import json,os,re,sys,tempfile
import math
from datetime import date
from pathlib import Path
folder=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'modesty'
path=folder/'reminders.json'
def day(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('Invalid date')
    date.fromisoformat(value)
def validate(data):
    if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('items'),list) or len(data['items'])>256:raise ValueError('Invalid reminder file')
    seen=set()
    for r in data['items']:
        if not isinstance(r,dict) or not isinstance(r.get('id'),str) or not re.fullmatch(r'[a-z0-9-]{1,80}',r['id']) or r['id'] in seen:raise ValueError('Invalid reminder id')
        seen.add(r['id']);day(r.get('date'))
        if not isinstance(r.get('title'),str) or not r['title'].strip() or len(r['title'])>160:raise ValueError('Invalid reminder title')
        if not isinstance(r.get('time'),str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',r['time']):raise ValueError('Invalid reminder time')
        if type(r.get('lead')) is not int or not 0<=r['lead']<=30 or type(r.get('count')) is not int or not 1<=r['count']<=r['lead']+1:raise ValueError('Invalid reminder schedule')
        if type(r.get('done')) is not bool or not isinstance(r.get('delivered'),list) or len(r['delivered'])>31:raise ValueError('Invalid reminder state')
        if 'at' in r and (type(r['at']) not in (int,float) or not math.isfinite(r['at']) or not 0<r['at']<253402300799000 or r['lead']!=0 or r['count']!=1):raise ValueError('Invalid exact reminder time')
        for d in r['delivered']:day(d)
    return data
try:
    if len(sys.argv)==1:
        data=validate(json.loads(path.read_text())) if path.exists() else {'version':1,'items':[]}
        print(json.dumps({'ok':True,**data}))
    else:
        data=validate(json.loads(sys.argv[1]));folder.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',dir=folder,delete=False,prefix='.reminders-') as f:
            json.dump(data,f,ensure_ascii=False);f.flush();os.fsync(f.fileno());name=f.name
        os.replace(name,path)
        print(json.dumps({'ok':True}))
except (ValueError,TypeError,OSError) as error:
    print(json.dumps({'ok':False,'error':str(error)}));sys.exit(1)
