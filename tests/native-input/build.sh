#!/usr/bin/env bash
set -euo pipefail
base=$(cd -- "$(dirname -- "$0")" && pwd)
out=$(mktemp -d /tmp/modesty-pointer.XXXXXX)
wayland-scanner client-header "$base/protocol.xml" "$out/pointer.h"
wayland-scanner private-code "$base/protocol.xml" "$out/protocol.c"
cc -I"$out" "$base/pointer.c" "$out/protocol.c" -o "$out/input" $(pkg-config --cflags --libs wayland-client)
printf '%s\n' "$out/input"
