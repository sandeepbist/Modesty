import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MESA = '/usr/share/glvnd/egl_vendor.d/50_mesa.json'
GPU_OVERRIDES = (
    'LD_PRELOAD', 'LD_AUDIT',
    '__EGL_VENDOR_LIBRARY_FILENAMES', '__EGL_VENDOR_LIBRARY_DIRS',
    '__NV_PRIME_RENDER_OFFLOAD', '__NV_PRIME_RENDER_OFFLOAD_PROVIDER',
    '__GLX_VENDOR_LIBRARY_NAME', '__VK_LAYER_NV_optimus', 'DRI_PRIME',
    'GBM_BACKEND', 'MESA_LOADER_DRIVER_OVERRIDE',
    'LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER', 'VK_ICD_FILENAMES', 'VK_DRIVER_FILES',
    'QT_OPENGL', 'QSG_RHI_BACKEND', 'QT_QUICK_BACKEND',
    'QT_WAYLAND_RECONNECT', 'QT_WAYLAND_CLIENT_BUFFER_INTEGRATION',
    'QT_WAYLAND_SERVER_BUFFER_INTEGRATION', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH',
)
WAYLAND_PLATFORMS = {
    'EGL_PLATFORM': ('wayland',),
    'QT_QPA_PLATFORM': ('wayland', 'wayland-egl', 'wayland;xcb', 'wayland-egl;xcb'),
}


def selection_file(environment):
    state = environment.get('XDG_STATE_HOME') or str(Path.home()/'.local/state')
    return Path(state)/'modesty'/'mesa-egl.json'


def device_probe():
    wayland = C.CDLL('libwayland-client.so.0')
    egl = C.CDLL('libEGL.so.1')
    wayland.wl_display_connect.argtypes = [C.c_char_p]
    wayland.wl_display_connect.restype = C.c_void_p
    wayland.wl_display_disconnect.argtypes = [C.c_void_p]
    egl.eglGetPlatformDisplay.argtypes = [C.c_uint, C.c_void_p, C.c_void_p]
    egl.eglGetPlatformDisplay.restype = C.c_void_p
    egl.eglInitialize.argtypes = [C.c_void_p, C.POINTER(C.c_int), C.POINTER(C.c_int)]
    egl.eglInitialize.restype = C.c_uint
    egl.eglTerminate.argtypes = [C.c_void_p]
    egl.eglQueryString.argtypes = [C.c_void_p, C.c_int]
    egl.eglQueryString.restype = C.c_char_p
    egl.eglGetProcAddress.argtypes = [C.c_char_p]
    egl.eglGetProcAddress.restype = C.c_void_p
    display = wayland.wl_display_connect(None)
    if not display:
        raise RuntimeError('Wayland display unavailable')
    native = None
    try:
        native = egl.eglGetPlatformDisplay(0x31D8, display, None)
        major, minor = C.c_int(), C.c_int()
        if not native or not egl.eglInitialize(native, C.byref(major), C.byref(minor)):
            raise RuntimeError('EGL initialization unavailable')
        query_display = egl.eglGetProcAddress(b'eglQueryDisplayAttribEXT')
        query_device = egl.eglGetProcAddress(b'eglQueryDeviceStringEXT')
        if not query_display or not query_device:
            raise RuntimeError('EGL device identification unavailable')
        device = C.c_ssize_t()
        query_display = C.CFUNCTYPE(C.c_uint, C.c_void_p, C.c_int, C.POINTER(C.c_ssize_t))(query_display)
        if not query_display(native, 0x322C, C.byref(device)):
            raise RuntimeError('EGL device unavailable')
        query_device = C.CFUNCTYPE(C.c_char_p, C.c_void_p, C.c_int)(query_device)
        node = query_device(device.value, 0x3377)
        if not node:
            raise RuntimeError('Hardware render node unavailable')
        node = node.decode()
        hardware = Path('/sys/class/drm')/Path(node).name/'device'
        return {'egl_vendor': egl.eglQueryString(native, 0x3053).decode(),
                'egl_version': egl.eglQueryString(native, 0x3054).decode(),
                'extensions': egl.eglQueryString(native, 0x3055).decode(),
                'render_node': node, 'device_path': str(hardware.resolve()),
                'gpu_vendor': (hardware/'vendor').read_text().strip(),
                'gpu_device': (hardware/'device').read_text().strip()}
    finally:
        if native:
            egl.eglTerminate(native)
        wayland.wl_display_disconnect(display)


