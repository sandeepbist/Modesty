#!/usr/bin/env python3
"""Reject unreachable QML types and missing literal QML/JS imports."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
files = {path: path.read_text() for folder in ('components', 'modules', 'services', 'theme', 'tests')
         for path in (ROOT / folder).rglob('*.qml')}
entries = [ROOT / name for name in ('shell.qml', 'preview.qml', 'typecheck.qml', 'layercheck.qml')]
files.update((path, path.read_text()) for path in entries)
reachable = set(entries)
while True:
    found = set(reachable)
    for path in reachable:
        source = files[path]
        for candidate, text in files.items():
            suffix = r'\s*\.' if 'pragma Singleton' in text else r'\s*\{'
            if re.search(r'\b' + re.escape(candidate.stem) + suffix, source) or candidate.name in source:
                found.add(candidate)
    if found == reachable:
        break
    reachable = found
unused = sorted(str(path.relative_to(ROOT)) for path in files.keys() - reachable)
assert not unused, f'Unreachable QML: {unused}'
for path, source in files.items():
    for relative in re.findall(r'^import\s+"([^"]+)"', source, re.M):
        assert (path.parent / relative).exists(), (path, relative)
print(f'PASS {len(files)} reachable QML files; literal QML/JS imports resolve')
