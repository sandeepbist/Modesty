#define _GNU_SOURCE
#include <wayland-client.h>
#include <xkbcommon/xkbcommon.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const struct wl_message keyboard_requests[] = {
    {"keymap", "uhu", NULL}, {"key", "uuu", NULL}, {"modifiers", "uuuu", NULL}, {"destroy", "", NULL}};
static const struct wl_interface keyboard_interface = {"zwp_virtual_keyboard_v1", 1, 4, keyboard_requests, 0, NULL};
static const struct wl_interface* keyboard_create_types[] = {&wl_seat_interface, &keyboard_interface};
static const struct wl_message keyboard_manager_requests[] = {{"create_virtual_keyboard", "on", keyboard_create_types}};
static const struct wl_interface keyboard_manager_interface = {"zwp_virtual_keyboard_manager_v1", 1, 1, keyboard_manager_requests, 0, NULL};
static const struct wl_message pointer_requests[] = {
    {"motion", "uff", NULL}, {"motion_absolute", "uuuuu", NULL}, {"button", "uuu", NULL},
    {"axis", "uuf", NULL}, {"frame", "", NULL}, {"axis_source", "u", NULL},
    {"axis_stop", "uu", NULL}, {"axis_discrete", "uufi", NULL}, {"destroy", "", NULL}};
static const struct wl_interface pointer_interface = {"zwlr_virtual_pointer_v1", 1, 9, pointer_requests, 0, NULL};
static const struct wl_interface* pointer_create_types[] = {&wl_seat_interface, &pointer_interface};
static const struct wl_message pointer_manager_requests[] = {
    {"create_virtual_pointer", "?on", pointer_create_types}, {"destroy", "", NULL}};
static const struct wl_interface pointer_manager_interface = {"zwlr_virtual_pointer_manager_v1", 1, 2, pointer_manager_requests, 0, NULL};
static const struct wl_message grab_requests[] = {{"release", "", NULL}};
static const struct wl_message grab_events[] = {{"keymap", "uhu", NULL}, {"key", "uuuu", NULL}, {"modifiers", "uuuuu", NULL}, {"repeat_info", "ii", NULL}};
static const struct wl_interface grab_interface = {"zwp_input_method_keyboard_grab_v2", 1, 1, grab_requests, 4, grab_events};
static const struct wl_interface* grab_types[] = {&grab_interface};
static const struct wl_message ime_requests[] = {
    {"commit_string", "s", NULL}, {"set_preedit_string", "sii", NULL}, {"delete_surrounding_text", "uu", NULL},
    {"commit", "u", NULL}, {"get_input_popup_surface", "no", NULL}, {"grab_keyboard", "n", grab_types}, {"destroy", "", NULL}};
static const struct wl_message ime_events[] = {{"activate", "", NULL}, {"deactivate", "", NULL}, {"surrounding_text", "suu", NULL},
    {"text_change_cause", "u", NULL}, {"content_type", "uu", NULL}, {"done", "", NULL}, {"unavailable", "", NULL}};
static const struct wl_interface ime_interface = {"zwp_input_method_v2", 1, 7, ime_requests, 7, ime_events};
static const struct wl_interface* ime_types[] = {&wl_seat_interface, &ime_interface};
static const struct wl_message ime_manager_requests[] = {{"get_input_method", "on", ime_types}, {"destroy", "", NULL}};
static const struct wl_interface ime_manager_interface = {"zwp_input_method_manager_v2", 1, 2, ime_manager_requests, 0, NULL};

static struct wl_display* display;
static struct wl_seat* seat;
static struct wl_proxy *keyboard_manager, *pointer_manager, *pointer, *keyboards[2];
static struct wl_proxy *ime_manager, *ime, *grab;
static struct xkb_context* context;
static unsigned int ime_keys;

static uint32_t now(void) {
    struct timespec value;
    clock_gettime(CLOCK_MONOTONIC, &value);
    return value.tv_sec*1000+value.tv_nsec/1000000;
}

static void global(void* data, struct wl_registry* registry, uint32_t name, const char* interface, uint32_t version) {
    if (!strcmp(interface, "wl_seat")) seat = wl_registry_bind(registry, name, &wl_seat_interface, 1);
    if (!strcmp(interface, keyboard_manager_interface.name)) keyboard_manager = wl_registry_bind(registry, name, &keyboard_manager_interface, 1);
    if (!strcmp(interface, pointer_manager_interface.name)) pointer_manager = wl_registry_bind(registry, name, &pointer_manager_interface, 1);
    if (!strcmp(interface, ime_manager_interface.name)) ime_manager = wl_registry_bind(registry, name, &ime_manager_interface, 1);
}
static void removed(void* data, struct wl_registry* registry, uint32_t name) {}
static const struct wl_registry_listener listener = {.global=global, .global_remove=removed};

static int ignore_event(const void* implementation, void* target, uint32_t opcode, const struct wl_message* message, union wl_argument* args) {
    if (!strcmp(message->signature, "uhu")) close(args[1].h);
    if (!strcmp(wl_proxy_get_class(target), grab_interface.name) && opcode==1) ++ime_keys;
    return 0;
}

