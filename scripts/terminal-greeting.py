#!/usr/bin/env python3
import colorsys
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
from terminal_art import catalogue, eligible


def ascii_art(source,width,mode,state):
    """Cache ANSI ASCII; glyphs remain selectable terminal text."""
    from PIL import Image
    theme={}
    try:theme=json.loads((state/'matugen/input.json').read_text())['colors']
    except (OSError,ValueError,KeyError):pass
    def rgb(role,fallback):
        value=theme.get(role,{}).get('default',{}).get('color',fallback).lstrip('#')
        return tuple(int(value[i:i+2],16) for i in (0,2,4))
    background=rgb('surface','#101318')
    light=sum(background)>500
    tones=[rgb('outline','#8b93a5'),rgb('primary','#91b9ff'),rgb('secondary','#d4a0ed'),rgb('on_surface','#e6e8ef')]
    key=hashlib.sha256((str(source)+str(source.stat().st_mtime_ns)+str(width)+mode+str(tones)+str(light)+'text-v5').encode()).hexdigest()[:20]
    cache=Path(os.environ.get('XDG_CACHE_HOME') or Path.home()/'.cache')/'modesty/terminal-art'
    cache.mkdir(parents=True,exist_ok=True)
    target=cache/(key+'.ansi')
    if target.exists():return target
    with Image.open(source) as original:
        height=max(8,round(width*original.height/original.width*.5))
        samples=original.convert('RGB').resize((width,height),Image.Resampling.LANCZOS)
    palette_mode=mode=='theme'
    result=subprocess.run(['chafa','--format=symbols','--symbols=ascii',
        '--colors=none','--fg-only',
        '--size='+str(width)+'x'+str(height),'--font-ratio=1/2','--scale=max',
        '--work=9','--polite=on','--animate=off','--optimize=0',
        '--fg=white','--bg=black',str(source)],
        capture_output=True,text=True,timeout=4,check=True)
    plain=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',result.stdout)
    rows=[]
    for y,line in enumerate(plain.splitlines()[:height]):
        ink=[];previous=None
        for x,char in enumerate(line[:width]):
            if char==' ':ink.append(char);continue
            if palette_mode:fg=tones[1]
            else:
                r,g,b=samples.getpixel((x,y))
                hue,saturation,value=colorsys.rgb_to_hsv(r/255,g/255,b/255)
                value=min(value,.62) if light else max(value,.8)
                fg=tuple(round(c*255) for c in colorsys.hsv_to_rgb(hue,saturation*.8,value))
            if fg!=previous:
                ink.append('\033[38;2;'+';'.join(map(str,fg))+'m');previous=fg
            ink.append(char)
        rows.append(''.join(ink)+'\033[0m')
    output='\n'.join(rows)+'\n'
    temporary=target.with_name(target.name+'.'+str(os.getpid())+'.tmp')
    temporary.write_text(output);temporary.replace(target)
    # Bound stale sizes/palettes without a background cleanup process.
    for old in sorted(cache.glob('*.ansi'),key=lambda p:p.stat().st_mtime,reverse=True)[36:]:
        old.unlink(missing_ok=True)
    return target


def main():
    if not sys.stdout.isatty() or os.environ.get('SSH_CONNECTION') or os.environ.get('TMUX'):
        return
    if not shutil.which('fastfetch'):
        return
    state=Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'modesty'
    try:preferences=json.loads((state/'preferences.json').read_text())
    except (OSError,ValueError):preferences={}
    if not preferences.get('terminalGreeting',True):return
    config=Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')
    images=eligible(catalogue(),preferences)
    image_mode=preferences.get('terminalArtFormat','image')=='image'
    terminal=os.environ.get('TERM','')
    kitty=terminal=='xterm-kitty'
    if not images or (not image_mode and not shutil.which('chafa')) or not (terminal.startswith('foot') or kitty):
        if preferences.get('terminalArtMinimal',False):return
        subprocess.run(['fastfetch','--config',str(config/'fastfetch/config.jsonc'),'--logo','none'],timeout=5)
        return
    state.mkdir(parents=True,exist_ok=True)
    with (state/'terminal-greeting.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        history=state/'terminal-greeting.json'
        try:saved=json.loads(history.read_text())
        except (OSError,ValueError):saved={}
        available={item['id']:item for item in images}
        pool=sorted(available)
        remaining=[name for name in saved.get('remaining',[]) if name in available] if saved.get('pool')==pool else []
        if not remaining:
            remaining=list(available);random.shuffle(remaining)
            if len(remaining)>1 and remaining[-1]==saved.get('last'):
                remaining[0],remaining[-1]=remaining[-1],remaining[0]
        chosen=available[remaining.pop()]
        temporary=history.with_suffix('.tmp')
        temporary.write_text(json.dumps({'last':chosen['id'],'remaining':remaining,'pool':pool}));temporary.replace(history)
    columns,lines=shutil.get_terminal_size((80,24))
    minimal=preferences.get('terminalArtMinimal',False)
    desired=max(24,min(60,int(preferences.get('terminalArtSize',36))))
    if not image_mode:desired=round(desired*1.7)
    side=not minimal and columns>=desired+40
    budget=columns-40 if side else columns-6
    image_width=min(desired,max(12,budget))
    from PIL import Image
    art=Path(chosen['image' if image_mode else 'ascii'])
    with Image.open(art) as source:
        ratio=source.height/source.width*.5
    max_height=max(8,lines-(4 if side or minimal else 14))
    image_width=min(image_width,max(12,int(max_height/ratio)))
    image_height=max(1,round(image_width*ratio))
    if not image_mode:art=ascii_art(art,image_width,preferences.get('terminalArtMode','original'),state)
    args=['fastfetch','--config',str(config/'fastfetch/config.jsonc'),
          '--pipe','false','--logo-type',('kitty-direct' if kitty else 'sixel') if image_mode else 'file-raw','--logo',str(art),
          '--color-keys','blue','--color-title','blue','--logo-padding-right','4','--logo-position','left' if side else 'top']
    if image_mode:args+=['--logo-width',str(image_width),'--logo-height',str(image_height)]
    if minimal:args+=['--structure','break']
    print(flush=True)
    result=subprocess.run(args,timeout=7)
    if result.returncode:
        if not minimal:subprocess.run(['fastfetch','--config',str(config/'fastfetch/config.jsonc'),'--logo','none'],timeout=5)
    print(flush=True)


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,subprocess.TimeoutExpired,subprocess.CalledProcessError):
        # Startup decoration must never prevent the shell prompt appearing.
        pass
