#!/usr/bin/env python3
"""Generate real GTK palettes and parse the shipped Thunar CSS without a display."""
import configparser
import importlib.util
import json
from itertools import product
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import appearance


def contrast(a, b):
    def luminance(value):
        rgb = [int(value[i:i+2], 16)/255 for i in (1, 3, 5)]
        return sum((c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4)*w
                   for c, w in zip(rgb, (.2126, .7152, .0722)))
    x, y = sorted((luminance(a), luminance(b)))
    return (y+.05)/(x+.05)


real_run = subprocess.run

def isolated_run(command, **kwargs):
    if command[0] == 'matugen':
        return real_run(command, **kwargs)
    assert command[0] in ('hyprctl', 'gsettings'), command
    return subprocess.CompletedProcess(command, 0, '', '')


# Selection foreground deliberately differs from the window background.
# Both named and wallpaper paths must preserve it through Matugen.
profiles = [
    ('dark', dict(accent='#bdc7dd', accentText='#172033', bg='#101013', surface='#18181c',
                  text='#f2f2f4', subtext='#b8b8c0', green='#a6e3a1', yellow='#f9e2af', red='#f38ba8')),
    ('light', dict(accent='#365f9d', accentText='#ffffff', bg='#f5f6fa', surface='#e9edf5',
                   text='#242a38', subtext='#5a6374', green='#35683b', yellow='#7e611f', red='#aa3856')),
]


