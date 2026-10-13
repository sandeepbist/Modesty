#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if not shutil.which(shlex.split(os.environ.get('CC', 'cc'))[0]):
    print('SKIP optional native EGL checks: C compiler unavailable')
    raise SystemExit(0)
SELECTOR = "__EGL_VENDOR_LIBRARY_FILENAMES"
MESA = "/usr/share/glvnd/egl_vendor.d/50_mesa.json"
OVERRIDES = (
    SELECTOR, "__EGL_VENDOR_LIBRARY_DIRS", "__NV_PRIME_RENDER_OFFLOAD",
    "__NV_PRIME_RENDER_OFFLOAD_PROVIDER", "__GLX_VENDOR_LIBRARY_NAME",
    "__VK_LAYER_NV_optimus", "DRI_PRIME", "EGL_PLATFORM", "QT_QPA_PLATFORM",
    "QT_OPENGL", "QSG_RHI_BACKEND", "QT_QUICK_BACKEND",
    "QT_WAYLAND_RECONNECT", "QT_WAYLAND_CLIENT_BUFFER_INTEGRATION",
    "QT_WAYLAND_SERVER_BUFFER_INTEGRATION", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH",
)
FAKE = r'''
#include <stdlib.h>
#include <string.h>
static int calls, arguments_ok;
static char *selected, *load_preload;
static void __attribute__((constructor)) loaded(void) {
    const char *value = getenv("LD_PRELOAD");
    if (value) load_preload = strdup(value);
}
int bootstrapCalls(void) { return calls; }
int bootstrapArgumentsOK(void) { return arguments_ok; }
const char *bootstrapSelector(void) { return selected; }
const char *bootstrapLoadPreload(void) { return load_preload; }
#ifndef NO_QUERY
const char *eglQueryString(void *display, int name) {
    calls++;
    arguments_ok = display == NULL && name == 0x3055;
    const char *value = getenv("__EGL_VENDOR_LIBRARY_FILENAMES");
    if (value) selected = strdup(value);
#ifdef NULL_QUERY
    return NULL;
#elif defined(EMPTY_QUERY)
    return "";
#elif defined(NO_PLATFORM_QUERY)
    return "EGL_KHR_client_get_all_proc_addresses";
#elif defined(INVALID_TOKEN_QUERY)
    return "prefixEGL_KHR_platform_wayland EGL_EXT_platform_wayland_suffix";
#elif defined(EXT_PLATFORM_QUERY)
    return "EGL_KHR_client_get_all_proc_addresses EGL_EXT_platform_wayland";
#else
    return "EGL_KHR_platform_wayland";
#endif
}
#endif
'''
PROGRAM = r'''
import ctypes, errno, fcntl, json, os, subprocess, sys
try:
    fcntl.fcntl(int(sys.argv[1]), fcntl.F_GETFD)
    closed = False
except OSError as error:
    assert error.errno == errno.EBADF
    closed = True
result = {"preload": os.environ.get("LD_PRELOAD"),
          "audit": os.environ.get("LD_AUDIT"),
          "selector": os.environ.get("__EGL_VENDOR_LIBRARY_FILENAMES"),
          "directories": os.environ.get("__EGL_VENDOR_LIBRARY_DIRS"), "closed": closed,
          "platform_hints": [os.environ.get("EGL_PLATFORM"), os.environ.get("QT_QPA_PLATFORM")]}
try:
    egl = ctypes.CDLL("libEGL.so.1", mode=os.RTLD_NOW | os.RTLD_NOLOAD)
except OSError:
    result["retained"] = False
else:
    result["retained"] = True
    result["calls"] = egl.bootstrapCalls()
    result["arguments_ok"] = egl.bootstrapArgumentsOK()
    for function, field in (("bootstrapSelector", "selected"),
                            ("bootstrapLoadPreload", "load_preload")):
        getter = getattr(egl, function)
        getter.restype = ctypes.c_char_p
        value = getter()
        result[field] = value.decode() if value is not None else None
child = subprocess.run([sys.executable, "-c",
    "import json, os; print(json.dumps({'environment': [os.environ.get('LD_PRELOAD'), "
    "os.environ.get('__EGL_VENDOR_LIBRARY_FILENAMES'), "
    "os.environ.get('__EGL_VENDOR_LIBRARY_DIRS')], 'platform_hints': "
    "[os.environ.get('EGL_PLATFORM'), os.environ.get('QT_QPA_PLATFORM')], "
    "'audit': os.environ.get('LD_AUDIT')}))"],
    text=True, capture_output=True, check=True)
child = json.loads(child.stdout)
result["child"] = child["environment"]
result["child_hints"] = child["platform_hints"]
result["child_audit"] = child["audit"]
print(json.dumps(result))
'''


def compile_library(source, output, *defines):
    subprocess.run(shlex.split(os.environ.get("CC", "cc")) + [
        "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror", *defines,
        str(source), "-o", str(output), "-ldl",
    ], check=True, capture_output=True, text=True)


