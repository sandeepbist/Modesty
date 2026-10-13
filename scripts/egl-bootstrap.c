#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int has_extension(const char *extensions, const char *name) {
    if (!extensions) return 0;
    size_t length = strlen(name);
    const char *match = extensions;
    while ((match = strstr(match, name))) {
        if ((match == extensions || match[-1] == ' ') &&
            (!match[length] || match[length] == ' ')) return 1;
        match += length;
    }
    return 0;
}

static void __attribute__((constructor)) bootstrap(void) {
    Dl_info own;
    const char *preload = getenv("LD_PRELOAD");
    if (!dladdr((void *)bootstrap, &own) || !own.dli_fname || !preload) _exit(78);

    size_t length = strlen(own.dli_fname);
    if (strncmp(preload, own.dli_fname, length) ||
        (preload[length] && preload[length] != ':' && preload[length] != ' ')) _exit(78);
    if (preload[length]) {
        if (setenv("LD_PRELOAD", preload + length + 1, 1)) _exit(78);
    } else if (unsetenv("LD_PRELOAD")) _exit(78);

    const char *prefix = "/proc/self/fd/";
    if (strncmp(own.dli_fname, prefix, strlen(prefix))) _exit(78);
    const char *number = own.dli_fname + strlen(prefix);
    char *end;
    errno = 0;
    long descriptor = strtol(number, &end, 10);
    if (*number < '0' || *number > '9' || *end || errno || descriptor > INT_MAX) _exit(78);
    close((int)descriptor);
    if (getenv("LD_PRELOAD") || getenv("LD_AUDIT")) return;

    static const char *const overrides[] = {
        "__EGL_VENDOR_LIBRARY_FILENAMES", "__EGL_VENDOR_LIBRARY_DIRS",
        "__NV_PRIME_RENDER_OFFLOAD", "__NV_PRIME_RENDER_OFFLOAD_PROVIDER",
        "__GLX_VENDOR_LIBRARY_NAME", "__VK_LAYER_NV_optimus", "DRI_PRIME",
        "QT_OPENGL", "QSG_RHI_BACKEND", "QT_QUICK_BACKEND",
        "QT_WAYLAND_RECONNECT", "QT_WAYLAND_CLIENT_BUFFER_INTEGRATION",
        "QT_WAYLAND_SERVER_BUFFER_INTEGRATION", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"
    };
    for (size_t i = 0; i < sizeof(overrides) / sizeof(overrides[0]); i++) {
        if (getenv(overrides[i])) return;
    }
    const char *platform = getenv("EGL_PLATFORM");
    if (platform && strcmp(platform, "wayland")) return;
    const char *qt_platform = getenv("QT_QPA_PLATFORM");
    if (qt_platform && strcmp(qt_platform, "wayland") &&
        strcmp(qt_platform, "wayland-egl") && strcmp(qt_platform, "wayland;xcb") &&
        strcmp(qt_platform, "wayland-egl;xcb")) return;

    void *egl = dlopen("libEGL.so.1", RTLD_NOW | RTLD_LOCAL);
    if (!egl) return;
    const char *(*query)(void *, int) = dlsym(egl, "eglQueryString");
    if (!query) {
        dlclose(egl);
        return;
    }
    if (setenv("__EGL_VENDOR_LIBRARY_FILENAMES",
               "/usr/share/glvnd/egl_vendor.d/50_mesa.json", 1)) return;
    const char *extensions = query(NULL, 0x3055);
    if (unsetenv("__EGL_VENDOR_LIBRARY_FILENAMES") ||
        !(has_extension(extensions, "EGL_KHR_platform_wayland") ||
          has_extension(extensions, "EGL_EXT_platform_wayland"))) _exit(78);
    /* Keep libEGL loaded so Qt reuses its initialized vendor cache. */
}
