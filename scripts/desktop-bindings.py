#!/usr/bin/env python3
"""Edit registered native Hyprland actions and persist only their key overrides."""
import json, os, re, sys
from pathlib import Path
from bindings import MODS, run
DIRECTORY=Path(os.environ.get('XDG_STATE_HOME',Path.home()/'.local/state'))/'modesty'
STATE=DIRECTORY/'desktop-bindings.json'
LIVE=DIRECTORY/'desktop-bindings-live.json'


def normalize(chord):
    if not chord.strip():return '',0,''
    parts=[p.strip() for p in chord.split('+')]
    if any(p.upper() not in MODS for p in parts[:-1]):raise ValueError('Use SUPER, CTRL, ALT or SHIFT, followed by a key.')
    key=parts[-1]
    if not re.fullmatch(r'[A-Za-z0-9_]+|mouse:\d+|code:\d+',key):raise ValueError('Use a key name such as M, Print, space or mouse:272.')
    mods={p.upper() for p in parts[:-1]}
    return ' + '.join([m for m in MODS if m in mods]+[key]),sum(MODS[m] for m in mods),key


def evaluate(code):
    result=run(['hyprctl','eval',code])
    if result.strip()!='ok':raise RuntimeError(result.strip())


def main():
    evaluate('assert(_modesty_desktop_bindings, "Reload Hyprland to load your shortcuts"):write()')
    rows=json.loads(LIVE.read_text())
    if len(sys.argv)>1:
        request=json.loads(sys.argv[1]);row=next((r for r in rows if r['id']==request.get('id')),None)
        if not row:raise ValueError('This shortcut is no longer available. Refresh the list.')
        chord,mask,key=normalize(request.get('chord',''))
        if chord and row['mouse'] and not (key.startswith('mouse:') or len(key)==1):raise ValueError('Use a mouse button or single key for this mouse action.')
        current=json.loads(run(['hyprctl','-j','binds']))
        for b in current:
            if chord and b.get('modmask')==mask and b.get('key','').lower()==key.lower() and b.get('description')!='Modesty desktop:'+row['id']:
                raise ValueError(chord+' is already assigned. Change or clear that shortcut first.')
        data=json.loads(STATE.read_text()) if STATE.exists() else {}
        if chord==row['original']:data.pop(row['id'],None)
        else:data[row['id']]=chord
        temp=STATE.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False))
        # All strings go through JSON quoting directly to Lua, never a shell.
        args=json.dumps(row['id'],ensure_ascii=False)+','+json.dumps(chord,ensure_ascii=False)
        evaluate('_modesty_desktop_bindings:set('+args+')')
        try:temp.replace(STATE)
        except OSError:
            evaluate('_modesty_desktop_bindings:set('+json.dumps(row['id'])+','+json.dumps(row['chord'])+')')
            raise
        rows=json.loads(LIVE.read_text())
    print(json.dumps({'ok':True,'desktopBindings':rows}),flush=True)


if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'ok':False,'error':str(e)}),flush=True);sys.exit(1)
