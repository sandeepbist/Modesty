#!/usr/bin/env python3
"""Run the real installer/uninstaller as this user in a disposable home and source copy.
Needs existing desktop dependencies and enabled NetworkManager/Bluetooth services.
Never installs packages, alters the real home, or starts a desktop session.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--isolated-home',action='store_true')
args=parser.parse_args()
if not args.isolated_home or os.geteuid()==0:
    raise SystemExit('Run as a normal desktop user with --isolated-home.')
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installer',ROOT/'install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
missing=installer.missing_core(installer.installed_packages())
if missing or installer.missing_services():
    raise SystemExit('Existing packages/services required first; this check does not install them: '+', '.join(missing))
with tempfile.TemporaryDirectory(prefix='modesty-cli-check-') as directory:
    folder=Path(directory);home=folder/'home';home.mkdir();repo=folder/'repo';repo.mkdir()
    paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    for name in paths:
        source=ROOT/name
        if not name or not source.is_file():continue
        target=repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    fish=home/'.config/fish/config.fish';fish.parent.mkdir(parents=True);fish.write_text('original fish config\n');fish.chmod(0o640)
    untouched=home/'personal.txt';untouched.write_text('keep personal files\n')
    key=home/'.config/modesty/gemini.key';key.parent.mkdir(parents=True);key.write_text('dummy-local-key');key.chmod(0o600)
    model=home/'.cache/modesty/voice-moonshine/keep';model.parent.mkdir(parents=True);model.write_text('dummy-existing-model')
    env=dict(os.environ,HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),XDG_STATE_HOME=str(home/'.local/state'),XDG_CACHE_HOME=str(home/'.cache'))
    env.pop('WAYLAND_DISPLAY',None);env.pop('HYPRLAND_INSTANCE_SIGNATURE',None)
    def cli(*flags,answers=None,expected=0):
        result=subprocess.run(['python3',str(repo/'install.py'),*flags],env=env,input=answers,capture_output=True,text=True,timeout=90)
        if result.returncode!=expected:raise RuntimeError(result.stdout+'\n'+result.stderr)
        return result.stdout
    packages=subprocess.check_output(['pacman','-Qq'],text=True)
    cli('--install-voice',answers='n\n',expected=130)
    assert not (home/'.local/share/modesty/stt-moonshine-venv').exists()
    prefix=['n']+(['n'] if any(p not in installer.installed_packages() for p in installer.EXTRAS) else [])
    selected=prefix+['y','y','y','n','n','y','n','n']
    for approval in ('n',''):
        output=cli(answers='\n'.join(selected+[approval])+'\n')
        assert output.index('Would replace '+str(fish))<output.index('Apply these files with backups')
        assert fish.read_text()=='original fish config\n' and not (home/'.local/state/modesty-install/receipt.json').exists()
        assert not (home/'Pictures/Wallpapers').exists()
    cli(answers='\n'.join(selected)+'\n',expected=130)
    assert fish.read_text()=='original fish config\n' and not (home/'.local/state/modesty-install/receipt.json').exists()
    cli(answers='\n'.join(selected+['y'])+'\n')
    receipt=home/'.local/state/modesty-install/receipt.json'
    assert len(json.loads(receipt.read_text())['files'])>50 and not (home/'Pictures/Wallpapers').exists()
    for approval in ('n',''):
        cli('--uninstall',answers=approval+'\n')
        assert json.loads(receipt.read_text())['files'] and fish.read_text()!='original fish config\n'
    cli('--uninstall',answers='y\n')
    assert fish.read_text()=='original fish config\n' and fish.stat().st_mode&0o777==0o640
    assert subprocess.check_output(['pacman','-Qq'],text=True)==packages
    # Even an interrupted zero-file transaction needs explicit recovery approval.
    journal=receipt.with_name('transaction.json')
    journal.write_text(json.dumps(dict(home=str(home),state=str(home/'.local/state'),before={},receipt=json.loads(receipt.read_text()))))
    before=journal.read_bytes()
    cli('--recover-install','--dry-run')
    for approval in ('n',''):
        cli('--recover-install',answers=approval+'\n')
        assert journal.read_bytes()==before
    cli('--recover-install',answers='y\n')
    assert not journal.exists()
    cli('--dry-run')
    assert fish.read_text()=='original fish config\n' and not json.loads(receipt.read_text())['files']
    cli('--non-interactive')
    receipt=home/'.local/state/modesty-install/receipt.json'
    data=json.loads(receipt.read_text());assert len(data['files'])>50,data
    assert str(home/'.local/state/modesty/main-shell') in data['files']
    assert fish.read_text()!='original fish config\n'
    assert 'Installed 0 files' in cli('--non-interactive')
    fish.write_text('edit after installation\n')
    assert 'Would' in cli('--uninstall','--dry-run') and fish.read_text()=='edit after installation\n'
    packages=subprocess.check_output(['pacman','-Qq'],text=True)
    cli('--uninstall','--non-interactive')
    assert fish.read_text()=='original fish config\n' and fish.stat().st_mode&0o777==0o640
    assert untouched.read_text()=='keep personal files\n' and key.read_text()=='dummy-local-key' and model.read_text()=='dummy-existing-model'
    assert not (home/'.local/state/modesty/main-shell').exists()
    assert not json.loads(receipt.read_text())['files']
    assert any(p.read_text()=='edit after installation\n' for p in (home/'.local/state/modesty-install-backups').rglob('config.fish'))
    assert subprocess.check_output(['pacman','-Qq'],text=True)==packages
print('PASS actual non-root CLI: previews before approval; declined/default-no/EOF preserve files; approved install/uninstall, repeat, backups, original modes, personal/key/model preservation and unchanged packages')
