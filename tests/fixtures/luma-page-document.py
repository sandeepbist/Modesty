import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Atk', '1.0')
from gi.repository import Atk, Gtk

window = Gtk.Window(title='Luma native document probe')
window.set_default_size(640, 500)
scroll = Gtk.ScrolledWindow()
editor = Gtk.TextView()
editor.set_editable(False)
editor.get_buffer().set_text('LUMA NATIVE DOCUMENT START\n' + 'Exposed paragraph\n'*100 + 'LUMA NATIVE BELOW-FOLD 9427')
editor.get_accessible().set_role(Atk.Role.DOCUMENT_TEXT)
scroll.add(editor)
window.add(scroll)
window.connect('destroy', Gtk.main_quit)
window.show_all()
Gtk.main()
