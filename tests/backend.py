#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))

def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / 'scripts' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
system, prefs = module('system'), module('preferences')
with tempfile.TemporaryDirectory() as tmp:
    directory=Path(tmp); walls=directory/'walls'; walls.mkdir(); state=directory/'state'
    tricky=walls/"quote ' and $().png"; tricky.write_bytes(b'fake test image')
    with (patch.object(system,'WALLS',walls), patch.object(system,'STATE',state),
          patch.object(system,'WALL_CACHE',directory/'wallpapers.json'),
          patch.object(system,'optional',return_value='[]'),
          patch.object(system.wallpaper_tools,'cached_image',side_effect=lambda path,*args:Path(path)),
          patch.object(system.wallpaper_tools,'display_url',return_value=tricky.as_uri()),
          patch.object(system,'run') as run):
        assert system.wallpapers()[0]['path'] == str(tricky)
        system.action('wallpaper',str(tricky))
        assert json.loads((state/'wallpaper.json').read_text())['path']==str(tricky)
        run.assert_not_called()
        try: system.action('wallpaper','/tmp/not-in-folder.png')
        except ValueError: pass
        else: raise AssertionError('Out-of-folder wallpaper accepted')
        system.action('brightness','8')
        run.assert_called_once_with(['brightnessctl','set','100%'])
    prefs.save({'motion':'gentle','contextVolume':False},state)
    assert json.loads((state/'preferences.json').read_text())['motion']=='gentle'
    assert not list(state.glob('.preferences-*'))
print('PASS wallpaper path validation, no shell interpolation, brightness clamp, atomic preferences')

# A rounded snapshot must not generate an unsolicited brightness OSD on panel open.
import os
with tempfile.TemporaryDirectory() as tmp:
    backlights=Path(tmp)/'backlights';device=backlights/'test-panel';device.mkdir(parents=True)
    (device/'max_brightness').write_text('1003')
    (device/'brightness').write_text('751')
    real_path=Path
    with patch.object(system,'Path',side_effect=lambda value:backlights if value=='/sys/class/backlight' else real_path(value)), patch.object(system,'STATE',Path(tmp)/'state'), patch.dict(os.environ,{'MODESTY_PREVIEW':'1'}):
        snapshot=system.snapshot()
        assert snapshot['brightness']==751/1003
        assert snapshot['brightnessAvailable']
print('PASS snapshot preserves exact backlight value without percentage rounding')

# An unrelated host ending in the same text must retain its own attribution.
import io
canvas = module('command-canvas')
for hostname in ('wikipedia.org', 'en.wikipedia.org', 'www.wikipedia.org',
                 'evilwikipedia.org', 'wikipedia.org.example.com', 'example.com'):
    source = f'https://{hostname}/wiki/Test'
    response = io.BytesIO(json.dumps({'AbstractText': 'Test overview', 'AbstractURL': source}).encode())
    with patch.object(canvas, 'urlopen', return_value=response), patch.object(canvas, 'emit') as emit:
        canvas.quick_answer('What is testing?')
    answer = emit.call_args.kwargs['answer']
    assert answer['source'] == source
    assert answer['sourceName'] == ('Wikipedia' if hostname in ('wikipedia.org', 'en.wikipedia.org', 'www.wikipedia.org') else hostname)
print('PASS instant-answer attribution uses actual Wikipedia domains and preserves unrelated hostnames')
