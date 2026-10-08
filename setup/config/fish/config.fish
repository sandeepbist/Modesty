# Starship prompt setup
if status is-interactive
    command -v starship &>/dev/null && starship init fish | source
end

# Direnv + Zoxide
command -v direnv &>/dev/null && direnv hook fish | source
command -v zoxide &>/dev/null && zoxide init fish --cmd cd | source

# Better ls
command -v eza &>/dev/null && alias ls='eza --icons --group-directories-first -1'

# Abbrs
abbr lg 'lazygit'
abbr gd 'git diff'
abbr ga 'git add .'
abbr gc 'git commit -am'
abbr gl 'git log'
abbr gs 'git status'
abbr gst 'git stash'
abbr gsp 'git stash pop'
abbr gp 'git push'
abbr gpl 'git pull'
abbr gsw 'git switch'
abbr gsm 'git switch main'
abbr gb 'git branch'
abbr gbd 'git branch -d'
abbr gco 'git checkout'
abbr gsh 'git show'

abbr l 'ls'
abbr ll 'ls -l'
abbr la 'ls -a'
abbr lla 'ls -la'

# Custom colours
set -l modesty_state $HOME/.local/state
if set -q XDG_STATE_HOME; and test -n "$XDG_STATE_HOME"
    set modesty_state $XDG_STATE_HOME
end
cat "$modesty_state/modesty/sequences.txt" 2> /dev/null

# For jumping between prompts in foot terminal
function mark_prompt_start --on-event fish_prompt
    echo -en "\e]133;A\e\\"
end

# Custom fish config
set -q XDG_CONFIG_HOME && set -l cConf $XDG_CONFIG_HOME/modesty/desktop || set -l cConf $HOME/.config/modesty/desktop
source $cConf/user-config.fish 2> /dev/null
