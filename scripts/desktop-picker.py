#!/usr/bin/env python3
"""Clipboard and emoji pickers using the existing desktop utilities."""
import os
from pathlib import Path
import subprocess
import sys

def main():
    mode=sys.argv[1] if len(sys.argv)>1 else 'clipboard'
    config=Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'modesty'
    if mode=='emoji':
        items=(config/'emoji-list.txt').read_bytes()
    else:
        items=subprocess.check_output(['cliphist','list'])
    prompt='Emoji' if mode=='emoji' else 'Delete clipboard item' if mode=='delete' else 'Clipboard'
    selected=subprocess.run(['fuzzel','--dmenu','--prompt='+prompt+'  '],input=items,stdout=subprocess.PIPE)
    if selected.returncode or not selected.stdout.strip():return
    if mode=='delete':subprocess.run(['cliphist','delete'],input=selected.stdout,check=True)
    else:
        content=selected.stdout.split()[0] if mode=='emoji' else subprocess.check_output(['cliphist','decode'],input=selected.stdout)
        subprocess.run(['wl-copy'],input=content,check=True)

if __name__=='__main__':
    try:main()
    except (OSError,subprocess.CalledProcessError) as error:
        subprocess.run(['notify-send','Picker unavailable',str(error)])
        sys.exit(1)