def check_gtk_opt_out():
    """Exercise the real appearance entry point with isolated desktop settings."""
    with tempfile.TemporaryDirectory(prefix='modesty-gtk-opt-out-') as temporary:
        directory = Path(temporary)
        environment = {key: value for key, value in os.environ.items() if key not in (
            'DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS', 'HYPRLAND_INSTANCE_SIGNATURE')}
        for key, name in [('HOME', 'home'), ('XDG_CONFIG_HOME', 'config'),
                          ('XDG_STATE_HOME', 'state'), ('XDG_DATA_HOME', 'data'),
                          ('XDG_CACHE_HOME', 'cache'), ('XDG_RUNTIME_DIR', 'runtime')]:
            path = directory/name
            path.mkdir(mode=0o700)
            environment[key] = str(path)
        commands = directory/'bin'
        commands.mkdir()
        (commands/'matugen').symlink_to(shutil.which('matugen'))
        (commands/'hyprctl').write_text('#!/bin/sh\nexit 0\n')
        (commands/'hyprctl').chmod(0o755)
        oracle = directory/'gsettings.json'
        oracle.write_text(json.dumps({'gtk-theme': 'UserTheme', 'color-scheme': 'default'}))
        environment['MODESTY_TEST_GSETTINGS'] = str(oracle)
        environment['MODESTY_TEST_GSETTINGS_FAIL'] = str(directory/'fail-gsettings')
        (commands/'gsettings').write_text('#!'+sys.executable+'\n'+'''import json, os, sys
from pathlib import Path
path = Path(os.environ['MODESTY_TEST_GSETTINGS'])
values = json.loads(path.read_text())
action, schema, key, *args = sys.argv[1:]
assert schema == 'org.gnome.desktop.interface'
assert key in values
if action == 'get':
    assert not args
    print(repr(values[key]))
else:
    assert action == 'set' and len(args) == 1
    failure = Path(os.environ['MODESTY_TEST_GSETTINGS_FAIL'])
    if key == 'gtk-theme' and failure.exists():
        failure.unlink()
        sys.exit('Injected GSettings write failure')
    values[key] = args[0].strip("'")
    path.write_text(json.dumps(values))
''')
        (commands/'gsettings').chmod(0o755)
        environment['PATH'] = str(commands)
        original_css = ('/* Keep modesty-generated.css references in user comments. */\n'
                        '@import "my-modesty-generated.css";\n'
                        '@define-color accent_color #7245a2;\n'
                        'button { color: @accent_color; }\n')
        original_ini = ('# User settings\n[Settings]\n'
                        'gtk-application-prefer-dark-theme=0\n'
                        'gtk-theme-name=UserTheme\ncustom-setting=keep\n')
        config = Path(environment['XDG_CONFIG_HOME'])
        for version in ('3.0', '4.0'):
            gtk = config/('gtk-'+version)
            gtk.mkdir()
            (gtk/'gtk.css').write_text(original_css)
            (gtk/'settings.ini').write_text(original_ini)

        def apply(mode, enabled, success=True):
            data = dict(paletteName='midnight', mode=mode, colors=dict(profiles)[mode], targets={'gtk': enabled})
            result = real_run([sys.executable, str(ROOT/'scripts/appearance.py'), '--stdin'],
                              input=json.dumps(data)+'\n', env=environment, text=True,
                              capture_output=True, timeout=20)
            assert (result.returncode == 0) == success, result.stdout+result.stderr
            assert json.loads(result.stdout)['ok'] == success

        apply('dark', True)
        for version in ('3.0', '4.0'):
            gtk = config/('gtk-'+version)
            css = (gtk/'gtk.css').read_text()
            assert css == '@import "modesty-generated.css";\n'+original_css, 'GTK sync destroyed user CSS'
            parser = configparser.ConfigParser()
            parser.read(gtk/'settings.ini')
            assert parser.get('Settings', 'gtk-application-prefer-dark-theme') == '1'
            if Path('/usr/share/themes/adw-gtk3-dark').exists():
                assert parser.get('Settings', 'gtk-theme-name') == 'adw-gtk3-dark'
                assert json.loads(oracle.read_text())['gtk-theme'] == 'adw-gtk3-dark'
        apply('light', False)
        for version in ('3.0', '4.0'):
            gtk = config/('gtk-'+version)
            assert (gtk/'gtk.css').read_text() == original_css
            assert (gtk/'settings.ini').read_text() == original_ini, 'GTK opt-out did not restore owned settings'
        assert json.loads(oracle.read_text()) == {'gtk-theme': 'UserTheme', 'color-scheme': 'prefer-light'}

        apply('dark', True)
        edited_ini = original_ini.replace('gtk-theme-name=UserTheme', 'gtk-theme-name=EditedTheme')+'# Keep this edit\nother-setting=keep-too\n'
        (config/'gtk-3.0/settings.ini').write_text(edited_ini)
        current = json.loads(oracle.read_text())
        current['gtk-theme'] = 'EditedTheme'
        oracle.write_text(json.dumps(current))
        apply('light', False)
        assert (config/'gtk-3.0/settings.ini').read_text() == edited_ini, 'GTK opt-out overwrote intervening edits'
        assert (config/'gtk-4.0/settings.ini').read_text() == original_ini
        assert json.loads(oracle.read_text()) == {'gtk-theme': 'EditedTheme', 'color-scheme': 'prefer-light'}
        # Old full-file backups cannot prove ownership of any current value.
        for version in ('3.0', '4.0'):
            backup = Path(environment['XDG_STATE_HOME'])/'modesty/theme-backups'/('gtk-'+version)/'settings.ini'
            backup.write_text(original_ini.replace('UserTheme', 'AmbiguousOldBackup'))
        apply('dark', False)
        assert (config/'gtk-3.0/settings.ini').read_text() == edited_ini
        assert (config/'gtk-4.0/settings.ini').read_text() == original_ini
        assert json.loads(oracle.read_text()) == {'gtk-theme': 'EditedTheme', 'color-scheme': 'prefer-dark'}
        # Repeated palette changes retain the latest user baseline, not a stale backup.
        apply('dark', True)
        if all((Path('/usr/share/themes')/theme).exists() for theme in ('adw-gtk3', 'adw-gtk3-dark')):
            Path(environment['MODESTY_TEST_GSETTINGS_FAIL']).touch()
            apply('light', True, success=False)
            assert json.loads(oracle.read_text())['gtk-theme'] == 'adw-gtk3-dark'
        apply('light', True)
        apply('dark', False)
        assert (config/'gtk-3.0/settings.ini').read_text() == edited_ini
        assert (config/'gtk-4.0/settings.ini').read_text() == original_ini
        assert json.loads(oracle.read_text()) == {'gtk-theme': 'EditedTheme', 'color-scheme': 'prefer-dark'}
        # Keys initially absent must be removed without deleting unrelated content.
        absent_ini = '[Other]\nkeep=value\n[Settings]\n# Keep this comment\ncustom-setting=keep\n'
        for version in ('3.0', '4.0'):
            (config/('gtk-'+version)/'settings.ini').write_text(absent_ini)
        apply('dark', True)
        apply('light', False)
        for version in ('3.0', '4.0'):
            assert (config/('gtk-'+version)/'settings.ini').read_text() == absent_ini
        assert not list((Path(environment['XDG_STATE_HOME'])/'modesty/gtk-settings').glob('*.json'))

        spec = importlib.util.spec_from_file_location('app_theme', ROOT/'scripts/app-theme.py')
        app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app)
        app.CONFIG = config
        settings = config/'gtk-3.0/settings.ini'
        settings.write_text(original_ini)
        state = Path(environment['XDG_STATE_HOME'])/'modesty'
        receipt = state/'gtk-settings/gtk-3.0.json'
        original_write = app.write
        for destination, failed_attempt in ((receipt, 1), (settings, 1), (receipt, 2)):
            app.gtk_settings(settings, state, 'dark', True)
            before = settings.read_text()
            attempts = 0
            def fail_write(path, text):
                nonlocal attempts
                if path == destination:
                    attempts += 1
                    if attempts == failed_attempt:
                        raise OSError('Injected GTK write failure')
                original_write(path, text)
            with patch.object(app, 'write', side_effect=fail_write):
                try:
                    app.gtk_settings(settings, state, 'light', True)
                except OSError:
                    pass
                else:
                    raise AssertionError('Expected injected GTK write failure')
            if failed_attempt == 1:
                assert settings.read_text() == before, 'GTK settings changed despite failed publication'
            app.gtk_settings(settings, state, 'light', True)
            app.gtk_settings(settings, state, 'dark', False)
            assert settings.read_text() == original_ini


