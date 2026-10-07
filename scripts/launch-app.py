#!/usr/bin/env python3
"""Launch an installed desktop entry with its desktop semantics and report errors."""
import json, os, re, shutil, subprocess, sys, time
from desktop_environment import clean_environment

def launch(identifier, terminal='foot'):
    import gi
    gi.require_version('Gio', '2.0')
    gi.require_version('GioUnix', '2.0')
    from gi.repository import Gio, GioUnix
    if os.environ.get('MODESTY_PREVIEW') == '1': raise ValueError('Launching is disabled in preview')
    env = clean_environment()
    os.environ.clear(); os.environ.update(env)
    entry = GioUnix.DesktopAppInfo.new(identifier if identifier.endswith('.desktop') else identifier+'.desktop')
    if entry is None: raise ValueError('This application is no longer installed')
    if entry.get_boolean('Terminal'):
        # GLib handles Exec quoting and field codes, including Terminal=true.
        # xdg-terminal-exec is used when installed; otherwise use a generated
        # desktop entry with an explicit terminal prefix, preserving Exec syntax.
        if terminal not in ('foot', 'kitty', 'alacritty', 'wezterm'): raise ValueError('Unsupported terminal')
        if not shutil.which(terminal): raise ValueError(terminal+' is not installed. Choose another terminal in Settings.')
        from gi.repository import GLib
        keyfile = GLib.KeyFile()
        keyfile.load_from_file(entry.get_filename(), GLib.KeyFileFlags.NONE)
        prefix = {'foot':'foot -e ', 'kitty':'kitty ', 'alacritty':'alacritty -e ', 'wezterm':'wezterm start -- '}[terminal]
        keyfile.set_string('Desktop Entry','Exec',prefix+entry.get_string('Exec'))
        keyfile.set_boolean('Desktop Entry','Terminal',False)
        keyfile.set_boolean('Desktop Entry','DBusActivatable',False)
        entry = GioUnix.DesktopAppInfo.new_from_keyfile(keyfile)
    context = Gio.AppLaunchContext()
    if not entry.launch([], context): raise RuntimeError('The application could not be started')
    return {'ok': True, 'id': identifier}

def close_app(identifier):
    """Resolve installed identity and ask its native windows to close gracefully."""
    import gi
    gi.require_version('GioUnix', '2.0')
    from gi.repository import GioUnix
    if os.environ.get('MODESTY_PREVIEW') == '1': raise ValueError('Closing is disabled in preview')
    entry=GioUnix.DesktopAppInfo.new(identifier if identifier.endswith('.desktop') else identifier+'.desktop')
    if entry is None: raise ValueError('This application is no longer installed')
    def normalized(value): return re.sub(r'[^a-z0-9]','',value.casefold())
    identities={normalized(identifier.removesuffix('.desktop')),normalized(entry.get_startup_wm_class() or '')}
    identities.discard('')
    def windows(): return json.loads(subprocess.check_output(['hyprctl','-j','clients'],timeout=3))
    selected=[client for client in windows() if normalized(client.get('class','')) in identities or normalized(client.get('initialClass','')) in identities]
    if not selected:
        return {'ok':False,'status':'no_matching_window','id':identifier,'windows':0,
            'error':'No window matches this installed identity. It may already be closed or lack a matching StartupWMClass.'}
    addresses=[]
    for client in selected:
        address=client.get('address','')
        if not re.fullmatch(r'0x[a-fA-F0-9]+',address): raise ValueError('Invalid native window address')
        addresses.append(address)
    for address in addresses:
        expression='hl.dispatch(hl.dsp.window.close({window="address:'+address+'"}))'
        result=subprocess.run(['hyprctl','eval',expression],capture_output=True,text=True,timeout=3)
        if result.returncode or 'error' in result.stdout.casefold(): raise RuntimeError('Compositor could not request window closing')
    remaining=len(addresses)
    for _ in range(6):
        remaining=sum(client.get('address') in addresses for client in windows())
        if not remaining: break
        time.sleep(.15)
    return {'ok':True,'id':identifier,'status':'close_requested' if remaining else 'closed','windowsRemaining':remaining,
        'note':'An application may be waiting for an unsaved-work dialog.' if remaining else ''}

if __name__ == '__main__':
    try: print(json.dumps(close_app(sys.argv[2]) if sys.argv[1]=='--close' else launch(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else 'foot')),flush=True)
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error)}),flush=True);sys.exit(1)
