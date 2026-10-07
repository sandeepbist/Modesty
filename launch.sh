#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
case "${1:-}" in
    --switch)
        exec python3 scripts/session-control.py enable
        ;;
    --restore)
        exec python3 scripts/session-control.py restore
        ;;
    --check)
        exec python3 scripts/session-control.py check
        ;;
    --preview)
        export MODESTY_PREVIEW=1
        exec quickshell --no-duplicate --path "$PWD/preview.qml"
        ;;
    --compat)
        if quickshell list --all 2>/dev/null | rg -q 'Config path: .*caelestia/shell.qml'; then
            echo 'Caelestia is still running. Stop it before starting compatibility mode.' >&2
            echo 'Use ./launch.sh --preview to try the UI alongside your current setup.' >&2
            exit 1
        fi
        export MODESTY_COMPAT=1
        ;;
    --help|-h)
        echo 'Usage: ./launch.sh [--preview | --compat | --check | --switch | --restore]'
        echo 'Default: run the island alongside your existing shell.'
        echo '--preview: isolated window; system actions disabled.'
        echo '--compat: handle existing Caelestia shortcut names after Caelestia is stopped.'
        echo '--check: validate the reversible main-shell handoff without changing anything.'
        echo '--switch: use Modesty now and at login; preserve app/workspace binds and gaps.'
        echo '--restore: restore Caelestia and its shell-specific startup/restart bindings.'
        exit 0
        ;;
    '') ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
esac
exec quickshell --no-duplicate --path "$PWD/shell.qml"