static void add_keyboard(unsigned int index, const char* layout) {
    if (keyboards[index]) wl_proxy_marshal_flags(keyboards[index], 3, NULL, 1, WL_MARSHAL_FLAG_DESTROY);
    keyboards[index] = wl_proxy_marshal_flags(keyboard_manager, 0, &keyboard_interface, 1, 0, seat, NULL);
    const struct xkb_rule_names names = {.layout=layout};
    struct xkb_keymap* keymap = xkb_keymap_new_from_names(context, &names, XKB_KEYMAP_COMPILE_NO_FLAGS);
    if (!keymap) exit(5);
    char* text = xkb_keymap_get_as_string(keymap, XKB_KEYMAP_FORMAT_TEXT_V1);
    const size_t size = strlen(text)+1;
    int fd = memfd_create("luma-private-test-map", 0);
    if (fd < 0 || write(fd, text, size) != (ssize_t)size) exit(6);
    wl_proxy_marshal_flags(keyboards[index], 0, NULL, 1, 0, WL_KEYBOARD_KEYMAP_FORMAT_XKB_V1, fd, size);
    wl_display_roundtrip(display);
    close(fd);free(text);xkb_keymap_unref(keymap);
}

int main(void) {
    if (!getenv("MODESTY_PRIVATE_TEST")) return 2;
    display = wl_display_connect(NULL);
    if (!display) return 3;
    struct wl_registry* registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &listener, NULL);
    wl_display_roundtrip(display);
    if (!seat || !keyboard_manager || !pointer_manager) return 4;
    context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    add_keyboard(0, "us");
    pointer = wl_proxy_marshal_flags(pointer_manager, 0, &pointer_interface, 1, 0, seat, NULL);
    char line[256], command[32], layout[64];
    unsigned int a,b,c,d,e;
    puts("ready");fflush(stdout);
    while (fgets(line, sizeof(line), stdin)) {
        if (sscanf(line, "%31s", command) != 1) continue;
        if (!strcmp(command, "key") && sscanf(line, "%*s %u %u %u", &a,&b,&c)==3 && a<2 && keyboards[a])
            wl_proxy_marshal_flags(keyboards[a], 1, NULL, 1, 0, now(), b, c);
        else if (!strcmp(command, "mods") && sscanf(line, "%*s %u %u %u %u %u", &a,&b,&c,&d,&e)==5 && a<2 && keyboards[a])
            wl_proxy_marshal_flags(keyboards[a], 2, NULL, 1, 0, b,c,d,e);
        else if (!strcmp(command, "move") && sscanf(line, "%*s %u %u %u %u", &a,&b,&c,&d)==4)
            wl_proxy_marshal_flags(pointer, 1, NULL, 1, 0, now(), a,b,c,d);
        else if (!strcmp(command, "button") && sscanf(line, "%*s %u %u", &a,&b)==2)
            wl_proxy_marshal_flags(pointer, 2, NULL, 1, 0, now(), a,b);
        else if (!strcmp(command, "axis") && sscanf(line, "%*s %u", &a)==1)
            wl_proxy_marshal_flags(pointer, 3, NULL, 1, 0, now(), 0, wl_fixed_from_int(a));
        else if (!strcmp(command, "map") && sscanf(line, "%*s %u %63s", &a,layout)==2 && a<2) add_keyboard(a, layout);
        else if (!strcmp(command, "remove") && sscanf(line, "%*s %u", &a)==1 && a<2 && keyboards[a]) {
            wl_proxy_marshal_flags(keyboards[a], 3, NULL, 1, WL_MARSHAL_FLAG_DESTROY);keyboards[a]=NULL;
        } else if ((!strcmp(command, "ime-on") || !strcmp(command, "ime-key")) && ime_manager && !ime) {
            ime = wl_proxy_marshal_flags(ime_manager, 0, &ime_interface, 1, 0, seat, NULL);
            wl_proxy_add_dispatcher(ime, ignore_event, NULL, NULL);
            grab = wl_proxy_marshal_flags(ime, 5, &grab_interface, 1, 0, NULL);
            wl_proxy_add_dispatcher(grab, ignore_event, NULL, NULL);
            if (!strcmp(command, "ime-key")) {
                wl_proxy_marshal_flags(keyboards[0], 1, NULL, 1, 0, now(), 30, 1);
                wl_proxy_marshal_flags(keyboards[0], 1, NULL, 1, 0, now(), 30, 0);
            }
        } else if (!strcmp(command, "ime-empty")) {
            if (ime_keys) return 9;
        } else if (!strcmp(command, "ime-off") && ime) {
            wl_proxy_marshal_flags(grab, 0, NULL, 1, WL_MARSHAL_FLAG_DESTROY);grab=NULL;
            wl_proxy_marshal_flags(ime, 6, NULL, 1, WL_MARSHAL_FLAG_DESTROY);ime=NULL;
        } else return 7;
        wl_proxy_marshal_flags(pointer, 4, NULL, 1, 0);
        if (wl_display_roundtrip(display)<0) return 8;
        puts("ok");fflush(stdout);
    }
    wl_display_disconnect(display);
    xkb_context_unref(context);
}
