#!/usr/bin/env python3
"""Short-lived slider bridge to Hyprsunset's native IPC; no per-step subprocesses.
Protocol: https://github.com/hyprwm/hyprsunset/blob/main/src/IPCSocket.cpp
"""
import json, os, socket, subprocess, sys, time
from pathlib import Path

def request(command):
    path = Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))/'hypr'
    if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'): path /= os.environ['HYPRLAND_INSTANCE_SIGNATURE']
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.settimeout(2);client.connect(str(path/'.hyprsunset.sock'))
        client.sendall(command.encode());return client.recv(4096).decode().strip()

def snapshot():
    try: return {'available':True,'nightLight':request('identity get')=='false','temperature':int(request('temperature'))}
    except (OSError,ValueError): return {'available':False,'nightLight':False}

def apply(enabled, temperature):
    temperature = max(2000,min(6500,int(temperature)))
    command = f'temperature {temperature}' if enabled else 'identity'
    try: response=request(command)
    except (FileNotFoundError,ConnectionRefusedError):
        if not enabled:return {'ok':True,'nightLight':False,'temperature':temperature}
        subprocess.Popen(['hyprsunset','--temperature',str(temperature)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        for _ in range(20):
            time.sleep(.1)
            try: response=request(command);break
            except (FileNotFoundError,ConnectionRefusedError):pass
        else:raise RuntimeError('Night Light could not start')
    if response!='ok':raise RuntimeError(response or 'No response from Night Light')
    return {'ok':True,'nightLight':enabled,'temperature':temperature}

def serve(fd=0):
    pending=b''
    while True:
        chunk=os.read(fd,4096)
        if not chunk:return
        pending+=chunk;lines=pending.split(b'\n');pending=lines.pop()
        if not lines:continue
        try:
            data=json.loads(lines[-1]);result=apply(bool(data['enabled']),data['temperature'])
        except Exception as error:result={'ok':False,'error':str(error)}
        print(json.dumps(result),flush=True)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='snapshot':print(json.dumps(snapshot()),flush=True)
    elif os.environ.get('MODESTY_PREVIEW')!='1':serve()
