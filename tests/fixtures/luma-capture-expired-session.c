#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <wayland-client.h>

#include "ext-image-capture-source-v1-client-protocol.h"
#include "ext-image-copy-capture-v1-client-protocol.h"

static const uint32_t formats[] = {
    WL_SHM_FORMAT_XRGB8888, WL_SHM_FORMAT_ARGB8888,
    WL_SHM_FORMAT_XBGR8888, WL_SHM_FORMAT_ABGR8888,
    WL_SHM_FORMAT_XRGB2101010, WL_SHM_FORMAT_ARGB2101010,
    WL_SHM_FORMAT_XBGR2101010, WL_SHM_FORMAT_ABGR2101010,
};

static struct {
    struct wl_display *display;
    struct wl_output *output;
    struct wl_shm *shm;
    struct ext_output_image_capture_source_manager_v1 *source_manager;
    struct ext_image_copy_capture_manager_v1 *capture_manager;
    uint32_t output_id, shm_formats, capture_formats, width, height, reason;
    unsigned size_events, damage_events, transform_events;
    bool constraints_done, capture_sent;
    int terminal;
} state;

static void die(const char *format, ...) {
    va_list args;
    fputs("FAIL: ", stderr);
    va_start(args, format);
    vfprintf(stderr, format, args);
    va_end(args);
    fputc('\n', stderr);
    exit(1);
}

static void timed_out(int signal_number) {
    static const char message[] = "FAIL: Wayland regression timed out\n";
    (void)write(STDERR_FILENO, message, sizeof(message) - 1);
    _exit(124);
}

static void check_dispatch(int result, const char *phase) {
    if (result >= 0)
        return;
    const struct wl_interface *interface = NULL;
    uint32_t object_id = 0;
    uint32_t code = wl_display_get_protocol_error(state.display, &interface, &object_id);
    die("%s: display error=%d (%s), protocol=%s object=%" PRIu32 " code=%" PRIu32,
        phase, wl_display_get_error(state.display),
        strerror(wl_display_get_error(state.display)),
        interface ? interface->name : "none", object_id, code);
}

static void sync_display(const char *phase) {
    check_dispatch(wl_display_roundtrip(state.display), phase);
}

static uint32_t format_bit(uint32_t format) {
    for (unsigned i = 0; i < sizeof(formats) / sizeof(formats[0]); ++i)
        if (formats[i] == format)
            return 1u << i;
    return 0;
}

static void shm_format(void *data, struct wl_shm *shm, uint32_t format) {
    state.shm_formats |= format_bit(format);
}

static const struct wl_shm_listener shm_listener = {.format = shm_format};

static void output_geometry(void *data, struct wl_output *output, int32_t x, int32_t y,
                            int32_t physical_width, int32_t physical_height,
                            int32_t subpixel, const char *make, const char *model,
                            int32_t transform) {}

static void output_mode(void *data, struct wl_output *output, uint32_t flags,
                        int32_t width, int32_t height, int32_t refresh) {}

static const struct wl_output_listener output_listener = {
    .geometry = output_geometry, .mode = output_mode,
};

static void global(void *data, struct wl_registry *registry, uint32_t name,
                   const char *interface, uint32_t version) {
    if (!state.output && strcmp(interface, wl_output_interface.name) == 0) {
        state.output = wl_registry_bind(registry, name, &wl_output_interface, 1);
        state.output_id = name;
        wl_output_add_listener(state.output, &output_listener, NULL);
    } else if (!state.shm && strcmp(interface, wl_shm_interface.name) == 0) {
        state.shm = wl_registry_bind(registry, name, &wl_shm_interface, 1);
        wl_shm_add_listener(state.shm, &shm_listener, NULL);
    } else if (!state.source_manager &&
               strcmp(interface, ext_output_image_capture_source_manager_v1_interface.name) == 0) {
        state.source_manager = wl_registry_bind(
            registry, name, &ext_output_image_capture_source_manager_v1_interface, 1);
    } else if (!state.capture_manager &&
               strcmp(interface, ext_image_copy_capture_manager_v1_interface.name) == 0) {
        state.capture_manager = wl_registry_bind(
            registry, name, &ext_image_copy_capture_manager_v1_interface, 1);
    }
}

static void global_remove(void *data, struct wl_registry *registry, uint32_t name) {
    if (name == state.output_id)
        die("selected output disappeared");
}

static const struct wl_registry_listener registry_listener = {
    .global = global, .global_remove = global_remove,
};

