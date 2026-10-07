#!/usr/bin/env python3
"""Validate release metadata and package a committed source snapshot; never publish."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'sandeepbist/Modesty'
VERSION = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-rc\.[1-9]\d*)?', re.ASCII)


def git(root, *args, binary=False):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env['TZ'] = 'UTC'
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'tar.umask=0022', *args],
                            cwd=root, env=env, capture_output=True, timeout=120)
    if result.returncode:
        raise ValueError(result.stderr.decode().strip())
    return result.stdout if binary else result.stdout.decode().strip()


def metadata(version, changelog, tag=None):
    version = version.strip()
    if not VERSION.fullmatch(version):
        raise ValueError('VERSION must be X.Y.Z or X.Y.Z-rc.N, without a v prefix.')
    if tag is not None and tag != 'v' + version:
        raise ValueError('Release tag must match VERSION exactly.')
    sections = re.split(r'^## ', changelog, flags=re.M)[1:]
    matches = [s for s in sections if s.splitlines()[0] == f'[{version}]']
    if len(matches) != 1 or not matches[0].partition('\n')[2].strip():
        raise ValueError('CHANGELOG.md needs exactly one nonempty section for VERSION.')
    return version, matches[0].partition('\n')[2].strip() + '\n'


def check(root=ROOT):
    return metadata((root / 'VERSION').read_text(), (root / 'CHANGELOG.md').read_text())


def passed(runs, revision):
    # The newest push run for this exact commit wins, including failed reruns.
    matches = [r for r in runs if r.get('head_sha') == revision
               and r.get('head_branch') == 'main' and r.get('event') == 'push']
    latest = max(matches, key=lambda r: (r['run_number'], r.get('run_attempt', 1)), default={})
    return latest.get('status') == 'completed' and latest.get('conclusion') == 'success'


def verify_checks(root, revision):
    try:
        git(root, 'merge-base', '--is-ancestor', revision, 'origin/main')
    except ValueError as error:
        raise ValueError('Release commit must belong to main.') from error
    for workflow in ('checks.yml', 'codeql.yml'):
        endpoint = f'repos/{REPOSITORY}/actions/workflows/{workflow}/runs?branch=main&event=push&head_sha={revision}&per_page=100'
        result = subprocess.run(['gh', 'api', endpoint], capture_output=True, text=True, check=True, timeout=30)
        if not passed(json.loads(result.stdout)['workflow_runs'], revision):
            raise ValueError(f'{workflow} has not passed for the exact release commit.')


def package(root, revision, version, notes, output):
    output = output.resolve()
    if output == root.resolve() or root.resolve() in output.parents:
        raise ValueError('Keep release outputs outside the source checkout.')
    output.mkdir(parents=True, exist_ok=True)
    names = (f'Modesty-{version}.tar.gz', f'Modesty-{version}.zip', 'SHA256SUMS', 'release-notes.md')
    if any((output / name).exists() for name in names):
        raise ValueError('Release output already exists; use a fresh output directory.')
    prefix = f'Modesty-{version}/'
    # Explicit timestamps and gzip headers make the same tree reproducible.
    with tempfile.TemporaryDirectory(prefix='modesty-release-', dir=output) as temporary:
        staging = Path(temporary)
        tar = git(root, 'archive', '--format=tar', '--mtime=2000-01-01T00:00:00Z', f'--prefix={prefix}', revision, binary=True)
        with (staging / names[0]).open('wb') as handle:
            with gzip.GzipFile(filename='', fileobj=handle, mode='wb', mtime=0) as compressed:
                compressed.write(tar)
        (staging / names[1]).write_bytes(git(root, 'archive', '--format=zip', '--mtime=2000-01-01T00:00:00Z', f'--prefix={prefix}', revision, binary=True))
        checksums = ''.join(f'{hashlib.sha256((staging / name).read_bytes()).hexdigest()}  {name}\n' for name in names[:2])
        (staging / names[2]).write_text(checksums)
        (staging / names[3]).write_text(f'# Modesty {version}\n\n{notes}\nSource revision: `{revision}`\n\n'
                                      'Verify downloads with `sha256sum -c SHA256SUMS`.\n'
                                      'Archives contain source and installation defaults, not system packages or voice models.\n'
                                      'Use the official Git checkout on `main` for Settings updates.\n')
        for name in names:
            (staging / name).replace(output / name)
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'build'))
    parser.add_argument('--tag')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify-ci', action='store_true')
    args = parser.parse_args()
    if args.action == 'check':
        version, _ = check()
        print(f'PASS release metadata: {version}')
        return
    if not args.tag or not args.tag.startswith('v') or not VERSION.fullmatch(args.tag[1:]) or args.output is None:
        parser.error('build requires --tag vX.Y.Z and --output outside the checkout')
    revision = git(ROOT, 'rev-parse', '--verify', f'refs/tags/{args.tag}^{{commit}}')
    if git(ROOT, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Build from a clean checkout; tagged source is read as data.')
    version, notes = metadata(git(ROOT, 'show', f'{revision}:VERSION'), git(ROOT, 'show', f'{revision}:CHANGELOG.md'), args.tag)
    if args.verify_ci:
        verify_checks(ROOT, revision)
    for name in package(ROOT, revision, version, notes, args.output):
        print(args.output.resolve() / name)


if __name__ == '__main__':
    main()
