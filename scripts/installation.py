"""Record file ownership and make installation/removal recoverable."""
from contextlib import contextmanager
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile


def atomic(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.modesty-', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        target.symlink_to(os.readlink(source))
    else:
        shutil.copy2(source, target)


def safe_target(path, home, state):
    if not path.is_absolute() or '..' in path.parts or path in (home, state) or not any(path.is_relative_to(p) for p in (home, state)):
        raise RuntimeError('Unsafe installation path: '+str(path))
    for parent in path.parents:
        if parent.is_symlink():
            raise RuntimeError('A destination parent is a symlink: '+str(parent)+'. No files were changed.')
    if path.is_dir() and not path.is_symlink():
        raise RuntimeError('Destination is a directory: '+str(path)+'; no dotfiles were changed.')


def backup_path(path, home, state, folder):
    relative = path.relative_to(home) if path.is_relative_to(home) else Path('state')/path.relative_to(state)
    return folder/relative


def require_space(files, state, removing=False):
    budgets = {}
    def add(path, size):
        while not path.exists(): path = path.parent
        device = path.stat().st_dev
        parent, current = budgets.get(device, (path, 0))
        budgets[device] = (parent, current+size)
    add(state, 0)
    for target, content, _ in files:
        if target.exists() and not target.is_symlink(): add(state, target.stat().st_size)
        size = (Path(content).stat().st_size if content and not Path(content).is_symlink() else 0) if removing else len(content)
        add(target.parent, size)
    for parent, required in budgets.values():
        # Keep space for the journal, receipt and recovery metadata as well.
        available = shutil.disk_usage(parent).free
        if available < required+8*1024*1024:
            raise RuntimeError(f'Insufficient disk space near {parent}: need {required+8*1024*1024} bytes, available {available}. No dotfiles were changed.')


@contextmanager
def locked(state):
    directory = state/'modesty-install'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory/'operation.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another installer operation is running.') from None
        yield


def receipt(root, home, state):
    path = state/'modesty-install/receipt.json'
    if not path.exists():
        return dict(schema=1, root=str(root), home=str(home), state=str(state), files={}, directories=[])
    data = json.loads(path.read_text())
    if data.get('schema') != 1 or data.get('home') != str(home) or data.get('state') != str(state):
        raise RuntimeError('Installation receipt belongs to a different home/state or format. No files were changed.')
    for name, entry in data['files'].items():
        safe_target(Path(name), home, state)
        original = entry.get('original')
        if original and (not Path(original).is_relative_to(state/'modesty-install-backups') or '..' in Path(original).parts):
            raise RuntimeError('Unsafe backup path in installation receipt.')
    return data


def restore(path, original):
    if original is None:
        path.unlink(missing_ok=True)
    else:
        source = Path(original)
        if source.is_symlink():
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name('.modesty-restore-'+path.name)
            try:
                temporary.unlink(missing_ok=True)
                temporary.symlink_to(os.readlink(source))
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        else:
            atomic(path, source.read_bytes(), source.stat().st_mode & 0o777)