static void constraint_event(void) {
    if (state.constraints_done)
        die("output constraints changed during this regression; use a stable nested output");
}

static void buffer_size(void *data, struct ext_image_copy_capture_session_v1 *session,
                        uint32_t width, uint32_t height) {
    constraint_event();
    state.width = width;
    state.height = height;
    ++state.size_events;
}

static void capture_shm_format(void *data, struct ext_image_copy_capture_session_v1 *session,
                               uint32_t format) {
    constraint_event();
    state.capture_formats |= format_bit(format);
    fprintf(stderr, "session.shm_format=%" PRIu32 "\n", format);
}

static void dmabuf_device(void *data, struct ext_image_copy_capture_session_v1 *session,
                          struct wl_array *device) {
    constraint_event();
}

static void dmabuf_format(void *data, struct ext_image_copy_capture_session_v1 *session,
                          uint32_t format, struct wl_array *modifiers) {
    constraint_event();
}

static void constraints_done(void *data, struct ext_image_copy_capture_session_v1 *session) {
    constraint_event();
    if (state.size_events != 1 || !state.width || !state.height)
        die("constraints.done without exactly one nonzero buffer_size");
    state.constraints_done = true;
    fprintf(stderr, "session.done size=%" PRIu32 "x%" PRIu32 "\n", state.width, state.height);
}

static void session_stopped(void *data, struct ext_image_copy_capture_session_v1 *session) {
    die("session stopped before the explicit session.destroy request");
}

static const struct ext_image_copy_capture_session_v1_listener session_listener = {
    .buffer_size = buffer_size, .shm_format = capture_shm_format,
    .dmabuf_device = dmabuf_device, .dmabuf_format = dmabuf_format,
    .done = constraints_done, .stopped = session_stopped,
};

static void transform(void *data, struct ext_image_copy_capture_frame_v1 *frame,
                      uint32_t value) {
    ++state.transform_events;
}

static void damage(void *data, struct ext_image_copy_capture_frame_v1 *frame,
                   int32_t x, int32_t y, int32_t width, int32_t height) {
    ++state.damage_events;
}

static void presentation_time(void *data, struct ext_image_copy_capture_frame_v1 *frame,
                              uint32_t high, uint32_t low, uint32_t nanoseconds) {
    die("unexpected frame.presentation_time on a stopped capture");
}

static void ready(void *data, struct ext_image_copy_capture_frame_v1 *frame) {
    die("unexpected frame.ready; expected frame.failed(reason=stopped)");
}

static void failed(void *data, struct ext_image_copy_capture_frame_v1 *frame, uint32_t reason) {
    if (!state.capture_sent || state.terminal)
        die("frame.failed arrived before capture or after a terminal event");
    state.terminal = 1;
    state.reason = reason;
    fprintf(stderr, "frame.failed reason=%" PRIu32 "\n", reason);
    ext_image_copy_capture_frame_v1_destroy(frame);
}

static const struct ext_image_copy_capture_frame_v1_listener frame_listener = {
    .transform = transform, .damage = damage, .presentation_time = presentation_time,
    .ready = ready, .failed = failed,
};