def compatible_device(environment):
    if not environment.get('WAYLAND_DISPLAY') or any(key in environment for key in GPU_OVERRIDES):
        return None
    if any(key in environment and environment[key] not in values for key, values in WAYLAND_PLATFORMS.items()):
        return None
    if 'LD_LIBRARY_PATH' in environment and any(
        part not in ('/usr/lib', '/usr/lib64', '/lib', '/lib64')
        for part in environment['LD_LIBRARY_PATH'].split(':')
    ):
        return None
    try:
        pragmas = re.findall(r'^\s*//@\s*pragma\s+(?:DefaultEnv|Env)\s+([A-Za-z_][A-Za-z_0-9]*)\s*=',
                             (ROOT/'shell.qml').read_text(), re.M)
        if any(key in (*GPU_OVERRIDES, *WAYLAND_PLATFORMS, 'LD_LIBRARY_PATH') for key in pragmas):
            return None
        vendor = json.loads(Path(MESA).read_text())
        if vendor['ICD']['library_path'] != 'libEGL_mesa.so.0':
            return None
        fingerprints = []
        for env in (environment, dict(environment, __EGL_VENDOR_LIBRARY_FILENAMES=MESA)):
            result = subprocess.run([sys.executable, __file__, '--probe'], env=env,
                                    capture_output=True, text=True, timeout=4, check=True)
            fingerprints.append(json.loads(result.stdout))
        first, second = fingerprints
        if first == second and first['egl_vendor'] == 'Mesa Project' and first['gpu_vendor'] == '0x1002':
            return first
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        pass
    return None


def bootstrap_library(environment):
    source = ROOT/'scripts/egl-bootstrap.c'
    compiler = shutil.which('cc', path=environment.get('PATH'))
    if not compiler:
        return None
    try:
        digest = hashlib.sha256(source.read_bytes()+os.uname().machine.encode()).hexdigest()
        cache = Path(environment.get('XDG_CACHE_HOME') or Path.home()/'.cache')/'modesty/egl-bootstrap'
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = cache/(digest+'.so')
        if not target.is_file():
            with tempfile.TemporaryDirectory(dir=cache) as temporary:
                built = Path(temporary)/'bootstrap.so'
                subprocess.run([compiler, '-std=c11', '-O2', '-fPIC', '-shared', '-Wall', '-Wextra',
                                '-Werror', '-Wl,-z,defs', str(source), '-ldl', '-o', str(built)],
                               env=environment, capture_output=True, timeout=15, check=True)
                built.chmod(0o400)
                built.replace(target)
        return target
    except (OSError, subprocess.SubprocessError):
        return None


def run_shell(command, environment, timeout=12):
    original = dict(environment)
    try:
        selected = json.loads(selection_file(original).read_text())
    except (OSError, ValueError):
        selected = None
    if selected and compatible_device(original) == selected:
        library = bootstrap_library(original)
        if library:
            try:
                pinned = library.open('rb')
            except OSError:
                pinned = None
        else:
            pinned = None
        if pinned:
            with pinned:
                prefix = f'/proc/self/fd/{pinned.fileno()}'
                preload = prefix + (':'+original['LD_PRELOAD'] if 'LD_PRELOAD' in original else '')
                candidate = dict(original, LD_PRELOAD=preload)
                code = 'import json,os;print(json.dumps({k:os.environ.get(k) for k in ("LD_PRELOAD","__EGL_VENDOR_LIBRARY_FILENAMES","__EGL_VENDOR_LIBRARY_DIRS")}))'
                expected = {k: original.get(k) for k in ('LD_PRELOAD', '__EGL_VENDOR_LIBRARY_FILENAMES', '__EGL_VENDOR_LIBRARY_DIRS')}
                ready = False
                try:
                    checked = subprocess.run([sys.executable, '-c', code], env=candidate,
                                             pass_fds=(pinned.fileno(),), capture_output=True,
                                             text=True, timeout=4, check=True)
                    ready = json.loads(checked.stdout) == expected
                except (OSError, ValueError, subprocess.SubprocessError):
                    pass
                if ready:
                    result = subprocess.run(command, env=candidate, pass_fds=(pinned.fileno(),), timeout=timeout)
                    if result.returncode != 78:
                        result.check_returncode()
                        return result
    return subprocess.run(command, env=original, check=True, timeout=timeout)


if __name__ == '__main__':
    from desktop_environment import clean_environment
    environment = clean_environment()
    if sys.argv[1:] == ['--probe']:
        print(json.dumps(device_probe()))
    elif sys.argv[1:] == ['--enable']:
        fingerprint = compatible_device(environment)
        if not fingerprint or not bootstrap_library(environment):
            raise SystemExit('This session cannot use the optional Mesa initialization.')
        path = selection_file(environment)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fingerprint)+'\n')
        print('Enabled for this verified EGL device. Restart the main shell to apply.')
    elif sys.argv[1:] == ['--disable']:
        selection_file(environment).unlink(missing_ok=True)
    else:
        raise SystemExit('Usage: shell_renderer.py --enable | --disable')
