"""Inspect the installed runtime without installing or replacing packages."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from desktop_environment import clean_environment


def version(text):
    match = re.search(r'(?<!\d)(\d+)\.(\d+)(?:\.(\d+))?', text)
    if not match:
        raise ValueError('Could not identify version: ' + text[:160])
    return tuple(int(n or 0) for n in match.groups())


def capture(argv):
    result = subprocess.run(argv, capture_output=True, text=True,
                            env=clean_environment(), timeout=12)
    if result.returncode:
        raise RuntimeError('Cannot run ' + argv[0] + ': ' + (result.stderr or result.stdout)[-800:])
    return result.stdout + result.stderr


def inspect(root, live=True):
    requirements = json.loads((Path(root)/'runtime-requirements.json').read_text())
    if requirements.get('schema') != 1:
        raise RuntimeError('This update needs a newer updater. Update manually after reviewing its requirements.')
    errors, warnings, versions = [], [], {}
    for executable, package in requirements['executables'].items():
        if not shutil.which(executable):
            errors.append(f'Missing {executable}. Required package: {package}.')
    for module, package in requirements['pythonModules'].items():
        if importlib.util.find_spec(module) is None:
            errors.append(f'Missing Python module {module}. Required package: {package}.')
    for name, command in [('hyprland', ['Hyprland', '--version']), ('quickshell', ['quickshell', '--version'])]:
        if not shutil.which(command[0]):
            continue
        try:
            output = capture(command)
            found = version(output)
            versions[name] = '.'.join(map(str, found))
            bounds = requirements[name]
            if not tuple(bounds['minimum']) <= found < tuple(bounds['before']):
                errors.append(f'{name} {versions[name]} is outside this revision’s supported range '
                              f'{".".join(map(str, bounds["minimum"]))} to below '
                              f'{".".join(map(str, bounds["before"]))}. Keep the current shell or use a compatible revision.')
            if re.search(r'COMPATIBILITY WARNING|Qt.*(?:mismatch|incompatible)', output, re.I):
                errors.append('Quickshell reports a Qt mismatch. Finish a full Arch upgrade and rebuild your installed Quickshell package.')
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as error:
            errors.append(str(error))
    if shutil.which('pacman'):
        modules = {}
        for package in requirements['qtPackages']:
            try:
                found = version(capture(['pacman', '-Q', package]).split()[-1])
                modules[package] = found[:2]
                versions[package] = '.'.join(map(str, found))
            except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired):
                errors.append(f'Missing or unreadable {package}. Complete a full Arch upgrade before updating Modesty.')
        if any(v[0] != requirements['qtMajor'] for v in modules.values()) or len(set(modules.values())) > 1:
            errors.append('Qt modules have different major/minor versions. Complete a full Arch upgrade; partial upgrades are unsupported.')
        if Path('/var/lib/pacman/db.lck').exists():
            errors.append('A package transaction may be running. Wait for it to finish; do not remove the pacman lock.')
    else:
        errors.append('Automatic updates currently require Arch Linux and pacman.')
    if live and os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') and 'hyprland' in versions:
        try:
            running = json.loads(capture(['hyprctl', 'version', '-j']))
            installed = capture(['Hyprland', '--version'])
            if version(running['version']) != version(installed) or running.get('commit') and running['commit'] not in installed:
                errors.append('Running Hyprland differs from the installed binary. Log out and back in before updating Modesty.')
        except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as error:
            errors.append('Cannot verify running Hyprland: ' + str(error))
    warnings.append('Optional Hyprland plugins are not rebuilt by OTA. Run hyprpm update after compositor updates.')
    return dict(ok=not errors, versions=versions, errors=errors, warnings=warnings)


def require(root, live=True):
    report = inspect(root, live)
    if not report['ok']:
        raise RuntimeError('\n'.join(report['errors']))
    return report
