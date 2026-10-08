#!/usr/bin/env python3
"""Exercise real Git transactions and blocked update paths without live restart."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import compatibility
import updates


def rejected(call, fragment):
    try: call()
    except (RuntimeError, ValueError) as error:
        assert fragment.lower() in str(error).lower(), (fragment, error)
    else: raise AssertionError('Accepted invalid operation: '+fragment)


# Stable packages and -git builds are accepted by actual version, not flavor.
requirements = json.loads((ROOT/'runtime-requirements.json').read_text())
def installed(argv):
    if argv[0] == 'Hyprland': return 'Hyprland 0.56.2'
    if argv[0] == 'quickshell': return 'Quickshell 0.3.1 (AUR quickshell-git)'
    if argv[0] == 'pacman': return argv[-1]+' 6.11.2-3'
    raise AssertionError(argv)

with patch.object(compatibility, 'capture', side_effect=installed), patch.object(compatibility.shutil, 'which', return_value='/usr/bin/tool'), patch.dict(compatibility.os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': ''}), patch.object(compatibility.importlib.util, 'find_spec', return_value=True):
    assert compatibility.inspect(ROOT)['ok']
    def mixed(argv):
        if argv[-1] == 'qt6-declarative': return 'qt6-declarative 6.10.2-1'
        return installed(argv)
    with patch.object(compatibility, 'capture', side_effect=mixed):
        rejected(lambda: compatibility.require(ROOT), 'Qt modules')
    with patch.object(compatibility, 'capture', side_effect=lambda argv: 'Hyprland 0.54.3' if argv[0]=='Hyprland' else installed(argv)):
        rejected(lambda: compatibility.require(ROOT), 'supported range')
    with patch.object(compatibility, 'capture', side_effect=lambda argv: 'Quickshell 0.3.1 COMPATIBILITY WARNING: Quickshell was built against Qt 6.10' if argv[0]=='quickshell' else installed(argv)):
        rejected(lambda: compatibility.require(ROOT), 'Qt mismatch')
    with patch.object(compatibility, 'capture', side_effect=lambda argv: 'Quickshell 0.3.1\nWARN: Quickshell was built against Qt 6.11.2 but the system has updated to Qt 6.12.0 without rebuilding the package.' if argv[0]=='quickshell' else installed(argv)):
        rejected(lambda: compatibility.require(ROOT), 'Qt mismatch')
    with patch.object(compatibility.shutil, 'which', side_effect=lambda name: None if name=='bwrap' else '/usr/bin/tool'):
        rejected(lambda: compatibility.require(ROOT), 'bubblewrap')
print('PASS stable/git versions, unsupported runtime, missing dependencies and mixed/compiled Qt gates')

with tempfile.TemporaryDirectory(prefix='modesty-update-check-') as directory, contextlib.redirect_stdout(io.StringIO()):
    directory = Path(directory); repo = directory/'repo'; repo.mkdir(); state = directory/'state'
    def raw(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args], text=True, stderr=subprocess.DEVNULL).strip()
    raw('init', '-b', 'main'); raw('config', 'user.email', 'test@example.invalid'); raw('config', 'user.name', 'Update test')
    raw('remote', 'add', 'origin', updates.UPSTREAM)
    (repo/'version.txt').write_text('old')
    (repo/'.gitignore').write_text('notes.cache\n')
    shutil.copy2(ROOT/'runtime-requirements.json', repo/'runtime-requirements.json')
    raw('add', '.'); raw('commit', '-m', 'Old version'); old = raw('rev-parse', 'HEAD')
    (repo/'version.txt').write_text('new');(repo/'notes.cache').write_text('upstream file');raw('add','--force','notes.cache')
    raw('commit', '-am', 'New version'); new = raw('rev-parse', 'HEAD')
    raw('reset', '--hard', old)
    control = MagicMock(unsafe=True); control.health.return_value = {'locked': False}
    control.MARKER=directory/'main-shell'; control.MARKER.write_text(str(repo))
    with patch.object(updates, 'ROOT', repo), patch.object(updates, 'STATE', state), patch.object(updates, 'STAGE', state/'candidate'), patch.object(updates, 'RECORD', state/'status.json'), patch.object(updates.os, 'geteuid', return_value=1000), patch.object(updates, 'session', return_value=control), patch.object(updates, 'busy_work'), patch.object(updates.compatibility, 'require', return_value={'ok':True,'warnings':[]}):
        assert updates.clean_checkout() == old
        (repo/'untracked').touch()
        rejected(updates.clean_checkout, 'local changes'); (repo/'untracked').unlink()
        raw('remote', 'set-url', 'origin', 'https://github.com/other/fork.git')
        rejected(updates.clean_checkout, 'fork'); raw('remote', 'set-url', 'origin', updates.UPSTREAM)
        raw('checkout', '-b', 'development'); rejected(updates.clean_checkout, 'main'); raw('checkout', 'main')
        rejected(lambda: updates.sha('--force'), 'Invalid update revision')
        with patch.object(updates, 'api', side_effect=[{'sha':new,'commit':{'message':'New version'}},{'workflow_runs':[]} ]):
            rejected(updates.verified_revision, 'not passed')
        # An unsupported download fails while the current checkout/shell stay intact.
        with patch.object(updates.compatibility, 'require', side_effect=RuntimeError('unsupported')):
            rejected(lambda: updates.stage(new, fetch=False), 'unsupported')
        assert raw('rev-parse', 'HEAD') == old and not updates.STAGE.exists()
        control.stop_modesty.assert_not_called()
        updates.stage(new, fetch=False); updates.save(phase='ready', staged=new, target=new)
        control.validate_shell.side_effect = RuntimeError('bad QML')
        rejected(lambda: updates.switch(new), 'bad QML')
        assert raw('rev-parse', 'HEAD') == old; control.stop_modesty.assert_not_called()
        control.validate_shell.side_effect = None
        control.assert_unlocked.side_effect=RuntimeError('locked')
        rejected(lambda:updates.switch(new),'locked')
        control.stop_modesty.assert_not_called()
        control.assert_unlocked.side_effect=None
        (repo/'notes.cache').write_text('private ignored notes')
        rejected(lambda:updates.switch(new),'ignored local file')
        assert (repo/'notes.cache').read_text()=='private ignored notes'
        control.stop_modesty.assert_not_called()
        (repo/'notes.cache').unlink()
        (updates.STAGE/'version.txt').write_text('tampered')
        rejected(lambda: updates.switch(new), 'Download and validate')
        updates.git('reset', '--hard', new, cwd=updates.STAGE)
        updates.switch(new)
        assert raw('rev-parse', 'HEAD') == new and (repo/'version.txt').read_text() == 'new'
        assert updates.status()['rollback'] == old and not updates.STAGE.exists()
        updates.switch(old, rollback=True)
        assert raw('rev-parse', 'HEAD') == old and updates.status()['rollback'] == ''
        # Startup failure restores the old tree and starts it again.
        updates.stage(new, fetch=False); updates.save(phase='ready', staged=new, target=new)
        control.start.side_effect = [RuntimeError('startup failed'), None]
        rejected(lambda: updates.switch(new), 'startup failed')
        assert raw('rev-parse', 'HEAD') == old and (repo/'version.txt').read_text() == 'old'
        # Download exercises a real fetch from an isolated upstream fixture.
        raw('branch','candidate',new)
        upstream=directory/'upstream.git'
        subprocess.run(['git','clone','--bare','--no-local',str(repo),str(upstream)],check=True,capture_output=True)
        subprocess.run(['git','--git-dir',str(upstream),'update-ref','refs/heads/main',new],check=True)
        with patch.object(updates,'UPSTREAM',str(upstream)),patch.object(updates,'verified_revision',return_value=(new,'New version')):
            updates.download(new)
            assert updates.status()['staged']==new and raw('rev-parse','HEAD')==old
        with patch.object(updates,'UPSTREAM',str(upstream)),patch.object(updates,'verified_revision',return_value=(old,'Changed selection')):
            rejected(lambda:updates.download(new),'selection changed')
        control.start.side_effect = None
        # Simulate a partial Git write: recovery must not depend on exit success.
        updates.save(phase='ready', staged=new, target=new)
        actual = updates.git
        def partial(*args, **kwargs):
            if args[0] == 'merge':
                (repo/'version.txt').write_text('partial')
                raise RuntimeError('write failed')
            return actual(*args, **kwargs)
        with patch.object(updates, 'git', side_effect=partial):
            rejected(lambda: updates.switch(new), 'write failed')
        assert raw('rev-parse', 'HEAD') == old and (repo/'version.txt').read_text() == 'old'
        if updates.STAGE.exists(): updates.git('worktree', 'remove', '--force', str(updates.STAGE))
        raw('commit','--allow-empty','-m','Local divergent commit')
        rejected(lambda:updates.require_fast_forward(new),'Local history diverges')
        raw('reset','--hard',old)
        with updates.locked():
            try:
                with updates.locked(): pass
            except RuntimeError as error: assert 'Another update' in str(error)
            else: raise AssertionError('Concurrent updater lock accepted')
        updates.save(phase='applying', pid=0)
        data=json.loads(updates.RECORD.read_text()); data['pid']=99999999; updates.RECORD.write_text(json.dumps(data))
        assert updates.status()['phase']=='recovery'
print('PASS real Git fetch/apply/rollback, locks, dirty/fork/branch/divergence guards, staged tampering, CI gate, locked session, failed validation/startup and partial-write recovery')

# A reload validates the current runtime; report those versions, not an older
# saved update check, so Qt repair diagnostics agree with the actual gate.
report = {'ok':True,'versions':{'qt6-base':'6.12.0'},'errors':[],'warnings':[]}
control = MagicMock(unsafe=True)
with patch.object(updates.compatibility, 'require', return_value=report), patch.object(updates, 'installed_session', return_value=control), patch.object(updates, 'busy_work'), patch.object(updates, 'save') as saved:
    updates.reload_shell()
    control.assert_unlocked.assert_called_once()
    control.restart.assert_called_once()
    assert saved.call_args_list[0].kwargs['compatibility'] == report
print('PASS reload diagnostics refresh actual validated runtime versions')
