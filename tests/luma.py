#!/usr/bin/env python3
"""Check extracted conversation boundaries and observed action validation offline."""
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from luma.actions import validated_action
from luma.observations import clock, hardware
from luma.protocol import clean_messages, stream_answer

for name in ('volume', 'brightness'):
    assert validated_action({'name': name, 'args': {'level': 41}})['args'] == {'level': 41}
    for value in (-1, 101, True, math.nan, math.inf, '41'):
        try:
            validated_action({'name': name, 'args': {'level': value}})
        except ValueError:
            pass
        else:
            raise AssertionError((name, value))
for action in ({'name': 'poweroff', 'args': {}},
               {'name': 'open_app', 'args': {'id': 'missing.desktop'}},
               {'name': 'open_panel', 'args': {'panel': 'missing'}}):
    try:
        validated_action(action)
    except ValueError:
        pass
    else:
        raise AssertionError(action)
app = {'id': 'foot.desktop', 'name': 'Foot'}
assert validated_action({'name': 'open_app', 'args': {'id': app['id']}}, [app])['label'] == 'Open Foot'
assert clean_messages([None, {}, {'role': 'user', 'text': 'Hello'}])[-1]['text'] == 'Hello'
raw = json.dumps({'answer': 'Line one\nLine two 🐈'})
_, answer = stream_answer(raw)
assert answer == 'Line one\nLine two 🐈'
assert clock(['UTC', 'Asia/Kolkata'])['readings'][1]['zone'] == 'Asia/Kolkata'
with patch('luma.observations.subprocess.run', return_value=subprocess.CompletedProcess(
        [], 0, json.dumps({'chip': {'CPU': {'temp1_input': 42, 'temp1_max': 95},
                                  'broken': {'temp2_input': 49, 'temp2_fault': 1}}}), '')):
    readings = hardware()['readings']
    assert len(readings) == 1 and readings[0]['value'] == 42 and readings[0]['max'] == 95
# Loading the public CLI must still expose its imported helpers without making requests.
spec = importlib.util.spec_from_file_location('assistant', ROOT / 'scripts/luma-assistant.py')
assistant = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assistant)
assert assistant.validated_action is validated_action
print('PASS Luma action boundaries, streamed text, conversation, sensors, clock and CLI imports')
