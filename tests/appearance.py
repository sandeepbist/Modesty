#!/usr/bin/env python3
"""Check dual-mode extraction and narrowly scoped desktop color synchronization."""
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import appearance
import wallpaper
names=['surface','surface_dim','surface_container','on_surface','on_surface_variant','primary','tertiary','secondary','error']
colors={name:{mode:{'color':'#123456' if mode=='dark' else '#abcdef'} for mode in ['dark','light']} for name in names}
with tempfile.TemporaryDirectory() as tmp:
    directory=Path(tmp); sample=directory/'sample.png'
    Image.new('RGB',(16,16),'#123456').save(sample)
    with (patch.dict(os.environ,{'XDG_CACHE_HOME':tmp}),
          patch.object(wallpaper,'IMAGE_CACHE',directory/'images'),
          patch.object(wallpaper,'command',return_value=json.dumps({'colors':colors})) as command):
        variants=wallpaper.generate_palettes(sample)
        assert variants['dark']['accent']=='#123456' and variants['light']['accent']=='#abcdef'
        assert '--dry-run' in command.call_args.args[0]
with (tempfile.TemporaryDirectory() as tmp,
      patch.dict(os.environ,{'XDG_CONFIG_HOME':str(Path(tmp)/'config')}),
      patch.object(appearance.subprocess,'run') as run,
      patch.object(appearance.shutil,'which',return_value='/usr/bin/gsettings')):
    data={'paletteName':'wallpaper','mode':'light','colors':dict(variants['light'],accent='#123456',subtext='#abcdef',bg='#fafafa')}
    appearance.apply(data,Path(tmp))
    assert json.loads((Path(tmp)/'appearance.json').read_text())=={'paletteName':'wallpaper','mode':'light'}
    lua=run.call_args_list[0].args[0][-1]
    assert 'active_border' in lua and 'shadow' in lua and 'rgba(123456e6)' in lua
    assert all(word not in lua for word in ['gaps','rounding','opacity','range','border_size'])
    assert any(call.args[0]==['gsettings','set','org.gnome.desktop.interface','color-scheme','prefer-light'] for call in run.call_args_list)
    try:appearance.colors_config({'accent':'#123456);evil()','subtext':'#aaaaaa','bg':'#ffffff'})
    except ValueError:pass
    else:raise AssertionError('Invalid color accepted')
print('PASS Matugen dark/light variants, no hooks, mode persistence, color-only compositor updates')
