#!/usr/bin/env python3
"""Check real file transactions, restore/uninstall and interruption recovery."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import installation


def rejected(call, fragment):
    try: call()
    except RuntimeError as error: assert fragment.lower() in str(error).lower(), error
    else: raise AssertionError('Accepted unsafe operation: '+fragment)


with tempfile.TemporaryDirectory(prefix='modesty-receipt-check-') as directory, contextlib.redirect_stdout(io.StringIO()):
    directory=Path(directory); home=directory/'home'; home.mkdir(); state=directory/'state'; source=directory/'source'; source.mkdir()
    a=home/'.config/app/a'; b=home/'.config/app/b'; c=home/'.config/new/c'
    a.parent.mkdir(parents=True); a.write_text('original a'); a.chmod(0o640)
    outside=directory/'outside'; outside.write_text('do not touch')
    b.symlink_to(outside)
    for name in ('a','b','c'): (source/name).write_text('installed '+name)
    files=[(source/name, target) for name,target in (('a',a),('b',b),('c',c))]
    render=lambda path:path.read_bytes()
    before=a.read_bytes()
    assert installation.install(files,render,source,home,state,True)==3
    assert not state.exists() and a.read_bytes()==before and b.is_symlink()
    with patch.object(installation.shutil,'disk_usage',return_value=SimpleNamespace(free=0)):
        rejected(lambda:installation.install(files,render,source,home,state,True),'Insufficient disk space')
        rejected(lambda:installation.install(files,render,source,home,state,False),'Insufficient disk space')
    assert a.read_bytes()==before and b.is_symlink() and not c.exists()
    actual=installation.atomic
    def fail_second(path,*args,**kwargs):
        if path==b: raise PermissionError('write failed')
        return actual(path,*args,**kwargs)
    with patch.object(installation,'atomic',side_effect=fail_second):
        try: installation.install(files,render,source,home,state,False)
        except PermissionError: pass
        else: raise AssertionError('Write failure accepted')
    assert a.read_bytes()==before and a.stat().st_mode&0o777==0o640 and b.is_symlink() and not c.exists()
    assert not (state/'modesty-install/transaction.json').exists()
    # An interrupt deliberately bypasses exception rollback, leaving a journal.
    def interrupt(path,*args,**kwargs):
        if path==b: raise KeyboardInterrupt()
        return actual(path,*args,**kwargs)
    with patch.object(installation,'atomic',side_effect=interrupt):
        try: installation.install(files,render,source,home,state,False)
        except KeyboardInterrupt: pass
        else: raise AssertionError('Interrupt ignored')
    assert a.read_text()=='installed a' and (state/'modesty-install/transaction.json').exists()
    backups=set((state/'modesty-install-backups').iterdir())
    assert installation.recover(source,home,state,True)==3
    assert a.read_text()=='installed a' and (state/'modesty-install/transaction.json').exists()
    assert set((state/'modesty-install-backups').iterdir())==backups
    rejected(lambda:installation.install(files,render,source,home,state,False),'recover-install')
    rejected(lambda:installation.install(files,render,source,home,state,True),'recover-install')
    with patch.object(installation.shutil,'disk_usage',return_value=SimpleNamespace(free=0)):
        rejected(lambda:installation.recover(source,home,state,True),'Insufficient disk space')
        rejected(lambda:installation.recover(source,home,state),'Insufficient disk space')
    assert a.read_text()=='installed a' and (state/'modesty-install/transaction.json').exists()
    installation.recover(source,home,state)
    assert a.read_bytes()==before and b.is_symlink() and not c.exists()
    assert installation.install(files,render,source,home,state,False)==3
    receipt=json.loads((state/'modesty-install/receipt.json').read_text())
    first_original=receipt['files'][str(a)]['original']
    assert all(p.stat().st_mode & 0o777 == 0o700 for p in (state/'modesty-install-backups').iterdir())
    assert Path(first_original).read_bytes()==before and Path(receipt['files'][str(b)]['original']).is_symlink()
    assert receipt['files'][str(c)]['original'] is None
    assert installation.install(files,render,source,home,state,False)==0
    a.write_text('my later edit')
    assert installation.install(files,render,source,home,state,False)==1
    assert installation.receipt(source,home,state)['files'][str(a)]['original']==first_original
    assert any(p.read_text()=='my later edit' for p in (state/'modesty-install-backups').rglob('a'))
    a.write_text('edit before uninstall'); unrelated=c.parent/'personal'; unrelated.write_text('keep me')
    assert installation.uninstall(source,home,state,True)==3 and a.read_text()=='edit before uninstall'
    installation.uninstall(source,home,state)
    assert a.read_bytes()==before and a.stat().st_mode&0o777==0o640
    assert b.is_symlink() and b.read_text()=='do not touch' and outside.read_text()=='do not touch'
    assert not c.exists() and unrelated.read_text()=='keep me'
    assert any(p.read_text()=='edit before uninstall' for p in (state/'modesty-install-backups').rglob('a'))
    assert installation.uninstall(source,home,state)==0
    assert installation.install(files,render,source,home,state,False)==3
    # Uninstall interrupted after one restore: recovery returns to installed state.
    actual_restore=installation.restore
    def interrupt_removal(path,*args,**kwargs):
        if path==b: raise KeyboardInterrupt()
        return actual_restore(path,*args,**kwargs)
    with patch.object(installation,'restore',side_effect=interrupt_removal):
        try: installation.uninstall(source,home,state)
        except KeyboardInterrupt: pass
    installation.recover(source,home,state)
    assert a.read_text()=='installed a' and b.read_text()=='installed b' and c.read_text()=='installed c'
    # Missing originals stop the complete removal plan before its first write.
    receipt=installation.receipt(source,home,state)
    Path(receipt['files'][str(a)]['original']).unlink()
    rejected(lambda:installation.uninstall(source,home,state),'Original backup missing')
    assert a.read_text()=='installed a' and b.read_text()=='installed b'
print('PASS real install/uninstall, first-original retention, edited-file backups, symlinks/modes, partial-write rollback and interrupted install/uninstall recovery')

with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
    directory=Path(directory); home=directory/'home'; home.mkdir(); state=directory/'state'; source=directory/'template'; source.write_text('template')
    target=home/'legacy'; target.write_text('template'); edited=home/'edited'; edited.write_text('personal edit')
    rejected(lambda:installation.uninstall(directory,home,state),'No installation receipt')
    files=[(source,target),(source,edited)]
    assert installation.adopt(files,lambda p:p.read_bytes(),directory,home,state,True)==1 and not state.exists()
    assert installation.adopt(files,lambda p:p.read_bytes(),directory,home,state)==1
    assert installation.receipt(directory,home,state)['files'][str(target)]['originalUnknown']
    installation.uninstall(directory,home,state)
    assert not target.exists() and edited.read_text()=='personal edit'
    assert any(p.read_text()=='template' for p in (state/'modesty-install-backups').rglob('legacy'))
    # Directory parent redirects must never make writes outside the chosen home.
    (home/'redirect').symlink_to(directory,target_is_directory=True)
    rejected(lambda:installation.install([(source,home/'redirect/unsafe')],lambda p:p.read_bytes(),directory,home,state,False),'parent is a symlink')
    rejected(lambda:installation.safe_target(directory/'outside',home,state),'Unsafe installation path')
print('PASS no-receipt refusal, explicit legacy adoption, edited-file exclusion and symlink/path escape guards')

with tempfile.TemporaryDirectory(prefix='modesty-deleted-config-') as directory, contextlib.redirect_stdout(io.StringIO()):
    directory=Path(directory);home=directory/'home';home.mkdir();state=home/'.local/state'
    source=directory/'template';source.write_text('installed config')
    original=directory/'original';original.write_text('original config')
    target=home/'.config/deleted/app';target.parent.mkdir(parents=True);target.symlink_to(original)
    installation.install([(source,target)],lambda p:p.read_bytes(),directory,home,state,False)
    target.unlink();target.parent.rmdir()
    installation.uninstall(directory,home,state)
    assert target.is_symlink() and target.read_text()=='original config'
print('PASS original symlink restored after the installed config directory was deleted')
