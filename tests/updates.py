#!/usr/bin/env python3
"""Exercise real Git transactions and blocked update paths without live restart."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import MagicMock, patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import compatibility
import updates


def rejected(call, fragment):
    try: call()
    except (RuntimeError, ValueError) as error:
        assert fragment.lower() in str(error).lower(), (fragment, error)
    else: raise AssertionError('Accepted invalid operation: '+fragment)


def successful_run(revision):
    return dict(head_sha=revision, head_branch='main', event='push', run_number=2,
                run_attempt=1, status='completed', conclusion='success')


def github_api(revision, workflows=None, main=None):
    workflows = workflows if workflows is not None else {
        workflow: [successful_run(revision)] for workflow in ('checks.yml', 'codeql.yml')}
    def response(path):
        if path == 'commits/main':
            return {'sha': main or revision, 'commit': {'message': 'New version'}}
        for workflow, runs in workflows.items():
            if path == f'actions/workflows/{workflow}/runs?branch=main&event=push&head_sha={revision}&per_page=100':
                return {'workflow_runs': runs}
        raise AssertionError('Unexpected GitHub request: '+path)
    return response


revision = 'a'*40
green = successful_run(revision)
for workflow in ('checks.yml', 'codeql.yml'):
    invalid_runs = ([], [{**green, 'head_sha': 'b'*40}], [{**green, 'head_branch': 'feature'}],
                    [{**green, 'event': 'pull_request'}], [{**green, 'status': 'in_progress', 'conclusion': None}],
                    [green, {**green, 'run_attempt': 2, 'conclusion': 'failure'}],
                    [green, {**green, 'run_number': 3, 'status': 'queued', 'conclusion': None}])
    for runs in invalid_runs:
        workflows = {name: [green] for name in ('checks.yml', 'codeql.yml')}
        workflows[workflow] = runs
        with patch.object(updates, 'api', side_effect=github_api(revision, workflows)):
            rejected(updates.verified_revision, 'not passed')
with patch.object(updates, 'api', side_effect=github_api(revision)) as requested:
    assert updates.verified_revision() == (revision, 'New version')
    assert requested.call_count == 3
with patch.object(updates, 'api', side_effect=URLError('unavailable')):
    try: updates.verified_revision()
    except URLError: pass
    else: raise AssertionError('GitHub API failure accepted')
print('PASS exact main push CI, both workflows, latest failed/pending reruns and API failure')


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
    with patch.object(updates, 'ROOT', repo), patch.object(updates, 'STATE', state), patch.object(updates, 'STAGE', state/'candidate'), patch.object(updates, 'RECORD', state/'status.json'), patch.object(updates.os, 'geteuid', return_value=1000), patch.object(updates, 'session', return_value=control), patch.object(updates, 'busy_work'), patch.object(updates.compatibility, 'require', return_value={'ok':True,'warnings':[]}), patch.object(updates, 'api', side_effect=github_api(new)):
        assert updates.clean_checkout() == old
        (repo/'untracked').touch()
        rejected(updates.clean_checkout, 'local changes'); (repo/'untracked').unlink()
        raw('remote', 'set-url', 'origin', 'https://github.com/other/fork.git')
        rejected(updates.clean_checkout, 'fork'); raw('remote', 'set-url', 'origin', updates.UPSTREAM)
        raw('checkout', '-b', 'development'); rejected(updates.clean_checkout, 'main'); raw('checkout', 'main')
        rejected(lambda: updates.sha('--force'), 'Invalid update revision')
        with patch.object(updates, 'api', side_effect=[{'sha':new,'commit':{'message':'New version'}},{'workflow_runs':[]} ]):
            rejected(updates.verified_revision, 'not passed')
        for workflow in ('checks.yml', 'codeql.yml'):
            runs = {name: [successful_run(new)] for name in ('checks.yml', 'codeql.yml')}
            runs[workflow] = []
            with patch.object(updates, 'api', side_effect=github_api(new, runs)), patch.object(updates, 'stage') as staged:
                rejected(lambda: updates.download(new), workflow+' has not passed')
                staged.assert_not_called()
            assert raw('rev-parse', 'HEAD') == old and not updates.STAGE.exists()
            control.stop_modesty.assert_not_called()
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
        with patch.object(updates, 'api', side_effect=github_api(new, main='c'*40)) as requested:
            updates.switch(new)
            assert requested.call_count == 2
            assert all(call.args[0] != 'commits/main' for call in requested.call_args_list)
        assert raw('rev-parse', 'HEAD') == new and (repo/'version.txt').read_text() == 'new'
        assert updates.status()['rollback'] == old and not updates.STAGE.exists()
        with patch.object(updates, 'api', side_effect=AssertionError('Rollback must stay offline')):
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
        with patch.object(updates,'UPSTREAM',str(upstream)):
            updates.download(new)
            assert updates.status()['staged']==new and raw('rev-parse','HEAD')==old
        with patch.object(updates,'UPSTREAM',str(upstream)),patch.object(updates,'api',side_effect=github_api(old)):
            rejected(lambda:updates.download(new),'selection changed')
        control.start.side_effect = None
        stops = control.stop_modesty.call_count
        def lock_during_ci(path):
            result = github_api(new)(path)
            if '/codeql.yml/' in path:
                control.assert_unlocked.side_effect = RuntimeError('locked during CI')
            return result
        with patch.object(updates, 'api', side_effect=lock_during_ci):
            rejected(lambda: updates.switch(new), 'locked during CI')
        control.assert_unlocked.side_effect = None
        assert raw('rev-parse', 'HEAD') == old and control.stop_modesty.call_count == stops
        def edit_during_ci(path):
            result = github_api(new)(path)
            if '/codeql.yml/' in path:
                (repo/'changed-during-ci').touch()
            return result
        with patch.object(updates, 'api', side_effect=edit_during_ci):
            rejected(lambda: updates.switch(new), 'local changes')
        (repo/'changed-during-ci').unlink()
        assert raw('rev-parse', 'HEAD') == old and control.stop_modesty.call_count == stops
        for workflow in ('checks.yml', 'codeql.yml'):
            green = successful_run(new)
            for rerun in ({**green, 'run_attempt': 2, 'conclusion': 'failure'},
                          {**green, 'run_attempt': 2, 'status': 'in_progress', 'conclusion': None}):
                runs = {name: [green] for name in ('checks.yml', 'codeql.yml')}
                def rerun_after_validation(*args):
                    runs[workflow].append(rerun)
                record = updates.RECORD.read_bytes()
                stops = control.stop_modesty.call_count
                with patch.object(control, 'validate_shell', side_effect=rerun_after_validation), patch.object(updates, 'api', side_effect=github_api(new, runs)), patch.object(updates, 'git', wraps=updates.git) as commands:
                    rejected(lambda: updates.switch(new), workflow+' has not passed')
                    assert not any(call.args[0] in ('update-ref', 'merge', 'reset', 'worktree') for call in commands.call_args_list)
                assert raw('rev-parse', 'HEAD') == old and updates.STAGE.exists()
                assert updates.RECORD.read_bytes() == record
                assert control.stop_modesty.call_count == stops
        stops = control.stop_modesty.call_count
        with patch.object(updates, 'api', side_effect=URLError('unavailable')):
            try: updates.switch(new)
            except URLError: pass
            else: raise AssertionError('Apply accepted GitHub API failure')
        assert raw('rev-parse', 'HEAD') == old and control.stop_modesty.call_count == stops
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
