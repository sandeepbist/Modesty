"""Local artwork catalogue shared by the terminal greeting and settings gallery."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def catalogue():
    result = []
    directory = ROOT / 'assets/terminal/cutouts'
    try:
        entries = json.loads((directory / 'catalogue.json').read_text())
    except (OSError, ValueError):
        entries = []
    for entry in entries:
        path = directory / (entry['id'] + '.png')
        if path.is_file():
            result.append(dict(id='portraits/' + entry['id'] + '-action', title=entry['title'], collection='portraits',
                               image=str(path), ascii=str(path), preview=path.as_uri()))
    directory = ROOT / 'assets/terminal/battle'
    try:
        entries = json.loads((directory / 'catalogue.json').read_text())
    except (OSError, ValueError):
        entries = []
    for entry in entries:
        path = directory / (entry['id'] + '.png')
        if path.is_file():
            result.append(dict(id='atelier/' + entry['id'], title=entry['title'], collection='atelier',
                               image=str(path), ascii=str(path), preview=path.as_uri()))
    for key, title in [('rose', 'Goku Black · Rosé'), ('broly', 'Broly'), ('vegeta', 'Vegeta · Blue')]:
        path = ROOT / 'assets/terminal/atelier' / (key + '.png')
        if path.is_file():
            result.append(dict(id='portraits/' + key, title=title, collection='portraits',
                               image=str(path), ascii=str(path), preview=path.as_uri()))
    directory = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'modesty/terminal/dragon-ball'
    names = {'broly': 'Broly', 'goku-black-rose': 'Goku Black · Rosé', 'vegeta': 'Vegeta · Evolution',
             'goku-ultra-instinct': 'Goku · Ultra Instinct', 'goku-instinct-sign': 'Goku · Sign',
             'goku-super-saiyan': 'Goku · Super Saiyan', 'goku-super-saiyan-3': 'Goku · Super Saiyan 3',
             'goku-god': 'Goku · God', 'vegeta-majin': 'Majin Vegeta', 'vegeta-blue': 'Vegeta · Blue',
             'gogeta-blue': 'Gogeta · Blue', 'vegito-blue': 'Vegito · Blue',
             'gohan-beast': 'Gohan · Beast', 'future-trunks': 'Future Trunks', 'beerus': 'Beerus'}
    for path in sorted(directory.glob('*')):
        if not path.is_file() or path.suffix.lower() not in ('.png', '.webp', '.jpg', '.jpeg'):
            continue
        image = directory / 'cards' / path.name
        if not image.is_file():
            image = path
        result.append(dict(id='legends/' + path.stem, title=names.get(path.stem, path.stem.replace('-', ' ').title()),
                           collection='legends', image=str(image), ascii=str(path), preview=image.as_uri()))
    return result


def eligible(items, preferences):
    hidden = preferences.get('terminalArtHidden', [])
    favorites = preferences.get('terminalArtFavorites', [])
    collection = preferences.get('terminalArtCollection', 'portraits')
    rows = [item for item in items if item['id'] not in hidden
            and (collection == 'all' or item['collection'] == collection)
            and (not preferences.get('terminalArtFavoritesOnly', False) or item['id'] in favorites)]
    pinned = preferences.get('terminalArtPinned', '')
    return [item for item in rows if item['id'] == pinned] if any(item['id'] == pinned for item in rows) else rows


if __name__ == '__main__':
    print(json.dumps(catalogue()))
