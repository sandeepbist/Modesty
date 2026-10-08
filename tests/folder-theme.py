#!/usr/bin/env python3
"""Check real folder overlays, GTK lookup/rendering, refresh and restoration."""
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import folder_theme as folders


def raw(accent, foreground, background='#101013'):
    return {'colors':{'primary':{'default':{'color':accent}},
                      'on_primary':{'default':{'color':foreground}},
                      'surface':{'default':{'color':background}}}}


with tempfile.TemporaryDirectory(prefix='modesty-folder-check-') as temporary:
    directory = Path(temporary)
    state = directory/'state'
    data = directory/'data'
    current = ['Adwaita']
    calls = []
    def setting(value=None):
        if value is not None:
            current[0] = value
            calls.append(value)
        return current[0]
    with patch.dict(os.environ, XDG_DATA_HOME=str(data)), patch.object(folders, 'setting', side_effect=setting):
        folders.apply(raw('#bdc7dd','#172033'), state, False)
        assert not calls and not data.exists(), 'Default off changed icon state'
        available = [base for base in folders.SUPPORTED if (folders.SYSTEM_ICONS/base).exists()]
        assert 'Adwaita' in available, 'Installer-required Adwaita theme missing'
        for base in available:
            current[0] = base
            folders.apply(raw('#bdc7dd','#172033'), state, True)
            assert current[0] == folders.THEMES[0]
            first = data/'icons'/current[0]
            assert json.loads((state/'folder-theme.json').read_text())['original'] == base
            theme = Gtk.IconTheme.new()
            theme.set_search_path([str(data/'icons'), str(folders.SYSTEM_ICONS)])
            theme.set_custom_theme(current[0])
            for name in ('folder','folder-documents','folder-download','user-home'):
                icon = theme.lookup_icon(name, 48, Gtk.IconLookupFlags.FORCE_SVG)
                assert icon and Path(icon.get_filename()).is_relative_to(first), (base, name)
                svg = Path(icon.get_filename()).read_text()
                body,emblem=folders.tones('#bdc7dd','#172033','#101013')
                assert body in svg and folders.contrast(body,'#101013')>=3
                assert folders.contrast(body,emblem)>=4.5
                assert '#5294e2' not in svg and '#62a0ea' not in svg
                image = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon.get_filename(), 48, 48, True)
                assert image.get_width() == 48 and image.get_height() == 48
            other = theme.lookup_icon('text-x-generic',48,Gtk.IconLookupFlags.FORCE_SVG)
            assert other and not Path(other.get_filename()).is_relative_to(first), 'Non-folder icons stopped inheriting'
            folders.apply(raw('#bdc7dd','#172033'), state, True)
            assert current[0] == folders.THEMES[0], 'Unchanged palette refreshed icons'
            folders.apply(raw('#365f9d','#ffffff'), state, True)
            assert current[0] == folders.THEMES[1], 'New palette did not invalidate GTK cache'
            assert folders.tones('#365f9d','#ffffff','#101013')[0] in (data/'icons'/current[0]/'48x48/places/folder.svg').read_text()
            folders.restore(state)
            assert current[0] == base and not (state/'folder-theme.json').exists()
            assert not any((data/'icons'/name).exists() for name in folders.THEMES)
        current[0] = 'PersonalIconTheme'
        try:folders.apply(raw('#bdc7dd','#172033'),state,True)
        except RuntimeError as error:assert 'preserved' in str(error)
        else:raise AssertionError('Unsupported icon theme was taken over')
        assert current[0] == 'PersonalIconTheme'
        current[0] = 'Adwaita'
        folders.apply(raw('#bdc7dd','#172033'),state,True)
        generated = data/'icons'/current[0]/'48x48/places/folder.svg'
        original = generated.read_bytes()
        generated.unlink()
        target = directory/'custom.svg'
        target.write_bytes(original)
        generated.symlink_to(target)
        try:folders.apply(raw('#bdc7dd','#172033'),state,True)
        except RuntimeError as error:assert 'symlinks were preserved' in str(error)
        else:raise AssertionError('Custom generated-file symlink accepted')
        assert generated.is_symlink() and target.read_bytes() == original
        generated.unlink();generated.write_bytes(original)
        # Disabling must preserve a user's newer manual theme choice and edits.
        edited = data/'icons'/current[0]/'48x48/places/folder.svg'
        edited.write_text('user edit')
        current[0] = 'PersonalIconTheme'
        folders.restore(state)
        assert current[0] == 'PersonalIconTheme' and edited.read_text() == 'user edit'
        try:folders.recolor('<svg/>','Papirus','#ff0000;bad','#ffffff')
        except ValueError:pass
        else:raise AssertionError('Invalid color accepted')
print('PASS palette folder SVGs, native GTK lookup/rendering, inherited icons, bounded refresh, defaults, restoration and custom-theme/edit preservation')
