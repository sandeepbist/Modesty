function fish_greeting
    if status is-interactive; and not set -q MODESTY_NO_GREETING
        python3 @MODESTY_ROOT@/scripts/terminal-greeting.py
    end
end
