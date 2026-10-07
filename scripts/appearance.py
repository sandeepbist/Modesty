#!/usr/bin/env python3
"""Persist shell appearance and update only Hyprland's theme colors."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import importlib.util


def colors_config(colors):
    if not all(re.fullmatch(r'#[0-9a-fA-F]{6}', colors.get(k, '')) for k in ('accent', 'subtext', 'bg')):
        raise ValueError('Invalid desktop theme colors')
    accent, inactive, background = (colors[k][1:] for k in ('accent', 'subtext', 'bg'))
    # A tinted shadow follows the theme; opacity and geometry remain restrained.
    tint = ''.join(f'{round(int(accent[i:i+2],16)*.3+int(background[i:i+2],16)*.7):02x}' for i in (0,2,4))
    return 'hl.config({general={col={active_border="rgba(' + accent + 'e6)",inactive_border="rgba(' + inactive + '24)"}},decoration={shadow={color="rgba(' + tint + '28)"}}})'


def apply(data, directory):
    if not isinstance(data.get('paletteName'), str) or data.get('mode') not in ('dark','light'):
        raise ValueError('A palette and light/dark mode are required')
    lua = colors_config(data['colors'])
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w',dir=directory,prefix='.appearance-',delete=False) as stream:
        json.dump({'paletteName':data['paletteName'],'mode':data['mode']},stream)
        temporary=Path(stream.name)
    temporary.replace(directory/'appearance.json')
    subprocess.run(['hyprctl','eval',lua],check=True,capture_output=True,text=True,timeout=5)
    raw=data.get('wallpaperData')
    if raw and data['paletteName']=='wallpaper':
        # Match the shell's resolved roles, including its contrast correction.
        # Keep Matugen's remaining roles intact for each application's hierarchy.
        raw=json.loads(json.dumps(raw))
        for role,key in {'primary':'accent','on_surface':'text','on_surface_variant':'subtext',
                         'surface':'bg','surface_dim':'bg','background':'bg','surface_container':'surface',
                         'on_primary':'accentText'}.items():
            value=data['colors'].get(key)
            if not re.fullmatch(r'#[0-9a-fA-F]{6}',value or ''):raise ValueError('Invalid shared palette role')
            raw['colors'].setdefault(role,{})[data['mode']]={'color':value}
            raw['colors'][role]['default']={'color':value}
        (directory/'wallpaper-data.json').write_text(json.dumps(raw))
        if data.get('wallpaperVariants'):(directory/'wallpaper-palette.json').write_text(json.dumps(data['wallpaperVariants']))
    else:
        # Named palettes must reach applications too; never reuse stale wallpaper colors.
        c=data['colors']
        roles={'primary':'accent','on_primary':'bg','secondary':'yellow','tertiary':'green',
               'surface':'bg','surface_container_lowest':'bg','surface_container_low':'surface',
               'surface_container':'surface','surface_container_high':'surface','surface_container_highest':'surface',
               'on_surface':'text','outline':'subtext','outline_variant':'subtext','shadow':'bg','error':'red'}
        raw={'colors':{role:{'default':{'color':c[key]},data['mode']:{'color':c[key]}} for role,key in roles.items()}}
    spec=importlib.util.spec_from_file_location('app_theme',Path(__file__).with_name('app-theme.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    errors=[]
    try:module.apply(raw,data['mode'],directory,data.get('targets',{}))
    except Exception as error:errors.append(str(error))
    if shutil.which('gsettings'):
        subprocess.run(['gsettings','set','org.gnome.desktop.interface','color-scheme','prefer-'+data['mode']],check=True,capture_output=True,text=True,timeout=5)
        if data.get('targets',{}).get('gtk'):
            theme='adw-gtk3-dark' if data['mode']=='dark' else 'adw-gtk3'
            if (Path('/usr/share/themes')/theme).exists():
                subprocess.run(['gsettings','set','org.gnome.desktop.interface','gtk-theme',theme],check=True,capture_output=True,text=True,timeout=5)
    if errors:raise RuntimeError('; '.join(errors))


if __name__ == '__main__':
    try:
        apply(json.loads(sys.argv[1]), Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local/state')/'modesty')
        print(json.dumps({'ok':True}))
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error)}));sys.exit(1)
