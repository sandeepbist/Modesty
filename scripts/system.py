#!/usr/bin/env python3
"""Bounded desktop queries and explicit actions; never execute user text as a shell."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import wallpaper as wallpaper_tools

STATE = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'modesty'
WALLS = Path(os.environ.get('MODESTY_WALLPAPERS') or Path.home() / 'Pictures/Wallpapers').expanduser()
WALL_CACHE = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache') / 'modesty' / 'wallpapers.json'

def run(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True, timeout=8)
    if check and p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or f'{args[0]} failed')
    return p.stdout.strip()

def optional(args):
    try: return run(args)
    except (OSError, RuntimeError, subprocess.TimeoutExpired): return ''

def wallpaper_files():
    if not WALLS.is_dir(): return []
    return [p.resolve() for p in sorted(WALLS.iterdir()) if p.is_file() and p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}]

def wallpapers(options=None):
    try: monitors = json.loads(optional(['hyprctl','monitors','-j']))
    except ValueError: monitors = []
    displays = [[m['width'],m['height']] for m in monitors if m.get('width') and m.get('height')]
    files = wallpaper_files()
    signature = [[str(path), path.stat().st_mtime_ns, path.stat().st_size] for path in files]
    key = [3, displays, signature]
    result = None
    try:
        cached = json.loads(WALL_CACHE.read_text())
        if cached.get('key') == key and isinstance(cached.get('wallpapers'), list):
            result = cached['wallpapers']
        else: result = None
    except (OSError, ValueError, AttributeError): pass
    if result is None:
        result = []
        for path in files:
            try:
                thumb = wallpaper_tools.cached_image(path, 'preview')
                display = wallpaper_tools.cached_image(path, 'display', displays)
            except (OSError, ValueError): thumb = display = path
            result.append({'name':path.name,'path':str(path),'url':path.as_uri(),'thumbnailUrl':thumb.as_uri(),'displayUrl':display.as_uri()})
        wallpaper_tools.write_json(WALL_CACHE, {'key':key, 'wallpapers':result})
    if options:
        result = [dict(entry) for entry in result]
        for entry in result:
            data = wallpaper_tools.cached_data(Path(entry['path']), options)
            if data:
                try:
                    entry['palette'] = wallpaper_tools.extract_palettes(data)
                    entry['paletteData'] = data
                except (KeyError, TypeError, ValueError): pass
    return result

def snapshot():
    backlights = sorted(Path('/sys/class/backlight').glob('*'))
    backlight = backlights[0] if backlights else None
    maximum = int((backlight / 'max_brightness').read_text()) if backlight else 1
    # Match the native sysfs watcher exactly. Rounded brightnessctl percentages
    # caused a false brightness event whenever the control center refreshed.
    value = int((backlight / 'brightness').read_text()) / maximum if backlight and maximum else 0
    current = ''
    backend = 'native'
    try:
        saved = json.loads((STATE / 'wallpaper.json').read_text())
        current = saved['path']; backend = saved.get('backend', 'native')
    except (OSError, ValueError, KeyError): pass
    inherited = ''
    try:
        candidate = (STATE / 'inherited-wallpaper.txt').read_text().strip()
        if Path(candidate).is_file(): inherited = candidate
    except OSError: pass
    if not current and os.environ.get('MODESTY_COMPAT') == '1': current = inherited
    if backend != 'native' and current and os.environ.get("MODESTY_PREVIEW") != "1":
        wallpaper_tools.write_json(STATE / 'wallpaper.json', {'path':current, 'backend':'native'})
    backend = 'native'
    display = wallpaper_tools.display_url(Path(current)) if current else ''
    try: lock_desktop = json.loads(optional(['hyprctl','-j','getoption','misc:session_lock_xray'])).get('bool', False) is True
    except (ValueError, AttributeError): lock_desktop = False
    return dict(lockDesktopVisible=lock_desktop,lockWallpaper=current or inherited, backlightPath=str(backlight) if backlight else '', maxBrightness=maximum, brightness=value, brightnessAvailable=bool(backlight), wallpaper=current, wallpaperDisplay=display, wallpaperBackend=backend, matugenAvailable=bool(shutil.which('matugen')))

def action(name, value=''):
    if name == 'wifi': run(['nmcli', 'radio', 'wifi', 'on' if value == 'true' else 'off'])
    elif name == 'bluetooth': run(['bluetoothctl', 'power', 'on' if value == 'true' else 'off'])
    elif name == 'brightness': run(['brightnessctl', 'set', f'{max(1, min(100, round(float(value) * 100)))}%'])
    elif name == 'palette':
        options=json.loads(value)
        path=Path(options['path']).resolve()
        if path not in wallpaper_files(): raise ValueError('Choose an image from your wallpaper folder')
        data=wallpaper_tools.generate_data(path,options)
        palette=wallpaper_tools.extract_palettes(data)
        return dict(ok=True,path=str(path),palette=palette,raw=data,key=options.get('key',''))
    elif name == 'wallpaper':
        options = json.loads(value) if value.startswith('{') else {'path': value}
        path = Path(options['path']).resolve()
        if path not in wallpaper_files(): raise ValueError('Choose an image from your wallpaper folder')
        return wallpaper_tools.apply_wallpaper(path, STATE)
    elif name in ('reboot', 'poweroff'): run(['systemctl', name])
    elif name == 'logout':
        if shutil.which('hyprshutdown'): run(['hyprshutdown'])
        else: run(['hyprctl', 'eval', 'hl.dispatch(hl.dsp.exit())'])
    else: raise ValueError('Unknown action')
    return {'ok': True}

if __name__ == '__main__':
    try:
        mode = sys.argv[1]
        result = snapshot() if mode == 'snapshot' else wallpapers(json.loads(sys.argv[2]) if len(sys.argv) > 2 else None) if mode == 'wallpapers' else action(mode, sys.argv[2] if len(sys.argv) > 2 else '')
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        sys.exit(1)
