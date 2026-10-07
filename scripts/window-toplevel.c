/* Resolve the active window's stable Wayland capture identifier. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wayland-client.h>
#include "toplevel-protocol.h"

struct window { char *app, *title, *identifier; struct window *next; };
static struct window *windows;
static struct ext_foreign_toplevel_list_v1 *list;
static void closed(void *data, struct ext_foreign_toplevel_handle_v1 *handle) {
    struct window *w = data;
    free(w->identifier); w->identifier = NULL;
    ext_foreign_toplevel_handle_v1_destroy(handle);
}
static void done(void *data, struct ext_foreign_toplevel_handle_v1 *handle) { (void)data; (void)handle; }
static void title(void *data, struct ext_foreign_toplevel_handle_v1 *handle, const char *value) {
    (void)handle; struct window *w = data; free(w->title); w->title = strdup(value);
}
static void app(void *data, struct ext_foreign_toplevel_handle_v1 *handle, const char *value) {
    (void)handle; struct window *w = data; free(w->app); w->app = strdup(value);
}
static void identifier(void *data, struct ext_foreign_toplevel_handle_v1 *handle, const char *value) {
    (void)handle; struct window *w = data; free(w->identifier); w->identifier = strdup(value);
}
static const struct ext_foreign_toplevel_handle_v1_listener handle_listener = {closed, done, title, app, identifier};
static void toplevel(void *data, struct ext_foreign_toplevel_list_v1 *manager, struct ext_foreign_toplevel_handle_v1 *handle) {
    (void)data; (void)manager;
    struct window *w = calloc(1, sizeof(*w));
    if (!w) exit(1);
    w->next = windows; windows = w;
    ext_foreign_toplevel_handle_v1_add_listener(handle, &handle_listener, w);
}
static void finished(void *data, struct ext_foreign_toplevel_list_v1 *manager) { (void)data; (void)manager; }
static const struct ext_foreign_toplevel_list_v1_listener list_listener = {toplevel, finished};
static void global(void *data, struct wl_registry *registry, uint32_t name, const char *interface, uint32_t version) {
    (void)data; (void)version;
    if (!strcmp(interface, "ext_foreign_toplevel_list_v1")) {
        list = wl_registry_bind(registry, name, &ext_foreign_toplevel_list_v1_interface, 1);
        ext_foreign_toplevel_list_v1_add_listener(list, &list_listener, NULL);
    }
}
static void removed(void *data, struct wl_registry *registry, uint32_t name) { (void)data; (void)registry; (void)name; }
static const struct wl_registry_listener registry_listener = {global, removed};
int main(void) {
    const char *wanted_app = getenv("LUMA_WINDOW_APP"), *wanted_title = getenv("LUMA_WINDOW_TITLE");
    if (!wanted_app || !wanted_title) return 1;
    struct wl_display *display = wl_display_connect(NULL);
    if (!display) return 1;
    struct wl_registry *registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);
    if (wl_display_roundtrip(display) < 0 || !list || wl_display_roundtrip(display) < 0 || wl_display_roundtrip(display) < 0) return 1;
    /* Ambiguous duplicate titles must not select an unrelated window. */
    const char *match = NULL;
    for (struct window *w = windows; w; w = w->next) {
        if (w->app && w->title && w->identifier && !strcmp(w->app, wanted_app) && !strcmp(w->title, wanted_title)) {
            if (match) return 1;
            match = w->identifier;
        }
    }
    if (match) puts(match);
    wl_display_disconnect(display);
    return match ? 0 : 1;
}
