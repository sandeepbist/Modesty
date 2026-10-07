#!/usr/bin/env python3
"""Apply additional Modesty shortcuts without replacing existing Hyprland binds."""
import json,os,re,subprocess,sys
from pathlib import Path
ACTIONS=('reminder','focus','focuspause','recorder','recordstop','recordpause','launcher','canvas','settings','quicksettings','media','calendar','themes','wallpapers','wifi','bluetooth','display','sound','notifhistory','power','appearance','awake','peace','nightlight','lock','playpause','next','previous')
STATE=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'modesty'/'bindings.json'
SCRIPT=Path(__file__).resolve().parents[1]/'shell.qml'
MODS={'SUPER':64,'CTRL':4,'ALT':8,'SHIFT':1}

def normalize(chord):
    parts=[x.strip() for x in chord.split('+')]
    if not chord.strip():return '',0,''
    if len(parts)<2 or any(x.upper() not in MODS for x in parts[:-1]):raise ValueError('Use modifiers and a key, for example SUPER + ALT + T')
    key=parts[-1]
    if not re.fullmatch(r'[A-Za-z0-9_]+',key):raise ValueError('Use a key name such as T, F8, comma or space')
    mods=set(x.upper() for x in parts[:-1]);mask=sum(MODS[x] for x in mods)
    return ' + '.join([m for m in MODS if m in mods]+[key]),mask,key

def run(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=5)
    if p.returncode:raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout

def apply(data):
    if os.environ.get('MODESTY_PREVIEW')=='1':raise ValueError('Shortcuts cannot be applied in preview')
    current=json.loads(run(['hyprctl','-j','binds']));normalized={};seen=set()
    for action,chord in data.items():
        if action not in ACTIONS:raise ValueError('Unknown shortcut action')
        chord,mask,key=normalize(chord)
        if not chord:continue
        identity=(mask,key.lower())
        if identity in seen:raise ValueError(chord+' is assigned more than once')
        seen.add(identity)
        if any(b['modmask']==mask and b['key'].lower()==key.lower() and not b.get('description','').startswith('Modesty custom:') for b in current):raise ValueError(chord+' is already used by your desktop. Choose another combination.')
        normalized[action]=chord
    lines=['if _modesty_custom_binds then for _,b in ipairs(_modesty_custom_binds) do pcall(function() b:unbind() end) end end','_modesty_custom_binds = {}']
    for action,chord in normalized.items():
        command='quickshell ipc -p '+str(SCRIPT)+' call island action '+action
        lines.append('_modesty_custom_binds[#_modesty_custom_binds+1] = hl.bind('+json.dumps(chord)+',hl.dsp.exec_cmd('+json.dumps(command)+'),{description='+json.dumps('Modesty custom:'+action)+'})')
    response=run(['hyprctl','eval','\n'.join(lines)])
    if 'error' in response.lower():raise RuntimeError(response)
    STATE.parent.mkdir(parents=True,exist_ok=True);temp=STATE.with_suffix('.tmp');temp.write_text(json.dumps(normalized));temp.replace(STATE)
    return normalized
def clear_live():
    run(['hyprctl','eval','if _modesty_custom_binds then for _,b in ipairs(_modesty_custom_binds) do pcall(function() b:unbind() end) end end; _modesty_custom_binds = {}'])

if __name__=='__main__':
    try:
        if len(sys.argv)>1 and sys.argv[1]=="--clear-live":
            clear_live();print(json.dumps({"ok":True}));sys.exit(0)
        data=json.loads(sys.argv[1]) if len(sys.argv)>1 else json.loads(STATE.read_text()) if STATE.exists() else {}
        # Nothing to restore on a first launch; avoid touching the compositor.
        result=apply(data) if data or len(sys.argv)>1 else {}
        print(json.dumps({'ok':True,'bindings':result}),flush=True)
    except Exception as e:print(json.dumps({'ok':False,'error':str(e)}),flush=True);sys.exit(1)
