#!/usr/bin/env python3
"""Small, optional Spicetify palette target; never restarts Spotify."""
import configparser
import os
import re
from pathlib import Path

CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
ROLES = {
    'text': 'on_surface', 'subtext': 'on_surface_variant',
    'main': 'surface', 'main-elevated': 'surface_container',
    'sidebar': 'surface_container_lowest', 'player': 'surface_container_low',
    'card': 'surface_container', 'shadow': 'shadow',
    'selected-row': 'on_surface', 'button': 'primary', 'button-active': 'primary',
    'button-disabled': 'outline', 'tab-active': 'surface_container_high',
    'notification': 'surface_container_high', 'notification-error': 'error',
    'misc': 'primary', 'highlight': 'surface_container_high',
    'highlight-elevated': 'surface_container_highest',
}


def write_changed(path, text):
    if path.exists() and path.read_text() == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.modesty-tmp')
    temp.write_text(text)
    temp.replace(path)


def apply(raw, mode):
    config = configparser.ConfigParser(interpolation=None)
    config.read(CONFIG / 'spicetify/config-xpui.ini')
    if config.get('Setting', 'current_theme', fallback='') != 'Modesty':
        return  # Do not take over a different user-selected theme.
    theme = CONFIG / 'spicetify/Themes/Modesty'
    if not (theme / 'user.css').exists():
        return

    def color(role, fallback='on_surface'):
        values = raw['colors'].get(role, raw['colors'][fallback])
        value = values.get(mode, values.get('default', {})).get('color', '')
        if not re.fullmatch(r'#[a-fA-F0-9]{6}', value):
            raise ValueError('Invalid Spotify theme color: ' + role)
        return value.lower()

    colors = {key: color(role) for key, role in ROLES.items()}
    write_changed(theme / 'color.ini', '[Modesty]\n' + ''.join(
        key + ' = ' + value[1:] + '\n' for key, value in colors.items()))
    css = '/* Modesty palette */\n:root {\n  color-scheme: ' + mode + ';\n'
    for key, value in colors.items():
        css += '  --spice-' + key + ': ' + value + ';\n'
        rgb = ','.join(str(int(value[i:i+2], 16)) for i in (1, 3, 5))
        css += '  --spice-rgb-' + key + ': ' + rgb + ';\n'
    css += '  --modesty-on-accent: ' + color('on_primary') + ';\n'
    css += '  --modesty-line: color-mix(in srgb, ' + color('outline_variant', 'outline') + ' 38%, transparent);\n'
    css += '  --modesty-hover: color-mix(in srgb, ' + color('on_surface') + ' 7%, transparent);\n'
    css += '  --modesty-selection: color-mix(in srgb, ' + color('primary') + ' 13%, ' + color('surface') + ');\n}\n'
    # Encore tokens are locally redefined by Spotify's semantic color sets.
    css += '.encore-dark-theme, .encore-light-theme, .encore-base-set {\n'
    tokens = {'background-base': 'main', 'background-highlight': 'highlight',
              'background-press': 'highlight-elevated', 'background-elevated-base': 'card',
              'background-elevated-highlight': 'highlight-elevated', 'background-elevated-press': 'highlight',
              'background-tinted-base': 'card', 'background-tinted-highlight': 'highlight',
              'background-tinted-press': 'highlight-elevated', 'text-base': 'text', 'text-subdued': 'subtext',
              'text-bright-accent': 'button', 'essential-base': 'text', 'essential-subdued': 'subtext',
              'essential-bright-accent': 'button', 'decorative-base': 'text', 'decorative-subdued': 'button-disabled'}
    for key, value in tokens.items():
        css += '  --' + key + ': var(--spice-' + value + ') !important;\n'
    css += '}\n.encore-bright-accent-set { --background-base: var(--spice-button); --background-highlight: var(--spice-button-active); --text-base: var(--modesty-on-accent); --essential-base: var(--modesty-on-accent); }\n'
    write_changed(theme / 'assets/modesty-colors.css', css)
    # Local xpui resources update in place. The theme's tiny visible-only reader
    # changes CSS variables, so switching palettes does not interrupt music.
    xpui = Path(config.get('Setting', 'spotify_path', fallback='/opt/spotify')) / 'Apps/xpui'
    if (xpui / 'modesty-colors.css').exists():
        write_changed(xpui / 'modesty-colors.css', css)


if __name__ == '__main__':
    import json
    import sys
    raw = json.loads(Path(sys.argv[1]).read_text())
    apply(raw, sys.argv[2] if len(sys.argv) > 2 else raw.get('mode', 'dark'))
