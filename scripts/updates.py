#!/usr/bin/env python3
"""Explicit, CI-gated source updates; never change packages or user configs."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request

import compatibility
from desktop_environment import clean_environment

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = 'https://github.com/sandeepbist/Modesty.git'
API = 'https://api.github.com/repos/sandeepbist/Modesty/'
STATE = Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'modesty/updates'/hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
STAGE = STATE/'candidate'
RECORD = STATE/'status.json'
ROLLBACK = 'refs/modesty-updates/rollback'


def git(*args, cwd=None):
    env = clean_environment()
    # Do not inherit another checkout's Git context from an embedding editor.
    env = {k: v for k, v in env.items() if not k.startswith('GIT_')}
    env.update(GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1')
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', *args],
                            cwd=cwd or ROOT, env=env, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[-1600:] or f'Git {args[0]} failed with exit code {result.returncode}.')
    return result.stdout.strip()


def sha(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{40}', value):
        raise ValueError('Invalid update revision.')
    return value


def status():
    try:
        data = json.loads(RECORD.read_text())
    except (FileNotFoundError, ValueError):
        data = dict(phase='idle', message='Check for updates when you are ready.')
    try:
        data['current'] = git('rev-parse', 'HEAD')
        data['rollback'] = git('rev-parse', '--verify', ROLLBACK)
    except RuntimeError:
        data['rollback'] = ''
    if data.get('phase') in ('launching', 'checking', 'downloading', 'preparing', 'applying') and not Path('/proc', str(data.get('pid', 0))).exists():
        data.update(phase='recovery', message='An update was interrupted. Use Roll back to restore the previous revision.')
    return data


def save(**changes):
    data = status()
    data.update(changes, updatedAt=int(time.time()), pid=os.getpid())
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = RECORD.with_suffix('.tmp')
    temporary.write_text(json.dumps(data))
    temporary.chmod(0o600)
    temporary.replace(RECORD)
    print(json.dumps(data), flush=True)
    return data


@contextmanager
def locked():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE/'operation.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another update operation is running.') from None
        yield


def clean_checkout():
    if os.geteuid() == 0:
        raise RuntimeError('Run updates as your desktop user, not root.')
    if git('rev-parse', '--show-toplevel') != str(ROOT):
        raise RuntimeError('Update the Modesty Git checkout, not a copied subdirectory.')
    if git('branch', '--show-current') != 'main':
        raise RuntimeError('Automatic updates require main. Update development branches manually.')
    origin = git('remote', 'get-url', 'origin').removesuffix('.git').rstrip('/')
    if origin not in ('https://github.com/sandeepbist/Modesty', 'git@github.com:sandeepbist/Modesty'):
        raise RuntimeError('This checkout uses a fork or custom origin. Update it manually.')
    if git('status', '--porcelain', '--untracked-files=all'):
        raise RuntimeError('Checkout has local changes or untracked files. Commit or move them first; nothing will be overwritten.')
    for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply', 'index.lock'):
        if Path(git('rev-parse', '--git-path', name)).is_absolute():
            path = Path(git('rev-parse', '--git-path', name))
        else:
            path = ROOT/git('rev-parse', '--git-path', name)
        if path.exists():
            raise RuntimeError('A Git operation is unfinished. Finish it before updating.')
    return sha(git('rev-parse', 'HEAD'))


def api(path):
    request = urllib.request.Request(API+path, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Modesty-updater'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def verified_revision():
    commit = api('commits/main')
    target = sha(commit['sha'])
    runs = api('actions/workflows/checks.yml/runs?branch=main&event=push&per_page=30')['workflow_runs']
    if not any(r['head_sha'] == target and r['head_branch'] == 'main' and
               r['event'] == 'push' and r['status'] == 'completed' and r['conclusion'] == 'success' for r in runs):
        raise RuntimeError('Latest main has not passed its checks yet. Keep the current version and try again later.')
    return target, commit['commit']['message'].split('\n')[0][:240]


def check():
    current = clean_checkout()
    save(phase='checking', message='Checking upstream and compatibility…', available=False, staged='', error='')
    report = compatibility.inspect(ROOT)
    target, title = verified_revision()
    return save(phase='available' if current != target else 'current', target=target, title=title,
                available=current != target, compatibility=report, error='\n'.join(report['errors']),
                message='Update available. Download to validate it on this machine.' if current != target else 'Modesty is up to date.')


def session():
    spec = importlib.util.spec_from_file_location('update_session', ROOT/'scripts/session-control.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def installed_session():
    control = session()
    if not control.MARKER.is_file() or control.MARKER.read_text().strip() != str(ROOT):
        raise RuntimeError('This checkout is not the installed main shell. Install it before using automatic updates.')
    return control


def reject_ignored_collisions(target):
    ignored = [p for p in git('ls-files', '--others', '--ignored', '--exclude-standard', '-z').split('\0') if p]
    added = [p for p in git('diff', '--name-only', '--diff-filter=A', '-z', 'HEAD', target).split('\0') if p]
    if any(a == p or a.startswith(p+'/') or p.startswith(a+'/') for a in added for p in ignored):
        raise RuntimeError('An ignored local file conflicts with this revision. Move it outside the checkout before updating.')


def require_fast_forward(target):
    try:
        git('merge-base', '--is-ancestor', git('rev-parse', 'HEAD'), target)
    except RuntimeError:
        raise RuntimeError('Local history diverges from this update. Update it manually; local commits were preserved.') from None


def stage(target, fetch=True):
    sha(target)
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    if min(shutil.disk_usage(ROOT).free, shutil.disk_usage(STATE).free) < 256*1024*1024:
        raise RuntimeError('Free at least 256 MiB in the checkout and state filesystems before downloading an update.')
    if STAGE.exists():
        git('worktree', 'remove', '--force', str(STAGE))
    if fetch:
        git('fetch', '--no-tags', '--no-recurse-submodules', UPSTREAM, 'main')
        if git('rev-parse', 'FETCH_HEAD') != target:
            raise RuntimeError('Upstream changed since your check. Check again before downloading.')
        require_fast_forward(target)
    total = sum(int(entry.split('\t',1)[0].split()[3]) for entry in git('ls-tree', '-r', '-l', '-z', target).split('\0')
                if entry and entry.split('\t',1)[0].split()[1] == 'blob')
    if min(shutil.disk_usage(ROOT).free, shutil.disk_usage(STATE).free) < total+64*1024*1024:
        raise RuntimeError('Not enough disk space for this update and validation cache. Free space before retrying.')
    git('worktree', 'add', '--detach', str(STAGE), target)
    try:
        report = compatibility.require(STAGE)
        session().validate_shell(STAGE)
        return report
    except Exception:
        git('worktree', 'remove', '--force', str(STAGE))
        raise


def download(target):
    clean_checkout()
    verified, _ = verified_revision()
    if sha(target) != verified:
        raise RuntimeError('Update selection changed. Check again.')
    save(phase='downloading', available=False, staged='', error='', message='Downloading and testing the update…')
    report = stage(target)
    # A rewritten/diverged upstream must never overwrite local commits.
    return save(phase='ready', available=True, staged=target, target=target, compatibility=report,
                message='Update tested on this machine. Install and reload when ready.')


def busy_work():
    for target in ('voice', 'luma', 'canvas'):
        result = subprocess.run(['quickshell', 'ipc', '-p', str(ROOT/'shell.qml'), 'call', target, 'status'],
                                env=clean_environment(), capture_output=True, text=True, timeout=5)
        if result.returncode:
            raise RuntimeError('Cannot verify active desktop work. Keep the shell running and retry.')
        data = json.loads(result.stdout)
        if (target == 'voice' and data.get('phase') in ('starting', 'listening', 'finishing')
                or target == 'luma' and data.get('busy')
                or target == 'canvas' and (data.get('answerRunning') or data.get('aiRunning'))):
            raise RuntimeError('Finish voice input, assistant work and recording before reloading.')
    recording = subprocess.run([sys.executable, str(ROOT/'scripts/recording.py'), 'status'],
                               env=clean_environment(), capture_output=True, text=True, timeout=5)
    if recording.returncode or json.loads(recording.stdout).get('phase') in ('preparing', 'selecting', 'countdown', 'recording', 'paused', 'saving'):
        raise RuntimeError('Finish recording before reloading.')


def switch(target, rollback=False):
    """Stop only after staged validation; restore code and shell on startup failure."""
    before = clean_checkout()
    target = sha(target)
    if before == target and not rollback:
        raise RuntimeError('This revision is already installed. Use Reload shell instead.')
    if not rollback:
        record = status()
        if record.get('staged') != target or not STAGE.exists() or git('rev-parse', 'HEAD', cwd=STAGE) != target or git('status', '--porcelain', cwd=STAGE):
            raise RuntimeError('Download and validate this update first.')
        require_fast_forward(target)
    else:
        if target != git('rev-parse', '--verify', ROLLBACK):
            raise RuntimeError('The rollback revision changed. Check the update status again.')
        stage(target, fetch=False)
    compatibility.require(STAGE)
    control = installed_session()
    control.validate_shell(STAGE)
    control.assert_unlocked()
    reject_ignored_collisions(target)
    if control.health():
        busy_work()
    elif not rollback:
        raise RuntimeError('Start Modesty before installing an update.')
    # Recheck after validation, which may take several seconds.
    if clean_checkout() != before:
        raise RuntimeError('Checkout changed during validation. Retry.')
    control.assert_unlocked()
    if not rollback:
        git('update-ref', ROLLBACK, before)
    save(phase='applying', pid=os.getpid(), previous=before, target=target, message='Installing and reloading…')
    stopped = changed = False
    try:
        stopped = True
        control.stop_modesty()
        # Even a failed Git command can have partly updated the working tree.
        changed = True
        if rollback:
            git('reset', '--hard', target)
        else:
            git('merge', '--ff-only', '--no-overwrite-ignore', '--no-edit', target)
        control.start()
    except Exception as error:
        recovery = ''
        try:
            if changed:
                control.stop_modesty()
                git('reset', '--hard', before)
            if stopped:
                control.start()
        except Exception as failed:
            recovery = '\nRecovery also failed: '+str(failed)+'\nFrom the checkout run: python3 scripts/updates.py rollback'
        save(phase='failed', staged='', available=False, message='Update failed; previous revision retained or restored.' if not recovery else 'Update and recovery failed.', error=str(error)+recovery)
        raise RuntimeError(str(error)+recovery) from error
    if rollback:
        git('update-ref', '-d', ROLLBACK)
    git('worktree', 'remove', '--force', str(STAGE))
    return save(phase='complete', staged='', available=False, error='', message='Previous version restored and shell reloaded.' if rollback else 'Update installed and shell reloaded. Your configs and packages were preserved.')


def reload_shell():
    compatibility.require(ROOT)
    control = installed_session()
    control.assert_unlocked()
    busy_work()
    save(phase='applying', pid=os.getpid(), message='Validating and reloading the shell…')
    control.restart()
    return save(phase='complete', message='Shell reloaded.', error='')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'check', 'download', 'apply', 'rollback', 'reload', 'launch'))
    parser.add_argument('argument', nargs='?')
    parser.add_argument('revision', nargs='?')
    args = parser.parse_args()
    if args.action == 'status':
        print(json.dumps(status())); return
    if args.action == 'launch':
        if args.argument not in ('apply', 'rollback', 'reload'):
            raise ValueError('Invalid detached operation.')
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        save(phase='launching', message='Preparing to reload…', error='')
        with (STATE/'operation.log').open('w') as log:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), args.argument,
                              *([sha(args.revision)] if args.argument == 'apply' else [])],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                             env=clean_environment(), start_new_session=True)
        return
    with locked():
        try:
            if args.action in ('apply', 'rollback', 'reload'):
                save(phase='preparing', message='Validating before reload…', error='')
            if args.action == 'check': check()
            elif args.action == 'download': download(sha(args.argument))
            elif args.action == 'apply': switch(sha(args.argument))
            elif args.action == 'rollback': switch(git('rev-parse', '--verify', ROLLBACK), rollback=True)
            elif args.action == 'reload': reload_shell()
        except Exception as error:
            save(phase='failed', available=False, error=str(error), message='Operation stopped. See details below.')
            raise


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
