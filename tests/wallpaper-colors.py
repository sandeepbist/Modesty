#!/usr/bin/env python3
"""Check real Matugen extraction and production refinement across wallpaper tones."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import wallpaper

with tempfile.TemporaryDirectory(prefix='modesty-wallpaper-colors-') as temporary:
    directory=Path(temporary)
    with patch.dict(os.environ, XDG_CACHE_HOME=str(directory/'cache')), patch.object(wallpaper,'IMAGE_CACHE',directory/'images'):
        paths=list((ROOT/'setup/wallpapers').glob('*'))
        for name,color in [('gray','#707070'),('dark','#101010'),('white','#fafafa'),('violet','#ad20ee'),('warm','#e99820'),('green','#32b680'),('blue','#358fdf')]:
            path=directory/(name+'.png');Image.new('RGB',(80,60),color).save(path);paths.append(path)
        variants=[]
        for path in paths:
            if path.suffix.lower() not in ('.jpg','.png'):continue
            colors=wallpaper.generate_palettes(path)
            variants.extend(dict(label=path.stem+'/'+mode,colors=value) for mode,value in colors.items())
        source=directory/'variants.json';source.write_text(json.dumps(variants))
        subprocess.run(['node','tests/palette.cjs',str(source)],cwd=ROOT,check=True,timeout=10)
print('PASS real wallpaper palette extraction: bundled photographs, grayscale and saturated tones; dark/light labels and selections')
