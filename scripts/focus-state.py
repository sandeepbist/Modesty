#!/usr/bin/env python3
"""Persist timer transitions only; countdown ticks never write to disk."""
import json, os, sys, tempfile
from pathlib import Path
folder=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'modesty'
path=folder/'focus.json'
if len(sys.argv)==1:
    try: data=json.loads(path.read_text())
    except (OSError,ValueError): data={}
    print(json.dumps(data))
else:
    data=json.loads(sys.argv[1])
    if data.get('phase') not in ('idle','running','paused','finished') or data.get('kind') not in ('focus','break'):
        raise ValueError('Invalid timer state')
    if not all(isinstance(data.get(k),(float,int)) and 0<=data[k]<=limit for k,limit in [('duration',7200),('remaining',7200),('deadline',1e13)]):
        raise ValueError('Invalid timer duration')
    folder.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=folder,delete=False,prefix='.focus-') as f:
        json.dump(data,f);name=f.name
    os.replace(name,path)