def recover(root, home, state, dry_run=False):
    journal = state/'modesty-install/transaction.json'
    if not journal.exists():
        print('No interrupted file operation to recover.'); return 0
    data = json.loads(journal.read_text())
    if data.get('home') != str(home) or data.get('state') != str(state):
        raise RuntimeError('Recovery record belongs to another installation.')
    for name, original in data['before'].items():
        safe_target(Path(name), home, state)
        if original and (not Path(original).is_relative_to(state/'modesty-install-backups') or '..' in Path(original).parts):
            raise RuntimeError('Unsafe recovery backup path.')
        if original and not (Path(original).exists() or Path(original).is_symlink()):
            raise RuntimeError('Recovery backup missing: '+original)
    for name, original in data['before'].items():
        print('Would restore' if original else 'Would remove', name)
    print('Surviving files will be backed up under', state/'modesty-install-backups')
    require_space([(Path(name), original, 0) for name, original in data['before'].items()], state, removing=True)
    if dry_run:
        return len(data['before'])
    # Back up whatever survived an interruption before restoring the transaction.
    folder = state/'modesty-install-backups'/('recovery-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True, mode=0o700)
    for name in data['before']:
        path = Path(name)
        if path.exists() or path.is_symlink():
            copy(path, backup_path(path, home, state, folder))
    for name, original in data['before'].items():
        restore(Path(name), original)
    atomic(state/'modesty-install/receipt.json', json.dumps(data['receipt']).encode())
    journal.unlink()
    print('Interrupted operation restored. Surviving files backed up to', folder)
    return len(data['before'])


def transaction(files, root, home, state, removing=False):
    """Back up every destination before writes; journal supports crash recovery."""
    journal = state/'modesty-install/transaction.json'
    if journal.exists():
        raise RuntimeError('An interrupted installation needs recovery. Run ./install.sh --recover-install first.')
    old = receipt(root, home, state)
    require_space(files, state, removing)
    data = json.loads(json.dumps(old))
    if not removing:
        data.update(root=str(root), uninstalled=False)
    folder = state/'modesty-install-backups'/dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    if any(target.exists() or target.is_symlink() for target, _, _ in files):
        folder.mkdir(parents=True, mode=0o700)
    before = {}
    for target, content, mode in files:
        safe_target(target, home, state)
        original = None
        if target.exists() or target.is_symlink():
            original = backup_path(target, home, state, folder)
            copy(target, original)
        before[str(target)] = str(original) if original else None
        if not removing:
            if str(target) not in data['files']:
                data['files'][str(target)] = dict(original=before[str(target)])
            data['files'][str(target)]['installedSha256'] = hashlib.sha256(content).hexdigest()
            for parent in reversed(target.parents):
                if not parent.exists() and str(parent) not in data['directories']:
                    data['directories'].append(str(parent))
    atomic(journal, json.dumps(dict(home=str(home), state=str(state), before=before, receipt=old)).encode())
    written = []
    try:
        for target, content, mode in files:
            if removing:
                restore(target, content)
            else:
                atomic(target, content, mode)
            written.append(target)
        if removing:
            data.update(files={}, directories=[], uninstalled=True)
        atomic(state/'modesty-install/receipt.json', json.dumps(data, indent=2).encode())
    except Exception:
        for target in reversed(written):
            restore(target, before[str(target)])
        journal.unlink()
        raise
    journal.unlink()
    if removing:
        for name in sorted(old['directories'], key=len, reverse=True):
            path = Path(name)
            if path not in (home, state) and any(path.is_relative_to(p) for p in (home, state)) and not path.is_symlink():
                try: path.rmdir()
                except (FileNotFoundError, OSError): pass
    return folder, sum(v is not None for v in before.values())


def install(files, rendered, root, home, state, dry_run):
    for _, target in files:
        safe_target(target, home, state)
    changes = [(target, rendered(source), source.stat().st_mode & 0o777) for source, target in files
               if target.is_symlink() or not target.is_file() or target.read_bytes() != rendered(source)]
    if dry_run:
        if (state/'modesty-install/transaction.json').exists():
            raise RuntimeError('An interrupted installation needs recovery. Run ./install.sh --recover-install first.')
        receipt(root, home, state)
        require_space(changes, state)
        for target, _, _ in changes:
            print('Would replace' if target.exists() or target.is_symlink() else 'Would install', target)
        print('Planned', len(changes), 'files.'); return len(changes)
    with locked(state):
        folder, count = transaction(changes, root, home, state)
    print(f'Installed {len(changes)} files; backed up {count} existing files'+(f' to {folder}' if count else '')+'.')
    return len(changes)


def uninstall_plan(root, home, state):
    if (state/'modesty-install/transaction.json').exists():
        raise RuntimeError('An interrupted installation needs recovery. Run ./install.sh --recover-install first.')
    if not (state/'modesty-install/receipt.json').exists():
        raise RuntimeError('No installation receipt. For older installs, use --adopt-existing after reviewing --dry-run; restore old backups manually.')
    data = receipt(root, home, state)
    result = []
    for name, entry in data['files'].items():
        original = entry['original']
        if original and not (Path(original).exists() or Path(original).is_symlink()):
            raise RuntimeError('Original backup missing: '+original+'. No dotfiles were changed.')
        target = Path(name)
        if target.is_symlink() or target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() != entry.get('installedSha256'):
            print('Local changes will be backed up:', target)
        result.append((target, original, 0))
    return result


def uninstall(root, home, state, dry_run=False):
    files = uninstall_plan(root, home, state)
    require_space(files, state, removing=True)
    for target, original, _ in files:
        print('Would restore' if original else 'Would remove', target)
    if dry_run:
        return len(files)
    with locked(state):
        folder, count = transaction(files, root, home, state, removing=True)
    print(f'Uninstalled {len(files)} files. Backed up {count} current files to {folder}.')
    print('Packages, accounts, personal files, user data and this checkout were preserved. Log out before using your restored desktop.')
    return len(files)


def adopt(files, rendered, root, home, state, dry_run=False):
    if (state/'modesty-install/receipt.json').exists():
        raise RuntimeError('An installation receipt already exists; adoption is only for older installs.')
    data = receipt(root, home, state)
    for source, target in files:
        safe_target(target, home, state)
        if target.is_file() and not target.is_symlink() and target.read_bytes() == rendered(source):
            print('Would adopt', target)
            data['files'][str(target)] = dict(original=None, originalUnknown=True, installedSha256=hashlib.sha256(target.read_bytes()).hexdigest())
    if not data['files']:
        raise RuntimeError('No exact template matches found; nothing was adopted.')
    if not dry_run:
        with locked(state):
            atomic(state/'modesty-install/receipt.json', json.dumps(data, indent=2).encode())
    print('Original configs are unknown. Uninstall backs up adopted files before removal; restore older backups manually.')
    return len(data['files'])
