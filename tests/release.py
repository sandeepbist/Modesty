#!/usr/bin/env python3
"""Release gates and source archives; no commits, tags or publication."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release', ROOT / 'scripts/release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def refused(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('Unsafe release operation was accepted')


assert release.metadata('1.2.3', '## [1.2.3]\nNotes\n', 'v1.2.3') == ('1.2.3', 'Notes\n')
assert release.metadata('1.2.3-rc.2', '## [1.2.3-rc.2]\nPreview\n')[0] == '1.2.3-rc.2'
for version in ('v1.2.3', '01.2.3', '1.2', '../1.2.3', '1.2.3-rc.0', '1.2.3+build', '1١.2.3'):
    refused(lambda: release.metadata(version, f'## [{version}]\nNotes\n'))
for changelog in ('## [Unreleased]\nNotes\n', '## [1.2.3]\n',
                  '## [1.2.3]\nFirst\n## [1.2.3]\nSecond\n'):
    refused(lambda: release.metadata('1.2.3', changelog))
refused(lambda: release.metadata('1.2.3', '## [1.2.3]\nNotes\n', 'v1.2.4'))

revision = 'a' * 40
run = dict(head_sha=revision, head_branch='main', event='push',
           run_number=2, run_attempt=1, status='completed', conclusion='success')
assert release.passed([run], revision)
assert not release.passed([], revision)
for override in (dict(head_sha='b'*40), dict(head_branch='feature'), dict(event='pull_request'),
                 dict(status='in_progress'), dict(conclusion='failure')):
    assert not release.passed([{**run, **override}], revision)
assert not release.passed([run, {**run, 'run_attempt': 2, 'conclusion': 'failure'}], revision)
assert not release.passed([run, {**run, 'run_number': 3, 'status': 'queued', 'conclusion': None}], revision)

with tempfile.TemporaryDirectory(prefix='modesty-release-test-') as temporary:
    base = Path(temporary)
    source = base / 'source'
    source.mkdir()
    subprocess.run(['git', 'init', '--quiet', str(source)], check=True)
    for name, body in {'install.sh': '#!/bin/sh\nprintf "installer\\n"\n',
                       'LICENSE': 'license', 'THIRD_PARTY.md': 'notices',
                       'VERSION': '1.2.3', 'README.md': 'installation',
                       '.gitignore': 'private/\n'}.items():
        (source / name).write_text(body)
    (source / 'install.sh').chmod(0o755)
    subprocess.run(['git', 'add', '.'], cwd=source, check=True)
    tree = release.git(source, 'write-tree')  # Git tree only; never create a commit.
    (source / 'untracked.key').write_text('secret')
    (source / 'private').mkdir()
    (source / 'private/research.md').write_text('private')
    refused(lambda: release.package(source, tree, '1.2.3', 'Notes\n', source / 'output'))
    names = release.package(source, tree, '1.2.3', 'Notes\n', base / 'first')
    release.package(source, tree, '1.2.3', 'Notes\n', base / 'second')
    refused(lambda: release.package(source, tree, '1.2.3', 'Notes\n', base / 'first'))
    for name in names:
        assert (base / 'first' / name).read_bytes() == (base / 'second' / name).read_bytes(), name
    for line in (base / 'first/SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ')
        assert hashlib.sha256((base / 'first' / name).read_bytes()).hexdigest() == digest
    prefix = 'Modesty-1.2.3/'
    tracked = set(release.git(source, 'ls-tree', '-r', '--name-only', tree).splitlines())
    with tarfile.open(base / 'first' / names[0]) as archive:
        assert {member.name.removeprefix(prefix) for member in archive if member.isfile()} == tracked
        assert archive.getmember(prefix + 'install.sh').mode & 0o111
        assert all(member.mtime == 946684800 for member in archive)
    with zipfile.ZipFile(base / 'first' / names[1]) as archive:
        assert {name.removeprefix(prefix) for name in archive.namelist() if not name.endswith('/')} == tracked
        assert archive.getinfo(prefix + 'install.sh').external_attr >> 16 & 0o111
        assert all(item.date_time == (2000, 1, 1, 0, 0, 0) for item in archive.infolist())
    assert tree in (base / 'first/release-notes.md').read_text()
print('PASS release metadata, exact CI gates, deterministic archives, checksums and private-file exclusion')
