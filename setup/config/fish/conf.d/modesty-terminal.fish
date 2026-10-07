# Foot supplies the blink cadence; Fish keeps the editing cursor a beam.
if status is-interactive
    set -g fish_cursor_default line blink
    set -g fish_cursor_insert line blink
    set -g fish_cursor_replace_one underscore
    set -g fish_cursor_replace underscore
    set -g fish_cursor_visual block
end
