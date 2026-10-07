#!/usr/bin/env bash
set -euo pipefail
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Python is needed by the interactive installer.' >&2
    for arg in "$@"; do
        if [[ "$arg" == --dry-run || "$arg" == --non-interactive ]]; then exit 1; fi
    done
    read -r -p 'Update Arch and install Python with pacman now? [Y/n] ' answer
    case "${answer,,}" in ''|y|yes) sudo pacman -Syu --needed python ;; *) exit 1 ;; esac
fi
exec python3 "$(dirname -- "$(realpath -- "$0")")/install.py" "$@"
