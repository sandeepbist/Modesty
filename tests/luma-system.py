#!/usr/bin/env python3
"""Check credential paths, command consent and the real read-only sandbox."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('system_tools', ROOT / 'scripts/luma-system.py')
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)

for path in (Path.home() / '.netrc', tools.CONFIG / 'gh/hosts.yml',
             Path.home() / '.t3/userdata/clerk-tokens.json',
             Path.home() / '.codex/auth.json',
             tools.DATA / 'fish/fish_history', Path('/proc/self/environ'),
             Path('/tmp/.env.local/secrets.txt')):
    try:
        tools.checked_path(str(path))
    except ValueError:
        pass
    else:
        raise AssertionError('Protected path accepted: ' + str(path))

with tempfile.TemporaryDirectory(prefix='modesty-security-') as directory:
    folder = Path(directory)
    secret = folder / 'credential.txt'
    secret.write_text('dummy-secret')
    alias = folder / 'alias.txt'
    alias.symlink_to(secret)
    with patch.object(tools, 'PROTECTED', [*tools.PROTECTED, secret]):
        try:
            tools.checked_path(str(alias))
        except ValueError:
            pass
        else:
            raise AssertionError('Symlink bypassed protected path')
        call = tools.validated(dict(name='run_command', purpose='Check sandbox',
                                    argv=['cat', str(secret)], cwd=directory))
        try:
            tools.command(call)
        except ValueError:
            pass
        else:
            raise AssertionError('Command ran without approval')
        result = tools.command(call, approved=True)
        assert not result['stdout'] and 'dummy-secret' not in result['stderr'], result
        call['argv'] = [sys.executable, '-c',
                        'import os;print("MODESTY_TEST_SECRET" in os.environ)']
        with patch.dict(os.environ, MODESTY_TEST_SECRET='dummy-secret'):
            result = tools.command(call, approved=True)
        assert result['ok'] and result['stdout'].strip() == 'False', result
        call['argv'] = ['touch', str(folder / 'unexpected')]
        assert not tools.command(call, approved=True)['ok']
        assert not (folder / 'unexpected').exists()
print('PASS credential paths, symlink checks, command consent and real sandbox isolation')
