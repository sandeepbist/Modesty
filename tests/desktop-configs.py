#!/usr/bin/env python3
"""Parse installed desktop configs and exercise startup/consent in private homes."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
with tempfile.TemporaryDirectory(prefix='modesty-desktop-configs-') as temporary:
    folder = Path(temporary)
    home = folder / 'home'
    home.mkdir()
    runtime = folder / 'runtime'
    runtime.mkdir(mode=0o700)
    state = folder / 'custom-state'
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'), XDG_STATE_HOME=str(state), XDG_RUNTIME_DIR=str(runtime))
    for name in ('WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE'):
        env.pop(name, None)
    with patch.object(installer, 'HOME', home), patch.object(installer, 'CONFIG', home / '.config'), patch.object(installer, 'STATE', state), contextlib.redirect_stdout(io.StringIO()):
        installer.install_files(['desktop', 'shell', 'apps', 'fonts'], False)
    # The container suite runs as root; this command parses only and never starts
    # a compositor. Actual installer CLI coverage runs as a separate normal user.
    for command in (['Hyprland', '--verify-config', *(['--i-am-really-stupid'] if os.geteuid() == 0 else []), '-c', str(home / '.config/hypr/hyprland.lua')],
                    ['foot', '--check-config', '--config='+str(home / '.config/foot/foot.ini')]):
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stdout + result.stderr
        if command[0] == 'Hyprland': assert 'config ok' in result.stdout + result.stderr
    startup = folder / 'startup.lua'
    startup.write_text('''local root = assert(arg[1])
local callbacks, commands = {}, {}
package.preload['variables'] = function() return {cursorTheme='Adwaita',cursorSize=24} end
package.preload['utils.functions'] = function() return {} end
hl = {on=function(event,callback) callbacks[event]=callback end,exec_cmd=function(command) commands[#commands+1]=command end}
io.open = function() return nil end
assert(loadfile(root .. '/setup/config/hypr/hyprland/execs.lua'))()
callbacks['hyprland.start']()
local shell, clipboard = false, false
for _,command in ipairs(commands) do
  assert(not command:find('trash%-empty') and not command:find('rm %-'),command)
  if command:find('session%-control.py start') then shell=true end
  if command:find('cliphist store') then clipboard=true end
end
assert(shell and clipboard,'Startup lost shell or clipboard')
''')
    subprocess.run(['lua', str(startup), str(ROOT)], env=env, check=True, timeout=5)
    for value in (str(state), str(folder / "state with # and spaces"), '', None):
        selected = Path(value) if value else home / '.local/state'
        sequences = selected / 'modesty/sequences.txt'
        sequences.parent.mkdir(parents=True, exist_ok=True)
        sequences.write_text('MODESTY_COLOR_FIXTURE\n')
        fish_env = dict(env)
        if value is None: fish_env.pop('XDG_STATE_HOME', None)
        else: fish_env['XDG_STATE_HOME'] = value
        result = subprocess.run(['fish', '--no-config', '-c', 'source "$HOME/.config/fish/config.fish"'], env=fish_env, capture_output=True, text=True, timeout=5)
        assert result.returncode == 0 and 'MODESTY_COLOR_FIXTURE' in result.stdout, result.stdout + result.stderr
    # Missing Python must not turn an empty answer into a full system update.
    binaries = folder / 'bin'
    binaries.mkdir()
    marker = folder / 'sudo-request'
    (binaries / 'sudo').write_text('#!/bin/bash\nprintf "%s\\n" "$*" > "$MODESTY_BOOTSTRAP_MARKER"\n')
    (binaries / 'sudo').chmod(0o755)
    for name in ('realpath', 'dirname'):
        (binaries / name).symlink_to(shutil.which(name))
    bootstrap_env = dict(env, PATH=str(binaries), MODESTY_BOOTSTRAP_MARKER=str(marker))
    for answers, flags in (('n\n', []), ('\n', []), ('', []), ('', ['--dry-run']), ('', ['--non-interactive'])):
        result = subprocess.run(['/bin/bash', str(ROOT / 'install.sh'), *flags], env=bootstrap_env, input=answers, capture_output=True, text=True, timeout=5)
        assert result.returncode != 0 and not marker.exists(), result.stdout + result.stderr
    subprocess.run(['/bin/bash', str(ROOT / 'install.sh')], env=bootstrap_env, input='yes\n', capture_output=True, text=True, timeout=5)
    assert marker.read_text().strip() == 'pacman -Syu --needed python'
print('PASS native Hyprland/foot config parsing, safe startup, fish XDG colors and explicit bootstrap consent')
