#!/usr/bin/env python3
"""On-demand wallpaper rendering and color extraction; no background polling."""
import json
import hashlib
import os
import re
from pathlib import Path
import subprocess

IMAGE_CACHE = Path(os.environ.get('XDG_CACHE_HOME', Path.home()/'.cache'))/'modesty'/'wallpaper-images'

def cached_image(path, kind, displays=()):
    from PIL import Image, ImageOps
    stat = path.stat()
    if kind == 'display':
        with Image.open(path) as source:
            width, height = source.size
            if source.getexif().get(274) in (5, 6, 7, 8): width, height = height, width
        factor = max((max(mw/width, mh/height) for mw, mh in displays), default=max(1920/width, 1080/height))
        if factor >= .9:
            if path.suffix.lower() in {'.jpg', '.jpeg'}: return path
            size = (width, height)
        else: size = (round(width*factor*1.02), round(height*factor*1.02))
    else:
        size = (400, 260)
    key = hashlib.sha256(json.dumps([str(path), stat.st_mtime_ns, stat.st_size, kind, size, 2 if kind == 'display' else 1]).encode()).hexdigest()
    png = kind != 'display' and path.suffix.lower() in {'.png', '.webp'}
    output = IMAGE_CACHE/(key+('.png' if png else '.jpg'))
    if output.exists(): return output
    IMAGE_CACHE.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        if kind == 'display': image = image.resize(size, Image.Resampling.LANCZOS)
        else: image.thumbnail(size, Image.Resampling.LANCZOS)
        temporary = output.with_suffix(output.suffix+'.tmp')
        if png: image.save(temporary, format='PNG')
        else:
            if 'A' in image.getbands():
                opaque = Image.new('RGB', image.size, (18, 26, 27))
                opaque.paste(image, mask=image.getchannel('A'))
                image = opaque
            image.convert('RGB').save(temporary, format='JPEG', quality=95 if kind == 'display' else 90, subsampling=0)
        temporary.replace(output)
    return output

def command(args, timeout=12):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'{args[0]} failed')
    return result.stdout

def display_url(path):
    try:
        monitors = json.loads(command(['hyprctl', 'monitors', '-j']))
        displays = [(m['width'], m['height']) for m in monitors if m.get('width') and m.get('height')]
        return cached_image(path, 'display', displays).as_uri()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired):
        return path.as_uri()

def palette_options(options=None):
    options=options or {}
    automatic=options.get('automatic',True)
    scheme='scheme-content' if automatic else options.get('scheme','scheme-tonal-spot')
    if scheme not in {'scheme-content','scheme-expressive','scheme-fidelity','scheme-fruit-salad','scheme-monochrome','scheme-neutral','scheme-rainbow','scheme-tonal-spot','scheme-vibrant','scheme-smart'}: scheme='scheme-tonal-spot'
    contrast=.1 if automatic else max(-1,min(1,float(options.get('contrast',0))))
    source=0 if automatic else max(0,min(4,int(options.get('source',0))))
    return automatic,scheme,contrast,source

def palette_cache_path(path, automatic, scheme, contrast, source):
    stat=path.stat()
    key=hashlib.sha256(json.dumps([str(path),stat.st_mtime_ns,stat.st_size,scheme,contrast,source,automatic,5]).encode()).hexdigest()
    cache=Path(os.environ.get('XDG_CACHE_HOME',Path.home()/'.cache'))/'modesty'/'palettes'
    return cache/(key+'.json')

def cached_data(path, options=None):
    try: return json.loads(palette_cache_path(path, *palette_options(options)).read_text())
    except (OSError, ValueError): return None

def generate_data(path, options=None):
    automatic,scheme,contrast,source=palette_options(options)
    saved=palette_cache_path(path, automatic, scheme, contrast, source)
    cache=saved.parent
    cache.mkdir(parents=True,exist_ok=True)
    if saved.exists(): return json.loads(saved.read_text())
    sample=cached_image(path,'preview')
    if automatic:
        # Avoid Matugen's colored fallback on genuinely monochrome artwork.
        # A tiny, one-off sample is sufficient; extraction itself remains Matugen's.
        from PIL import Image
        import colorsys
        with Image.open(sample) as image:
            image.thumbnail((64,64))
            samples=[colorsys.rgb_to_hsv(*(c/255 for c in p)) for p in image.convert('RGB').getdata()]
        if sum(s>.12 and .1<v<.95 for _,s,v in samples)/max(1,len(samples))<.03:
            scheme='scheme-monochrome'
    data=json.loads(command(['matugen','image',str(sample),'--dry-run','--json','hex','--source-color-index',str(source),'--resize-filter','lanczos3','--mode','dark','--type',scheme,'--contrast',str(contrast)],timeout=25))
    data['modesty']={'automatic':automatic,'scheme':scheme,'contrast':contrast,'sourceIndex':source,'sample':'preview'}
    write_json(saved,data)
    for old in sorted(cache.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[80:]: old.unlink(missing_ok=True)
    return data

def extract_palettes(data):
    colors = data['colors']
    def palette(mode):
        def color(name):
            value = colors[name][mode]['color']
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', value): raise ValueError('Invalid generated color')
            return value
        background = color('surface_dim' if mode == 'dark' else 'surface')
        return dict(bg=background, bgSolid=background, surface=color('surface_container'), surfaceSolid=color('surface_container'), text=color('on_surface'), subtext=color('on_surface_variant'), accent=color('primary'), accentText=color('on_primary') if 'on_primary' in colors else background, secondary=color('secondary'), tertiary=color('tertiary'), green='#8fd49a' if mode=='dark' else '#286c39', yellow='#dcbf76' if mode=='dark' else '#805800', red=color('error'))
    return {mode: palette(mode) for mode in ('dark', 'light')}

def generate_palettes(path):
    return extract_palettes(generate_data(path))

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(data))
    temp.replace(path)

def apply_wallpaper(path, state):
    display = display_url(path)
    write_json(state/'wallpaper.json', {'path':str(path), 'backend':'native'})
    return dict(ok=True, wallpaper=str(path), wallpaperDisplay=display, wallpaperBackend='native')
