#!/usr/bin/env python3
"""Store the validated QML grid document with an atomic rename."""
import json, os, sys, tempfile
from pathlib import Path
if __name__ == '__main__':
    data=json.loads(sys.argv[1])
    if not isinstance(data,dict) or not isinstance(data.get('items'),list) or len(data['items'])>14 or not 5<=data.get('columns',0)<=9:
        raise ValueError('Invalid layout')
    directory=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'modesty'
    directory.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=directory,delete=False,prefix='.layout-') as f:
        json.dump(data,f); name=f.name
    os.replace(name,directory/'control-layout.json')
