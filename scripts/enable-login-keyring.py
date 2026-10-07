#!/usr/bin/env python3
"""Add optional GNOME Keyring integration to greetd, with a root-owned backup."""
import argparse
import datetime
import os
from pathlib import Path
import shutil
import tempfile

PAM = Path('/etc/pam.d/greetd')
EXPECTED = '#%PAM-1.0\nauth    include   system-local-login\naccount   include   system-local-login\nsession    include   system-local-login\n'
UPDATED = '#%PAM-1.0\nauth    include   system-local-login\nauth    optional  pam_gnome_keyring.so\naccount   include   system-local-login\nsession    include   system-local-login\nsession    optional  pam_gnome_keyring.so auto_start\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not Path('/usr/lib/security/pam_gnome_keyring.so').is_file():
        raise SystemExit('GNOME Keyring PAM module is not installed.')
    original = PAM.read_text()
    if original == UPDATED:
        print('Login keyring integration is already installed.')
        return
    if original != EXPECTED or PAM.is_symlink():
        raise SystemExit('greetd PAM configuration differs from the reviewed version; no changes made.')
    if not args.apply:
        print('Ready: add optional keyring auth and session lines to /etc/pam.d/greetd.')
        print('Existing authentication requirements stay unchanged. Takes effect at next password sign-in.')
        return
    if os.geteuid() != 0:
        raise SystemExit('Administrator authentication is required to update greetd PAM.')
    backup = PAM.with_name('greetd.modesty-backup-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(PAM, backup)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=PAM.parent, prefix='.modesty-greetd-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(UPDATED)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(PAM.stat().st_mode & 0o777)
        temporary.replace(PAM)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    print('Installed. Backup: ' + str(backup))
    print('Sign in normally with your password next time. No logout is needed now.')


if __name__ == '__main__':
    main()