check_gtk_opt_out()
for mode, colors in profiles:
    for source, revision in product(('midnight', 'wallpaper'), ('legacy', 'solid', 'inset', 'pass1')):
        fixture = ROOT/'tests/fixtures'/f'thunar-{revision}.css'
        with tempfile.TemporaryDirectory(prefix='modesty-gtk-check-') as temporary:
            directory = Path(temporary)
            config = directory/'config'
            for version in ('3.0', '4.0'):
                gtk = config/('gtk-'+version)
                gtk.mkdir(parents=True)
                (gtk/'gtk.css').write_text((ROOT/'setup/config/gtk-3.0/gtk.css').read_text())
                # Exercise migration on an existing install, not only fresh CSS.
                (gtk/'thunar.css').write_text(fixture.read_text())
            data = dict(paletteName=source, mode=mode, colors=colors, targets={'gtk': True})
            if source == 'wallpaper':
                roles = {'primary':'accent', 'on_primary':'accentText', 'surface':'bg',
                         'surface_container_lowest':'bg', 'surface_container_low':'surface',
                         'surface_container':'surface', 'surface_container_high':'surface',
                         'surface_container_highest':'surface', 'on_surface':'text',
                         'on_surface_variant':'subtext', 'outline':'subtext', 'outline_variant':'subtext',
                         'shadow':'bg', 'secondary':'yellow', 'tertiary':'green', 'error':'red'}
                data['wallpaperData'] = {'colors':{role:{mode:{'color':colors[key]}} for role, key in roles.items()}}
                data['wallpaperData']['colors']['surface_container_lowest'][mode]['color'] = '#09090c' if mode == 'dark' else '#ffffff'
            with patch.dict(os.environ, XDG_CONFIG_HOME=str(config)), patch.object(appearance.subprocess, 'run', side_effect=isolated_run):
                appearance.apply(data, directory/'state')
            generated = json.loads((directory/'state/matugen/input.json').read_text())
            assert generated['colors']['on_primary']['default']['color'] == colors['accentText']
            assert contrast(colors['accent'], colors['accentText']) >= 4.5
            assert contrast(colors['bg'], colors['text']) >= 4.5
            selected = '#'+''.join(f'{round(int(colors["accent"][i:i+2],16)*.18+int(colors["bg"][i:i+2],16)*.82):02x}' for i in (1,3,5))
            assert contrast(selected, colors['text']) >= 4.5
            for version in ('3.0', '4.0'):
                gtk = config/('gtk-'+version)
                assert (gtk/'thunar.css').read_text() == (ROOT/'setup/config/gtk-3.0/thunar.css').read_text()
                assert (directory/'state/theme-backups'/('gtk-'+version)/'thunar.css').read_text() == fixture.read_text()
                errors = []
                provider = Gtk.CssProvider()
                provider.connect('parsing-error', lambda provider, section, error: errors.append(str(error)))
                provider.load_from_path(str(gtk/'gtk.css'))
                assert not errors, (mode, source, revision, errors)
                assert (gtk/'gtk.css').read_text().count('modesty-generated.css') == 1
            if '--live' in sys.argv:
                # Query actual GTK style resolution, not a CSS substring. No
                # window is shown and no desktop settings or state are changed.
                from gi.repository import Gdk
                def hex_color(rgba):
                    return '#'+''.join(f'{round(channel*255):02x}' for channel in (rgba.red,rgba.green,rgba.blue))
                Gtk.init([])
                settings = Gtk.Settings.get_default()
                settings.props.gtk_enable_animations = False
                settings.props.gtk_theme_name = 'adw-gtk3-dark' if mode == 'dark' else 'adw-gtk3'
                Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER+1)
                window = Gtk.Window(); window.get_style_context().add_class('thunar')
                rubberband = Gtk.DrawingArea(); rubberband.get_style_context().add_class('rubberband'); window.add(rubberband)
                border = rubberband.get_style_context().get_border_color(Gtk.StateFlags.NORMAL)
                assert border.alpha == 1, 'Drag-selection border became translucent'
                window.remove(rubberband)
                frame = Gtk.ScrolledWindow(); frame.get_style_context().add_class('standard-view'); frame.get_style_context().add_class('frame'); window.add(frame)
                background = frame.get_style_context().get_background_color(Gtk.StateFlags.NORMAL)
                assert background.alpha == 1 and hex_color(background) == colors['bg'], (mode, source, background.to_string())
                for kind in (Gtk.IconView, Gtk.TreeView):
                    view = kind(); view.get_style_context().add_class('view'); frame.add(view)
                    # ExoIconView adds the cell class while painting each item.
                    if kind is Gtk.IconView:view.get_style_context().add_class('cell')
                    context = view.get_style_context()
                    # Thunar's highlighting renderer looks up these roles directly,
                    # bypassing the widget's resolved background property.
                    for role in ('theme_selected_bg_color','theme_unfocused_selected_bg_color'):
                        found, color = context.lookup_color(role)
                        assert found and abs(color.alpha-.18)<.001, (mode,kind,role,color.to_string())
                    found, color = context.lookup_color('theme_selected_fg_color')
                    assert found and color.alpha == 1
                    for state in (Gtk.StateFlags.SELECTED, Gtk.StateFlags.SELECTED|Gtk.StateFlags.FOCUSED, Gtk.StateFlags.SELECTED|Gtk.StateFlags.BACKDROP):
                        context.set_state(state)
                        text = context.get_color(state)
                        background = context.get_background_color(state)
                        assert hex_color(text) == colors['text'], (mode, kind, state, text.to_string())
                        assert hex_color(background) == colors['accent'] and abs(background.alpha-.18)<.001, (mode, kind, state, background.to_string())
                        rgb = [int(colors['bg'][i:i+2],16) for i in (1,3,5)]
                        blended = '#'+''.join(f'{round(c*255*background.alpha+b*(1-background.alpha)):02x}' for c,b in zip((background.red,background.green,background.blue),rgb))
                        assert text.alpha == 1 and contrast(hex_color(text), blended) >= 4.5
                    frame.remove(view)
                window.remove(frame)
                sidebar = Gtk.Box(); sidebar.get_style_context().add_class('sidebar'); window.add(sidebar)
                tree = Gtk.TreeView(); tree.get_style_context().add_class('view'); sidebar.add(tree)
                context = tree.get_style_context(); context.set_state(Gtk.StateFlags.SELECTED)
                text = context.get_color(Gtk.StateFlags.SELECTED)
                assert text.alpha == 1 and hex_color(text) == colors['accent']
                background = context.get_background_color(Gtk.StateFlags.SELECTED)
                base = sidebar.get_style_context().get_background_color(Gtk.StateFlags.NORMAL)
                assert base.alpha == 1 and hex_color(base) == generated['colors']['surface_container_lowest']['default']['color']
                blended = '#'+''.join(f'{round((c*background.alpha+b*(1-background.alpha))*255):02x}' for c,b in zip((background.red,background.green,background.blue),(base.red,base.green,base.blue)))
                assert contrast(hex_color(text), blended) >= 4.5, (mode, source, hex_color(text), blended)
                window.destroy()
                Gtk.StyleContext.remove_provider_for_screen(Gdk.Screen.get_default(), provider)
            # A user-modified stylesheet must survive subsequent palette changes.
            custom = config/'gtk-3.0/thunar.css'
            custom.write_text('/* User customization */\n'+custom.read_text())
            preserved = custom.read_text()
            with patch.dict(os.environ, XDG_CONFIG_HOME=str(config)), patch.object(appearance.subprocess, 'run', side_effect=isolated_run):
                appearance.apply(data, directory/'state')
            assert custom.read_text() == preserved
            # Matching bundled bytes behind a user symlink are still custom.
            custom.unlink()
            linked = directory/'linked-thunar.css'
            linked.write_text(fixture.read_text())
            custom.symlink_to(linked)
            original = linked.read_bytes()
            with patch.dict(os.environ, XDG_CONFIG_HOME=str(config)), patch.object(appearance.subprocess, 'run', side_effect=isolated_run):
                appearance.apply(data, directory/'state')
            assert custom.is_symlink() and linked.read_bytes() == original
print('PASS GTK opt-out ownership, user CSS/INI edits, GTK palette generation, named/wallpaper selection foreground, dark/light contrast, legacy/solid/inset/pass1 migrations and Thunar CSS parsing'+('; native icon/list selection states and sidebar contrast' if '--live' in sys.argv else ''))