with tempfile.TemporaryDirectory(prefix="modesty-egl-abi-") as directory:
    directory = Path(directory)
    helper = directory / "bootstrap.so"
    compile_library(ROOT / "scripts/egl-bootstrap.c", helper)
    fake_source = directory / "fake.c"
    fake_source.write_text(FAKE)
    libraries = {}
    for name, defines in (("valid", ()), ("null", ("-DNULL_QUERY",)),
                          ("empty", ("-DEMPTY_QUERY",)), ("no-query", ("-DNO_QUERY",)),
                          ("no-platform", ("-DNO_PLATFORM_QUERY",)),
                          ("invalid-token", ("-DINVALID_TOKEN_QUERY",)),
                          ("ext-platform", ("-DEXT_PLATFORM_QUERY",))):
        location = directory / name
        location.mkdir()
        compile_library(fake_source, location / "libEGL.so.1", *defines)
        libraries[name] = location
    unavailable = directory / "unavailable"
    unavailable.mkdir()
    (unavailable / "libEGL.so.1").write_text("Invalid ELF prevents system EGL fallback.")
    libraries["unavailable"] = unavailable
    inert_source = directory / "inert.c"
    inert_source.write_text("static void __attribute__((constructor)) inert(void) {}\n")
    inert = directory / "inert.so"
    compile_library(inert_source, inert)

    def run(name="valid", original=None, overrides=None, detach=False):
        environment = os.environ.copy()
        for variable in (*OVERRIDES, "LD_PRELOAD", "LD_AUDIT"):
            environment.pop(variable, None)
        environment.update(overrides or {})
        environment["LD_LIBRARY_PATH"] = str(libraries[name])
        with helper.open("rb") as pinned:
            descriptor = pinned.fileno()
            prefix = f"/proc/self/fd/{descriptor}"
            environment["LD_PRELOAD"] = prefix if original is None else prefix + ":" + original
            if detach:
                detached = directory / "detached.so"
                helper.rename(detached)
            try:
                process = subprocess.run([sys.executable, "-c", PROGRAM, str(descriptor)],
                    env=environment, pass_fds=(descriptor,), text=True, capture_output=True)
            finally:
                if detach:
                    detached.rename(helper)
        return process

    for original in (None, "", str(inert), f" :{inert}:: {inert}:"):
        process = run(original=original)
        assert process.returncode == 0, process.stderr
        result = json.loads(process.stdout)
        assert result["preload"] == original, result
        assert result["selector"] is None and result["directories"] is None, result
        assert result["closed"] and result["child"] == [original, None, None], result
        if original is None:
            assert result["retained"] and result["load_preload"] is None, result
            assert result["calls"] == 1 and result["arguments_ok"] == 1, result
            assert result["selected"] == MESA, result
        else:
            assert not result["retained"], result
    process = run(overrides={"LD_AUDIT": ""})
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["closed"] and not result["retained"] and result["preload"] is None, result
    assert result["audit"] == "" and result["child_audit"] == "", result
    assert result["selector"] is None and result["child"] == [None, None, None], result
    process = run(detach=True)
    assert process.returncode == 0 and json.loads(process.stdout)["calls"] == 1, process.stderr
    process = run("ext-platform")
    assert process.returncode == 0 and json.loads(process.stdout)["calls"] == 1, process.stderr
    print("PASS exact original preload/audit bypass, child isolation, closed descriptor, retained EGL, and pinned inode")

    for variable in OVERRIDES:
        for value in ("", "caller-value"):
            process = run(overrides={variable: value})
            assert process.returncode == 0, process.stderr
            result = json.loads(process.stdout)
            assert result["closed"] and result["preload"] is None and not result["retained"], result
            assert result["selector"] == (value if variable == SELECTOR else None), result
            assert result["directories"] == (value if variable == "__EGL_VENDOR_LIBRARY_DIRS" else None), result
            assert result["child"] == [None, result["selector"], result["directories"]], result
    print("PASS explicit EGL and GPU override presence, including empty values")

    qt_platforms = ("wayland", "wayland-egl", "wayland;xcb", "wayland-egl;xcb")
    hints = [{"EGL_PLATFORM": "wayland"}]
    hints += [{"QT_QPA_PLATFORM": value} for value in qt_platforms]
    hints += [{"EGL_PLATFORM": "wayland", "QT_QPA_PLATFORM": value} for value in qt_platforms]
    for values in hints:
        process = run(overrides=values)
        assert process.returncode == 0, process.stderr
        result = json.loads(process.stdout)
        expected = [values.get("EGL_PLATFORM"), values.get("QT_QPA_PLATFORM")]
        assert result["calls"] == 1 and result["selected"] == MESA, result
        assert result["platform_hints"] == expected and result["child_hints"] == expected, result
        assert result["closed"] and result["child"] == [None, None, None], result
    for variable, value in (("EGL_PLATFORM", "wayland-egl"),
                            ("EGL_PLATFORM", "wayland;xcb"),
                            ("QT_QPA_PLATFORM", "wayland;xcb;offscreen")):
        process = run(overrides={variable: value})
        assert process.returncode == 0, process.stderr
        result = json.loads(process.stdout)
        assert not result["retained"] and result["platform_hints"] == result["child_hints"], result
    print("PASS exact supported Wayland hints with unchanged child values; other hints bypass")

    for name in ("no-query", "unavailable"):
        process = run(name)
        assert process.returncode == 0, process.stderr
        result = json.loads(process.stdout)
        assert result["closed"] and result["selector"] is None and result["preload"] is None, result
        assert not result["retained"] and result["child"] == [None, None, None], result
    for name in ("null", "empty", "no-platform", "invalid-token"):
        process = run(name)
        assert process.returncode == 78 and not process.stdout, (name, process.returncode, process.stdout)
    print("PASS safe unavailable-EGL fallback and missing Wayland extension failure before main")
