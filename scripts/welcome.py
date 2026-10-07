#!/usr/bin/env python3
"""Return a welcome once per compositor session, never on ordinary shell reloads."""
import json,os,re
from pathlib import Path
root=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))
key=re.sub(r'[^A-Za-z0-9_.-]','_',os.environ.get('HYPRLAND_INSTANCE_SIGNATURE','desktop'))
marker=root/('modesty-welcome-'+key)
try:
 fd=os.open(marker,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd);first=True
except FileExistsError:first=False
print(json.dumps({'first':first,'message':'Welcome'}),flush=True)
