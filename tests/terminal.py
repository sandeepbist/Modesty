#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from unittest.mock import patch
from types import SimpleNamespace
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import appearance
spec=importlib.util.spec_from_file_location('greeting',ROOT/'scripts/terminal-greeting.py')
greeting=importlib.util.module_from_spec(spec);spec.loader.exec_module(greeting)

with tempfile.TemporaryDirectory(prefix='modesty-terminal-check-') as temporary:
    directory=Path(temporary);config=directory/'config with spaces';state=directory/'state'
    kitty=config/'kitty';kitty.mkdir(parents=True)
    profile=kitty/'modesty.conf'
    profile.write_bytes((ROOT/'setup/config/kitty/modesty.conf').read_bytes())
    (kitty/"modesty-effects.conf").write_bytes((ROOT/"setup/config/kitty/modesty-effects.conf").read_bytes())
    original=kitty/'kitty.conf';original.write_text('font_size 17\n')
    real_run=subprocess.run
    real_iterdir=Path.iterdir
    def isolated_iterdir(path):
        return iter(()) if path==Path('/proc') else real_iterdir(path)
    def isolated_run(command,**kwargs):
        if command[0]=='matugen':return real_run(command,**kwargs)
        assert command[0] in ('hyprctl','gsettings'),command
        return subprocess.CompletedProcess(command,0,'','')
    for mode in ('dark','light'):
        colors=dict(accent='#bdc7dd' if mode=='dark' else '#365f9d',accentText='#172033' if mode=='dark' else '#ffffff',
            bg='#101013' if mode=='dark' else '#f5f6fa',surface='#18181c' if mode=='dark' else '#e9edf5',
            text='#f2f2f4' if mode=='dark' else '#242a38',subtext='#888888',green='#9bdc91',yellow='#edca80',red='#f07886')
        with patch.dict(os.environ,XDG_CONFIG_HOME=str(config)),patch.object(appearance.subprocess,'run',side_effect=isolated_run),patch.object(Path,'iterdir',isolated_iterdir):
            appearance.apply(dict(paletteName='midnight',mode=mode,colors=colors,targets={'foot':True}),state)
        generated=(kitty/'modesty-generated.conf').read_text()
        assert 'cursor '+colors['accent'] in generated and 'cursor_text_color '+colors['accentText'] in generated
        assert 'background '+colors['bg'] in generated and 'color15 ' in generated
        assert original.read_text()=='font_size 17\n'
        assert len([line for line in profile.read_text().splitlines() if line.startswith('include ') and 'modesty-generated.conf' in line])==1 and 'include modesty-effects.conf' in profile.read_text()
        if shutil.which('kitty'):
            code=('import json; from kitty.config import load_config; bad=[]; p=load_config('+repr(str(profile))+',accumulate_bad_lines=bad); '
                'print(json.dumps([len(bad),p.cursor_trail,p.cursor_trail_decay,p.cursor_trail_start_threshold,p.cursor_blink_interval[0],p.custom_shaders]))')
            result=subprocess.run(['kitty','+runpy',code],check=True,timeout=10,capture_output=True,text=True)
            assert json.loads(result.stdout)==[0,1,[0.06,0.14],[2,2],0,[]]
        with patch.dict(os.environ,XDG_CONFIG_HOME=str(config)),patch.object(appearance.subprocess,'run',side_effect=isolated_run),patch.object(Path,'iterdir',isolated_iterdir):
            appearance.apply(dict(paletteName='midnight',mode=mode,colors=colors,targets={'foot':False}),state)
        assert 'modesty-generated.conf' not in profile.read_text() and 'include modesty-effects.conf' in profile.read_text() and original.read_text()=='font_size 17\n'
    stub=directory/'bin';stub.mkdir()
    executable=stub/'kitty'
    executable.write_text('#!'+sys.executable+'\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n');executable.chmod(0o755)
    function=ROOT/'setup/config/fish/functions/modesty-terminal.fish'
    command=['fish','-c','source $argv[1]; modesty-terminal printf "%s" "arg with spaces"',str(function)]
    result=subprocess.run(command,env=dict(os.environ,PATH=str(stub)+':'+os.environ['PATH'],XDG_CONFIG_HOME=str(config)),check=True,capture_output=True,text=True)
    assert json.loads(result.stdout)==['--config',str(profile),'printf','%s','arg with spaces']
    spec=importlib.util.spec_from_file_location('app_theme',ROOT/'scripts/app-theme.py')
    app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
    proc=directory/'proc';proc.mkdir()
    for pid,parent,name in [(10,0,'kitty'),(11,10,'fish'),(20,0,'kitty'),(21,20,'fish'),(30,0,'foot'),(31,30,'fish')]:
        process=proc/str(pid);process.mkdir();(process/'stat').write_text(f'{pid} ({name}) S {parent}')
    real_read=Path.read_bytes
    def command_line(path):
        if path==Path('/proc/10/cmdline'):return b'kitty\0--config\0'+str(profile).encode()+b'\0'
        if path==Path('/proc/20/cmdline'):return b'kitty\0'
        return real_read(path)
    with patch.object(app,'CONFIG',config),patch.object(Path,'read_bytes',command_line),\
         patch.object(Path,'iterdir',lambda path:real_iterdir(proc if path==Path('/proc') else path)),\
         patch.object(app.os,'readlink',side_effect=lambda path:'/dev/pts/'+path.split('/')[2] if path.split('/')[2] in ('11','21','31') else '/dev/null'),\
         patch.object(app.os,'open',return_value=99) as opened,patch.object(app.os,'close'),\
         patch.object(app.os,'fstat',return_value=SimpleNamespace(st_uid=os.getuid(),st_mode=stat.S_IFCHR)),patch.object(app.os,'write'):
        app.apply_live_terminals(json.loads((state/'matugen/input.json').read_text()),state)
        assert {call.args[0] for call in opened.call_args_list}=={'/dev/pts/11','/dev/pts/31'}
    art=directory/'art.png';Image.new('RGB',(24,40),'#123456').save(art)
    for term,protocol in [('foot','sixel'),('xterm-kitty','kitty-direct')]:
        with patch.dict(os.environ,dict(TERM=term,XDG_CONFIG_HOME=str(config),XDG_STATE_HOME=str(directory)),clear=True),\
             patch.object(greeting.sys.stdout,'isatty',return_value=True),\
             patch.object(greeting.shutil,'which',return_value='/bin/fastfetch'),\
             patch.object(greeting,'catalogue',return_value=[dict(id='portraits/test',collection='portraits',image=str(art),ascii=str(art))]),\
             patch.object(greeting.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as run:
            greeting.main()
            args=run.call_args.args[0]
            assert args[args.index('--logo-type')+1]==protocol
print('PASS optional Kitty native trail/palette, original config preservation, theme opt-out, Fish arguments and Foot/Kitty artwork protocols')

import contextlib
import io
from unittest.mock import Mock
spec=importlib.util.spec_from_file_location('effects',ROOT/'scripts/terminal-effects.py')
effects=importlib.util.module_from_spec(spec);spec.loader.exec_module(effects)
spec=importlib.util.spec_from_file_location('terminal_installer',ROOT/'install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
import installation

with tempfile.TemporaryDirectory(prefix='modesty-effects-check-') as temporary:
    home=Path(temporary);config=home/'.config';state=home/'.local/state'
    optional=(config/'kitty/modesty.conf',config/'kitty/modesty-effects.conf',config/'kitty/modesty-generated.conf',config/'fish/functions/modesty-terminal.fish')
    environment=dict(HOME=str(home),XDG_CONFIG_HOME=str(config),XDG_STATE_HOME=str(state),XDG_DATA_HOME=str(home/'.local/share'),XDG_CACHE_HOME=str(home/'.cache'),PATH=os.environ['PATH'])
    with (
        patch.dict(os.environ,environment,clear=True),patch.object(effects,'HOME',home),patch.object(effects,'CONFIG',config),patch.object(effects,'STATE',state),
        patch.object(effects,'PROFILE',optional[0]),patch.object(effects,'EFFECTS',optional[1]),patch.object(effects,'OPTIONAL',optional),
        patch.object(installer,'HOME',home),patch.object(installer,'CONFIG',config),patch.object(installer,'STATE',state),contextlib.redirect_stdout(io.StringIO()),
    ):
        assert effects.status()['availability']=='absent'
        assert not list(home.iterdir())
        ordinary=config/'kitty/kitty.conf';ordinary.parent.mkdir(parents=True);ordinary.write_text('font_size 23\n')
        originals={}
        for source,target in installer.planned_files(['terminal-effects']):
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(installer.rendered(source));target.chmod(0o640)
            originals[str(target)]=target.read_bytes()
        assert effects.status()['availability']=='unmanaged'
        assert installer.install_files(['terminal-effects'],True)==4
        assert not state.exists()
        assert installer.install_files(['terminal-effects'],False)==4
        receipt_path=state/'modesty-install/receipt.json'
        first=json.loads(receipt_path.read_text())
        assert all(entry['original'] for entry in first['files'].values())
        assert installer.install_files(['terminal-effects'],False)==0
        assert json.loads(receipt_path.read_text())['files']==first['files']
        if shutil.which('kitty'):
            assert effects.status()['availability']=='ready' and effects.status()['enabled']
            original_effects=optional[1].read_bytes()
            for malformed in ('cursor_trail unsupported\n','cursor_trail 1\ncursor_trail_decay invalid\n'):
                optional[1].write_text(malformed)
                receipt_before=receipt_path.read_bytes();backups_before=set((state/'modesty-install-backups').iterdir())
                assert effects.status()['availability']=='unsupported'
                real_popen=subprocess.Popen
                def native_only(args,*positional,**keywords):
                    if args[1:2]!=['+runpy']:raise AssertionError('Malformed profile reached native window launch')
                    return real_popen(args,*positional,**keywords)
                with patch.object(effects.subprocess,'Popen',side_effect=native_only):
                    for action in (lambda:effects.set_trail(False),effects.launch):
                        try:action()
                        except RuntimeError:pass
                        else:raise AssertionError('Malformed native configuration was accepted')
                assert optional[1].read_text()==malformed and receipt_path.read_bytes()==receipt_before
                assert set((state/'modesty-install-backups').iterdir())==backups_before
            optional[1].write_bytes(original_effects)
            before=optional[0].read_bytes();palette=optional[2].read_bytes()
            assert effects.set_trail(False)['enabled'] is False
            assert optional[1].read_text().startswith('cursor_trail 0\n')
            receipt_off=receipt_path.read_bytes();backups=set((state/'modesty-install-backups').iterdir())
            assert effects.set_trail(False)['enabled'] is False
            assert receipt_path.read_bytes()==receipt_off and set((state/'modesty-install-backups').iterdir())==backups
            assert effects.set_trail(True)['enabled'] is True
            assert optional[0].read_bytes()==before and optional[2].read_bytes()==palette
            assert {name:entry['original'] for name,entry in json.loads(receipt_path.read_text())['files'].items()}=={name:entry['original'] for name,entry in first['files'].items()}
            with patch.object(effects.subprocess,'Popen') as launch,patch.object(effects,'status',return_value=dict(availability='ready',enabled=True,message='ready')):
                effects.launch()
                assert launch.call_args.args[0]==[shutil.which('kitty'),'--config',str(optional[0])]
        with patch.object(effects.shutil,'which',side_effect=lambda name:None if name=='fish' else '/stub/kitty'):
            assert effects.status()['availability']=='error' and 'Fish is required' in effects.status()['message']
        with patch.object(effects.shutil,'which',return_value=None):
            assert effects.status()['availability']=='missing-kitty'
        with patch.object(effects,'validate_profile',side_effect=RuntimeError('unsupported native option')),patch.object(effects.shutil,'which',return_value='/stub/kitty'):
            assert effects.status()['availability']=='unsupported'
            try:effects.set_trail(False)
            except RuntimeError as error:assert 'unsupported' in str(error)
            else:raise AssertionError('Unsupported native option was changed')
        with patch.dict(os.environ,MODESTY_PREVIEW='1'),patch.object(effects.subprocess,'Popen') as launch:
            for action in (lambda:effects.set_trail(False),effects.launch):
                try:action()
                except RuntimeError as error:assert 'Preview' in str(error)
                else:raise AssertionError('Preview terminal action accepted')
            launch.assert_not_called()
        locked_session=SimpleNamespace(assert_unlocked=Mock(side_effect=RuntimeError('Unlock first')))
        fake_spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module:None))
        with patch.dict(os.environ,XDG_SESSION_ID='isolated-test'),patch.object(effects.importlib.util,'spec_from_file_location',return_value=fake_spec),patch.object(effects.importlib.util,'module_from_spec',return_value=locked_session):
            try:effects.set_trail(False)
            except RuntimeError as error:assert 'Unlock' in str(error)
            else:raise AssertionError('Locked terminal action accepted')
        contents=optional[1].read_bytes();optional[1].unlink();optional[1].symlink_to(ordinary)
        assert effects.status()['availability']=='error'
        optional[1].unlink();optional[1].write_bytes(contents)
        optional[1].write_text('later user edit\n')
        installation.uninstall(ROOT,home,state)
        for target in optional:
            assert target.read_bytes()==originals[str(target)] and target.stat().st_mode&0o777==0o640
        assert any(path.read_text()=='later user edit\n' for path in (state/'modesty-install-backups').rglob('modesty-effects.conf'))
        assert ordinary.read_text()=='font_size 23\n'

with tempfile.TemporaryDirectory(prefix='modesty-no-kitty-theme-') as temporary:
    config=Path(temporary)/'config';config.mkdir();state=Path(temporary)/'state'
    with patch.dict(os.environ,XDG_CONFIG_HOME=str(config)),patch.object(appearance.subprocess,'run',side_effect=isolated_run),patch.object(Path,'iterdir',isolated_iterdir):
        appearance.apply(dict(paletteName='midnight',mode='dark',colors=colors,targets={'foot':True}),state)
    assert not (config/'kitty').exists()
print('PASS receipt-owned native toggle, identical optional adoption, first-original uninstall, idempotence, unsafe paths, preview/lock guards, explicit launch and absent theme profile')
