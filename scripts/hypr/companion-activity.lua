-- Anonymous activity only. The callback intentionally accepts no key data.
-- Restrict pulses to Zen and terminal windows, at most once per second.
if _G.modestyCompanionInput then _G.modestyCompanionInput:remove() end
local lastPulse = 0
_G.modestyCompanionInput = hl.on("input.keyboard.key", function()
    local now = os.time()
    if now == lastPulse then return end
    local window = hl.get_active_window()
    if not window then return end
    local class = string.lower(window.class or "")
    if class ~= "zen" and class ~= "zen-browser" and class ~= "app.zen_browser.zen"
        and class ~= "foot" and class ~= "footclient" and class ~= "kitty"
        and class ~= "alacritty" and class ~= "org.wezfurlong.wezterm"
        and class ~= "com.mitchellh.ghostty" then return end
    lastPulse = now
    hl.dispatch(hl.dsp.event("modesty-input"))
end)
