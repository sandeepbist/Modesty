#!/usr/bin/env python3
"""Atomically save the shell's preference document."""
import json
import os
from pathlib import Path
import sys
import tempfile

def save(data, directory):
    directory.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=directory, prefix='.preferences-', delete=False) as stream:
            temp = Path(stream.name)
            json.dump(data, stream)
        temp.replace(directory / 'preferences.json')
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)

if __name__ == '__main__':
    save(json.loads(sys.argv[1]), Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'modesty')
