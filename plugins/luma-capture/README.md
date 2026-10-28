# Experimental private Luma capture

This plugin renders a separate desktop scene for compositor-managed monitor and
region captures. It omits Luma's canvas and the entire Modesty island, including
their popups. Local rendering and keyboard interaction keep working. Captured
content behind the omitted surfaces continues to update.

The island shares one client surface with Luma indicators, so its clock, dock and
controls are also absent from the capture. Capture omits all closing snapshots,
drag previews, IME overlays and cursor images. Those remain available locally.

Only Hyprland build `c26dbf9337998ba9afcfe84050e36969bb787598` with matching
headers and dependency ABI is supported. The first implementation accepts GL,
sRGB, scale 1, unrotated, non-mirrored outputs. Unsupported capture requests fail.
If rendering fails after a request starts, the client receives a failed frame.
The export target stays black rather than receiving the normal desktop texture.
The plugin refuses to load while a capture session or permission snapshot exists.
Stop capture before loading so an old, unfiltered frame cannot be delivered later.

## Opt in

In Modesty, open **Settings → Luma → Assistant → Screen sharing** and toggle
**Hide Luma from screen sharing**. The switch shows the saved setting; the status
below it reports whether protection is active. Refresh checks changes made from
the command line. Stop sharing before changing the setting.

Enable it from this checkout on the supported setup:

```sh
python3 scripts/luma-capture.py enable
python3 scripts/luma-capture.py status
```

The helper loads the plugin before persisting the enabled state. It registers a
guarded Lua bootstrap in the installed Hyprland `execs.lua`, preserving existing
content. On later starts, native capture protection applies before the helper
restores the plugin. If the installed compositor becomes incompatible, restoration
fails and native protection can black out the shared monitor. Check `status` after
a compositor update. Both `enabled` and `loaded` must be true for this feature.

Luma still opens with Super+Space and accepts keyboard input. No per-call toggle
is needed. To turn off the feature, stop sharing first, then run:

```sh
python3 scripts/luma-capture.py disable
```

The guarded bootstrap stays installed but becomes inactive. If enable fails while
writing its first state file, the helper unloads the newly loaded plugin. If a
later write or reload fails, the state file remains so `disable` can recover.
Changes to the compiled plugin require disabling the old build before enabling
the new one in the same session.

A failed unload keeps the saved plugin path so `disable` can retry. If the final
configuration reload fails after unloading, run `disable` again even when the
saved setting is already off.

## Build and verify

Run from this checkout:

```sh
python3 scripts/luma-capture.py build
python3 scripts/luma-capture.py test
python3 scripts/luma-capture.py status
```

Building requires the matching Hyprland development files, `pkg-config` and a
C++23 compiler. Verification additionally requires Quickshell, Pillow, `grim`,
`wtype`, `wf-recorder` and FFmpeg. It opens a separate nested compositor window,
loads the plugin only there and closes its own processes afterward. It never
loads the plugin into the current desktop. Evidence stays in
`output/luma-capture/`.

The verification compares captured pixels against a changing background and a
local view of the private surface. It checks native black masking as a baseline,
full-monitor and region captures, continuous recording, popup and island
exclusion, animated close/reopen, local typing and plugin unload.
It also compares a public window's blur with the private overlay open and closed,
and checks that unsupported scaling refuses capture without crashing.
Full fixture images and lossless video frames are compared with the expected
public image. Pass `--production` to the verification script to also exercise the
real canvas in preview mode. Pass `--with-plugin PATH` for each additional plugin
to check coexistence. With scrolloverview loaded, verification opens the overview
and compares its captured image with the ordinary desktop capture.
Pass `--loader` to exercise the real enable/restore/disable helper and a fresh
nested startup. It writes only that nested compositor's temporary configuration.

The expired-session regression uses the installed Wayland protocol XML:

```sh
python3 tests/luma-capture-protocol.py --output-dir output/luma-protocol-build
```

Pass the printed executable as `--session-client PATH` to the live verification.
The client requires the harness's explicit test marker and nested socket. The
verification also compares legacy alpha-discard blur against native rendering
over a checkerboard. Run directories retain source and binary hash manifests.

## Review and limits

The isolated verification can exercise the production canvas, protocol lifecycle,
legacy blur, additional plugins and cold-start restoration. The callback check
exercises frame completion and destruction under ASan and UBSan.
Application-level recipient verification remains separate and incomplete.
The implementation uses seven
internal function hooks and temporarily exchanges renderer resources during a
synchronous capture pass. A compositor plugin can crash the desktop if its
assumptions are wrong. Do not treat the nested fixture as proof of compatibility
with other plugins, the portal, Google Meet or Discord.

This protects the compositor capture path. A camera, privileged GPU capture or
another compositor capturing a nested desktop can still see the local image.
Focus changes or actions performed in shared applications can reveal activity.
Compositor notification, error and debug overlays are omitted from the clean
capture scene. Active overview visuals are omitted too; the capture keeps showing
the underlying workspace. The native clients still control their layout and
repaint timing after output changes.

This is an experimental feature for the supported compositor setup, not a
universal capture exclusion guarantee.
