#!/usr/bin/env python3
"""Generate real GTK palettes and parse the shipped Thunar CSS without a display."""
import json
import os
from pathlib import Path
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
for mode, colors in profiles:
    for source in ('midnight', 'wallpaper'):
        with tempfile.TemporaryDirectory(prefix='modesty-gtk-check-') as temporary:
            directory = Path(temporary)
            config = directory/'config'
            for version in ('3.0', '4.0'):
                gtk = config/('gtk-'+version)
                gtk.mkdir(parents=True)
                (gtk/'gtk.css').write_text('@import "thunar.css";\n')
                # Exercise migration on an existing install, not only fresh CSS.
                (gtk/'thunar.css').write_text((ROOT/'tests/fixtures/thunar-legacy.css').read_text())
            data = dict(paletteName=source, mode=mode, colors=colors, targets={'gtk': True})
            if source == 'wallpaper':
                roles = {'primary':'accent', 'on_primary':'accentText', 'surface':'bg',
                         'surface_container_lowest':'bg', 'surface_container_low':'surface',
                         'surface_container':'surface', 'surface_container_high':'surface',
                         'surface_container_highest':'surface', 'on_surface':'text',
                         'on_surface_variant':'subtext', 'outline':'subtext', 'outline_variant':'subtext',
                         'shadow':'bg', 'secondary':'yellow', 'tertiary':'green', 'error':'red'}
                data['wallpaperData'] = {'colors':{role:{mode:{'color':colors[key]}} for role, key in roles.items()}}
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
                assert (directory/'state/theme-backups'/('gtk-'+version)/'thunar.css').read_text() == (ROOT/'tests/fixtures/thunar-legacy.css').read_text()
                errors = []
                provider = Gtk.CssProvider()
                provider.connect('parsing-error', lambda provider, section, error: errors.append(str(error)))
                provider.load_from_path(str(gtk/'gtk.css'))
                assert not errors, (mode, source, errors)
                assert (gtk/'gtk.css').read_text().count('modesty-generated.css') == 1
            if '--live' in sys.argv:
                # Query actual GTK style resolution, not a CSS substring. No
                # window is shown and no desktop settings or state are changed.
                from gi.repository import Gdk
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
                frame = Gtk.ScrolledWindow(); frame.get_style_context().add_class('standard-view'); window.add(frame)
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
                        def hex_color(rgba):
                            return '#'+''.join(f'{round(channel*255):02x}' for channel in (rgba.red,rgba.green,rgba.blue))
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
                assert hex_color(context.get_color(Gtk.StateFlags.SELECTED)) == colors['text']
                background = context.get_background_color(Gtk.StateFlags.SELECTED)
                for base in (colors['bg'], colors['surface']):
                    rgb = [int(base[i:i+2],16) for i in (1,3,5)]
                    blended = '#'+''.join(f'{round(c*255*background.alpha+b*(1-background.alpha)):02x}' for c,b in zip((background.red,background.green,background.blue),rgb))
                    assert contrast(colors['text'], blended) >= 4.5
                window.destroy()
                Gtk.StyleContext.remove_provider_for_screen(Gdk.Screen.get_default(), provider)
            # A user-modified stylesheet must survive subsequent palette changes.
            custom = config/'gtk-3.0/thunar.css'
            custom.write_text('/* User customization */\n'+custom.read_text())
            preserved = custom.read_text()
            with patch.dict(os.environ, XDG_CONFIG_HOME=str(config)), patch.object(appearance.subprocess, 'run', side_effect=isolated_run):
                appearance.apply(data, directory/'state')
            assert custom.read_text() == preserved
print('PASS GTK palette generation, named/wallpaper selection foreground, dark/light contrast and Thunar CSS parsing'+('; native icon/list selection states' if '--live' in sys.argv else ''))