int main(int argc, char **argv) {
    const char *marker = getenv("MODESTY_CAPTURE_TEST");
    const char *display_name = getenv("WAYLAND_DISPLAY");
    if (!marker || strcmp(marker, "1") != 0 || !display_name || !*display_name) {
        fputs("Refusing connection: require MODESTY_CAPTURE_TEST=1 and explicit nested WAYLAND_DISPLAY.\n", stderr);
        return 2;
    }
    if (getenv("WAYLAND_SOCKET")) {
        fputs("Refusing connection: unset WAYLAND_SOCKET so WAYLAND_DISPLAY selects the nested socket.\n", stderr);
        return 2;
    }
    unsigned timeout = 10;
    if (argc > 2) {
        fprintf(stderr, "Usage: %s [timeout-seconds:1..120]\n", argv[0]);
        return 2;
    }
    if (argc == 2) {
        char *end;
        errno = 0;
        unsigned long value = strtoul(argv[1], &end, 10);
        if (errno || !*argv[1] || *end || value < 1 || value > 120) {
            fputs("Invalid timeout: expected an integer from 1 to 120.\n", stderr);
            return 2;
        }
        timeout = (unsigned)value;
    }
    struct sigaction action = {.sa_handler = timed_out};
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGALRM, &action, NULL) != 0)
        die("sigaction: %s", strerror(errno));
    alarm(timeout);

    state.display = wl_display_connect(display_name);
    if (!state.display)
        die("connect to explicit WAYLAND_DISPLAY: %s", strerror(errno));
    struct wl_registry *registry = wl_display_get_registry(state.display);
    wl_registry_add_listener(registry, &registry_listener, NULL);
    sync_display("registry globals");
    sync_display("wl_shm formats");
    if (!state.output || !state.shm || !state.source_manager || !state.capture_manager)
        die("require wl_output, wl_shm, ext_output_image_capture_source_manager_v1 and ext_image_copy_capture_manager_v1");

    struct ext_image_capture_source_v1 *source =
        ext_output_image_capture_source_manager_v1_create_source(state.source_manager, state.output);
    struct ext_image_copy_capture_session_v1 *session =
        ext_image_copy_capture_manager_v1_create_session(state.capture_manager, source, 0);
    ext_image_copy_capture_session_v1_add_listener(session, &session_listener, NULL);
    sync_display("initial buffer constraints");
    while (!state.constraints_done)
        check_dispatch(wl_display_dispatch(state.display), "waiting for constraints.done");

    uint32_t candidates = state.shm_formats & state.capture_formats;
    if (!candidates)
        die("no common advertised packed 32-bit wl_shm format");
    unsigned format_index = 0;
    while (!(candidates & (1u << format_index)))
        ++format_index;
    uint32_t format = formats[format_index];
    if (state.width > INT32_MAX / 4 || state.height > INT32_MAX / (state.width * 4))
        die("buffer dimensions exceed wl_shm signed 32-bit size limits");
    int32_t stride = (int32_t)(state.width * 4);
    int32_t size = stride * (int32_t)state.height;
    int fd = memfd_create("modesty-luma-regression", MFD_CLOEXEC);
    if (fd < 0 || ftruncate(fd, size) != 0)
        die("allocate wl_shm backing file: %s", strerror(errno));
    struct wl_shm_pool *pool = wl_shm_create_pool(state.shm, fd, size);
    struct wl_buffer *buffer = wl_shm_pool_create_buffer(
        pool, 0, (int32_t)state.width, (int32_t)state.height, stride, format);
    wl_shm_pool_destroy(pool);
    close(fd);

    struct ext_image_copy_capture_frame_v1 *frame =
        ext_image_copy_capture_session_v1_create_frame(session);
    ext_image_copy_capture_frame_v1_add_listener(frame, &frame_listener, NULL);
    ext_image_copy_capture_frame_v1_attach_buffer(frame, buffer);
    ext_image_copy_capture_frame_v1_damage_buffer(frame, 0, 0, (int32_t)state.width, (int32_t)state.height);
    sync_display("create frame, attach valid wl_shm buffer, damage full buffer");
    fprintf(stderr, "frame prepared format=%" PRIu32 " stride=%" PRId32 "\n", format, stride);

    ext_image_copy_capture_session_v1_destroy(session);
    sync_display("session.destroy processed while retaining frame");
    fputs("session.destroy processed; sending retained frame.capture\n", stderr);
    state.capture_sent = true;
    ext_image_copy_capture_frame_v1_capture(frame);
    sync_display("capture after session.destroy");
    while (!state.terminal)
        check_dispatch(wl_display_dispatch(state.display), "waiting for frame.failed");
    if (state.reason != EXT_IMAGE_COPY_CAPTURE_FRAME_V1_FAILURE_REASON_STOPPED)
        die("expected frame.failed(reason=2/stopped), got %" PRIu32, state.reason);

    wl_buffer_destroy(buffer);
    ext_image_capture_source_v1_destroy(source);
    ext_output_image_capture_source_manager_v1_destroy(state.source_manager);
    ext_image_copy_capture_manager_v1_destroy(state.capture_manager);
    sync_display("post-failure compositor liveness and frame cleanup");
    wl_display_disconnect(state.display);
    alarm(0);
    printf("{\"test\":\"session-destroy-before-capture\",\"status\":\"pass\","
           "\"failure_reason\":%" PRIu32 ",\"compositor_alive\":true,"
           "\"width\":%" PRIu32 ",\"height\":%" PRIu32 ",\"shm_format\":%" PRIu32 ","
           "\"damage_events\":%u,\"transform_events\":%u}\n",
           state.reason, state.width, state.height, format, state.damage_events, state.transform_events);
    return 0;
}
