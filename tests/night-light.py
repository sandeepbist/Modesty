#!/usr/bin/env python3
"""Test the native protocol with an isolated fake socket, including stream coalescing."""
import importlib.util,json,os,socket,tempfile,threading,subprocess
from pathlib import Path
spec=importlib.util.spec_from_file_location('night','scripts/night-light.py');night=importlib.util.module_from_spec(spec);spec.loader.exec_module(night)
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp)/'hypr'/'test';p.mkdir(parents=True);path=p/'.hyprsunset.sock'
 server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);server.bind(str(path));server.listen();commands=[]
 def run():
  for _ in range(5):
   c,_=server.accept();cmd=c.recv(1024).decode();commands.append(cmd)
   c.sendall(('false' if cmd=='identity get' else '3200' if cmd=='temperature' else 'ok').encode());c.close()
 thread=threading.Thread(target=run);thread.start();old=dict(os.environ);os.environ.update(XDG_RUNTIME_DIR=temp,HYPRLAND_INSTANCE_SIGNATURE='test')
 try:
  assert night.snapshot()=={'available':True,'nightLight':True,'temperature':3200}
  assert night.apply(True,1800)['temperature']==2000
  assert night.apply(False,9000)['temperature']==6500
  response=subprocess.check_output(['python3','scripts/night-light.py'],input='{"enabled":true,"temperature":3500}\n{"enabled":true,"temperature":4250}\n',text=True)
  assert json.loads(response)['temperature']==4250
 finally:os.environ.clear();os.environ.update(old)
 thread.join(timeout=3);server.close();assert commands==['identity get','temperature','temperature 2000','identity','temperature 4250'],commands
 print('PASS native Night Light snapshot, clamps, identity, coalesced final target')
