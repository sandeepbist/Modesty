function modesty-terminal --description 'Open Modesty Kitty with a short cursor trail'
    if not command -sq kitty
        echo 'Kitty is not installed. Install the optional kitty package to use this profile.' >&2
        return 127
    end
    set -l config $HOME/.config
    if set -q XDG_CONFIG_HOME; and test -n "$XDG_CONFIG_HOME"
        set config $XDG_CONFIG_HOME
    end
    if not test -f "$config/kitty/modesty.conf"; or not test -f "$config/kitty/modesty-effects.conf"
        echo 'Modesty Kitty profile is missing. Run optional terminal setup from Settings.' >&2
        return 1
    end
    command kitty --config "$config/kitty/modesty.conf" $argv
end
