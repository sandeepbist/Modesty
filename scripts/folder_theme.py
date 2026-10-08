"""Optional GTK folder-color overlay; system icons and custom themes stay intact."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
from installation import atomic

THEMES = ('Modesty-Folders-A', 'Modesty-Folders-B')
SUPPORTED = ('Adwaita', 'Papirus', 'Papirus-Dark', 'Papirus-Light')
NAMES = ('folder', 'folder-open', 'folder-drag-accept', 'folder-documents',
         'folder-download', 'folder-downloads', 'folder-music', 'folder-pictures',
         'folder-videos', 'folder-publicshare', 'folder-templates', 'folder-remote',
         'folder-desktop', 'user-home', 'user-desktop')
OWNER = 'modesty-folder-colors-v1'
SYSTEM_ICONS = Path('/usr/share/icons')
ET.register_namespace('', 'http://www.w3.org/2000/svg')


def data_home():
    return Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')


def write(path, text):
    if path.is_symlink():
        raise RuntimeError('Custom folder-theme symlinks were preserved')
    if path.exists() and path.read_text() == text:
        return
    atomic(path, text.encode())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setting(value=None):
    command = ['gsettings', 'get' if value is None else 'set',
               'org.gnome.desktop.interface', 'icon-theme']
    if value is not None:
        command.append(value)
    return subprocess.run(command, check=True, capture_output=True, text=True,
                          timeout=5).stdout.strip().strip("'")


def mix(color, target, amount):
    return '#'+''.join(f'{round(int(color[i:i+2],16)*(1-amount)+int(target[i:i+2],16)*amount):02x}'
                      for i in (1,3,5))



def contrast(first, second):
    def luminance(value):
        channels = [int(value[i:i+2],16)/255 for i in (1,3,5)]
        return sum((c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4)*w
                   for c,w in zip(channels,(.2126,.7152,.0722)))
    low,high = sorted((luminance(first),luminance(second)))
    return (high+.05)/(low+.05)


def tones(accent, foreground, background):
    # A little surface color calms bright accents without losing icon contrast.
    body = mix(accent, background, .12)
    if contrast(body,background)<3:body=accent
    if contrast(foreground,body)<4.5:
        foreground=max(('#000000','#ffffff'),key=lambda color:contrast(color,body))
    return body,foreground

def recolor(source, base, accent, foreground):
    for value in (accent, foreground):
        if not re.fullmatch(r'#[a-fA-F0-9]{6}', value):
            raise ValueError('Invalid folder palette color')
    expected = '#5294e2' if base.startswith('Papirus') else '#62a0ea'
    if expected not in source.lower():
        raise RuntimeError('Folder SVG format changed; icon theme was preserved')
    if base.startswith('Papirus'):
        colors = {'#5294e2':accent, '#4877b1':mix(accent, '#000000', .24),
                  '#1d344f':foreground}
        return re.sub(r'#[a-fA-F0-9]{6}', lambda m:colors.get(m[0].lower(), m[0]), source)
    # Adwaita's first three paths form the folder; later paths are its emblem.
    tree = ET.fromstring(source)
    colors = {'#62a0ea':accent, '#438de6':mix(accent, '#000000', .18),
              '#a4caee':mix(accent, '#ffffff', .36),
              '#afd4ff':mix(accent, '#ffffff', .48),
              '#c0d5ea':mix(accent, '#ffffff', .58)}
    paths = 0
    for element in tree.iter():
        if element.tag.endswith('}path'):
            paths += 1
        for key, value in list(element.attrib.items()):
            if element.tag.endswith('}path') and paths > 3 and value.lower() in colors:
                element.set(key, foreground)
            else:
                element.set(key, re.sub(r'#[a-fA-F0-9]{6}', lambda m:colors.get(m[0].lower(), m[0]), value))
    return ET.tostring(tree, encoding='unicode')


def owned(directory):
    marker = directory/'.modesty-generated.json'
    if directory.is_symlink() or marker.is_symlink() or (directory/'48x48').is_symlink() or (directory/'48x48/places').is_symlink():
        raise RuntimeError('Folder overlay path must not be a symlink')
    if not directory.exists():
        return None
    if not marker.is_file():
        raise RuntimeError('Folder overlay directory already contains unowned files')
    record = json.loads(marker.read_text())
    if record.get('owner') != OWNER or not isinstance(record.get('files'), dict):
        raise RuntimeError('Folder overlay directory belongs to another application')
    allowed = {'index.theme', *('48x48/places/'+n+'.svg' for n in NAMES)}
    if any(name not in allowed or not isinstance(sha,str) or not re.fullmatch(r'[a-f0-9]{64}', sha) for name,sha in record['files'].items()):
        raise RuntimeError('Invalid generated folder-icon record')
    return record


def cleanup():
    for name in THEMES:
        directory = data_home()/'icons'/name
        record = owned(directory)
        if not record:
            continue
        # Delete only known generated bytes. Keep edits and unrelated files.
        for relative, sha in record['files'].items():
            path = directory/relative
            if path.is_file() and not path.is_symlink() and digest(path) == sha:
                path.unlink()
        for relative in ('48x48/places', '48x48'):
            try:(directory/relative).rmdir()
            except OSError:pass
        if list(directory.iterdir()) == [directory/'.modesty-generated.json']:
            (directory/'.modesty-generated.json').unlink()
            directory.rmdir()


def restore(state):
    path = state/'folder-theme.json'
    if not path.exists():
        return
    record = json.loads(path.read_text())
    if record.get('owner') != OWNER or record.get('original') not in SUPPORTED:
        raise RuntimeError('Invalid folder-theme recovery record')
    if setting() in THEMES:
        setting(record['original'])
    cleanup()
    path.unlink()


def apply(raw, state, enabled):
    record_path = state/'folder-theme.json'
    if not enabled:
        restore(state)
        return
    current = setting()
    record = json.loads(record_path.read_text()) if record_path.exists() else {}
    base = record.get('original') if current in THEMES and record.get('owner') == OWNER else current
    if base not in SUPPORTED:
        raise RuntimeError('Palette folders support Adwaita and Papirus; your icon theme was preserved')
    if (data_home()/'icons'/base).exists() or (Path.home()/'.icons'/base).exists():
        raise RuntimeError('Custom local icon-theme overrides were preserved; disable Palette folders')
    accent = raw['colors']['primary']['default']['color']
    foreground = raw['colors']['on_primary']['default']['color']
    background = raw['colors']['surface']['default']['color']
    if not all(re.fullmatch(r'#[a-fA-F0-9]{6}', value) for value in (accent,foreground,background)):
        raise ValueError('Invalid folder palette color')
    accent,foreground=tones(accent,foreground,background)
    folder = '48x48' if base.startswith('Papirus') else 'scalable'
    icons = {}
    for name in NAMES:
        filename = name.replace('folder', 'folder-blue', 1).replace('user-', 'user-blue-', 1) if base.startswith('Papirus') else name
        source = SYSTEM_ICONS/base/folder/'places'/(filename+'.svg')
        if source.is_file():
            icons['48x48/places/'+name+'.svg'] = recolor(source.read_text(), base, accent, foreground)
    if '48x48/places/folder.svg' not in icons:
        raise RuntimeError('Supported folder SVGs are unavailable; icon theme was preserved')
    icons['index.theme'] = ('[Icon Theme]\nName=Modesty palette folders\nInherits='+base+
        '\nDirectories=48x48/places\n\n[48x48/places]\nSize=48\nType=Scalable\nMinSize=16\nMaxSize=512\nContext=Places\n')
    hashes = {name:hashlib.sha256(text.encode()).hexdigest() for name,text in icons.items()}
    if current in THEMES:
        existing = owned(data_home()/'icons'/current)
        if existing and any((data_home()/'icons'/current/name).is_symlink() for name in existing['files']):
            raise RuntimeError('Custom folder-icon symlinks were preserved')
        if existing and existing['files'] == hashes and all((data_home()/'icons'/current/name).is_file() and digest(data_home()/'icons'/current/name)==sha for name,sha in hashes.items()):
            return
    # Two bounded slots force GTK to refresh icons without growing a cache.
    active = THEMES[1] if current == THEMES[0] else THEMES[0]
    directory = data_home()/'icons'/active
    existing = owned(directory)
    if any((directory/name).is_symlink() for name in icons):
        raise RuntimeError('Custom folder-icon symlinks were preserved')
    if existing and any((directory/name).exists() and digest(directory/name)!=sha for name,sha in existing['files'].items()):
        raise RuntimeError('Edited generated folder icons were preserved')
    if any((directory/name).exists() and name not in (existing or {}).get('files', {}) for name in icons):
        raise RuntimeError('Existing custom folder-icon files were preserved')
    for name,text in icons.items():write(directory/name, text)
    write(directory/'.modesty-generated.json', json.dumps(dict(owner=OWNER, files=hashes)))
    # Save recovery before changing the desktop setting.
    write(record_path, json.dumps(dict(owner=OWNER, original=base)))
    setting(active)
