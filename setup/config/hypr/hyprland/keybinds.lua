local vars = require("variables")
local fn   = require("utils.functions")
local modestyBindings = dofile("@MODESTY_ROOT@/scripts/hypr/desktop-bindings.lua")


-- Flags
local locked           = { locked = true }
local mouse            = { mouse = true }
local release          = { release = true }
local repeating        = { repeating = true }
local locked_repeating = { locked = true, repeating = true }

local function normalise_keybind(key)
    return key:gsub("%s+", ""):lower()
end

local function valid_keybind(key)
    return type(key) == "string" and key:match("%S") ~= nil
end

local function repeating_unless_mouse(key)
    return not normalise_keybind(key):find("mouse", 1, true) and repeating or nil
end

local function flatten_keybinds(keybinds, keys)
    keys = keys or {}

    if type(keybinds) == "table" then
        for _, keybind in pairs(keybinds) do
            flatten_keybinds(keybind, keys)
        end
    elseif valid_keybind(keybinds) then
        keys[#keys + 1] = keybinds
    end

    return keys
end

local function create_bind(spec, action, flags)
    for _,key in ipairs(flatten_keybinds(spec.keys)) do
        modestyBindings:register(spec.__modesty_id, spec.__modesty_label, key, action, flags)
    end
end

local function extend_keybind(base, suffix)
    return valid_keybind(base) and base .. " + " .. suffix or nil
end

-- Launcher
local launcher_default = normalise_keybind("SUPER + SUPER_L")
create_bind({__modesty_id="kbLauncher", __modesty_label="Applications", keys=vars.kbLauncher},
    hl.dsp.exec_cmd("quickshell ipc -p @MODESTY_ROOT@/shell.qml call island toggle launcher"),
    function(key)
        return normalise_keybind(key) == launcher_default and release or nil
    end
)
create_bind({__modesty_id="kbCommandCanvas", __modesty_label="Quick Search", keys=vars.kbCommandCanvas},
    hl.dsp.global("modesty:canvas"))
create_bind({__modesty_id="kbLumaVoice", __modesty_label="Luma hold-to-talk", keys=vars.kbLumaVoice or "CTRL + grave"},
    hl.dsp.global("modesty:voice"))

-- Misc
create_bind({__modesty_id="kbSession", __modesty_label="Session", keys=vars.kbSession}, hl.dsp.global("caelestia:session"))
create_bind({__modesty_id="kbShowSidebar", __modesty_label="Show Sidebar", keys=vars.kbShowSidebar}, hl.dsp.global("caelestia:sidebar"))
create_bind({__modesty_id="kbClearNotifs", __modesty_label="Clear Notifs", keys=vars.kbClearNotifs}, hl.dsp.global("caelestia:clearNotifs"), locked)
create_bind({__modesty_id="kbShowPanels", __modesty_label="Show Panels", keys=vars.kbShowPanels}, hl.dsp.global("caelestia:showall"))
create_bind({__modesty_id="kbLock", __modesty_label="Lock", keys=vars.kbLock}, hl.dsp.global("caelestia:lock"))

-- Restore lock
create_bind({__modesty_id="kbRestoreLock", __modesty_label="Restore Lock", keys=vars.kbRestoreLock}, function()
    hl.dispatch(hl.dsp.exec_cmd("python3 @MODESTY_ROOT@/scripts/session-control.py restore-lock"))
end)

-- Kill/restart
create_bind({__modesty_id="key_d2becf34d5", __modesty_label="CTRL + SUPER + SHIFT + R", keys="CTRL + SUPER + SHIFT + R"}, hl.dsp.exec_cmd("python3 @MODESTY_ROOT@/scripts/session-control.py stop"), release)
create_bind({__modesty_id="key_317f792794", __modesty_label="CTRL + SUPER + ALT + R", keys="CTRL + SUPER + ALT + R"},
    hl.dsp.exec_cmd("python3 @MODESTY_ROOT@/scripts/session-control.py restart"),
    release
)

for i = 1, 10 do
    local key = i % 10 -- 10 maps to key 0
    create_bind({__modesty_id="kbGoToWs", __modesty_label="Go To Ws", keys=extend_keybind(vars.kbGoToWs, key)}, fn.wsaction("focus", "", i))
    create_bind({__modesty_id="kbMoveWinToWs", __modesty_label="Move Win To Ws", keys=extend_keybind(vars.kbMoveWinToWs, key)}, fn.wsaction("move", "", i))
    create_bind({__modesty_id="kbGoToWsGroup", __modesty_label="Go To Ws Group", keys=extend_keybind(vars.kbGoToWsGroup, key)}, fn.wsaction("focus", "group", i))
    create_bind({__modesty_id="kbMoveWinToWsGroup", __modesty_label="Move Win To Ws Group", keys=extend_keybind(vars.kbMoveWinToWsGroup, key)}, fn.wsaction("move", "group", i))
end

-- Go to workspace -1/+1
create_bind({__modesty_id="kbPrevWs", __modesty_label="Prev Ws", keys=vars.kbPrevWs}, hl.dsp.focus({ workspace = "-1" }), repeating_unless_mouse)
create_bind({__modesty_id="kbNextWs", __modesty_label="Next Ws", keys=vars.kbNextWs}, hl.dsp.focus({ workspace = "+1" }), repeating_unless_mouse)

-- Go to workspace group -1/+1
create_bind({__modesty_id="kbPrevWsGroup", __modesty_label="Prev Ws Group", keys=vars.kbPrevWsGroup}, hl.dsp.focus({ workspace = "-10" }), repeating_unless_mouse)
create_bind({__modesty_id="kbNextWsGroup", __modesty_label="Next Ws Group", keys=vars.kbNextWsGroup}, hl.dsp.focus({ workspace = "+10" }), repeating_unless_mouse)

-- Move window to workspace -1/+1
create_bind({__modesty_id="kbMoveWinToWsNext", __modesty_label="Move Win To Ws Next", keys=vars.kbMoveWinToWsNext}, hl.dsp.window.move({ workspace = "+1" }), repeating_unless_mouse)
create_bind({__modesty_id="kbMoveWinToWsPrev", __modesty_label="Move Win To Ws Prev", keys=vars.kbMoveWinToWsPrev}, hl.dsp.window.move({ workspace = "-1" }), repeating_unless_mouse)

-- Move window to/from special workspace
create_bind({__modesty_id="kbMoveWinToWsSpecial", __modesty_label="Move Win To Ws Special", keys=vars.kbMoveWinToWsSpecial}, hl.dsp.window.move({ workspace = "special:special" }))
create_bind({__modesty_id="kbMoveWinFromWsSpecial", __modesty_label="Move Win From Ws Special", keys=vars.kbMoveWinFromWsSpecial}, hl.dsp.window.move({ workspace = "e+0" }))

-- Window groups
create_bind({__modesty_id="kbWindowCycleNext", __modesty_label="Window Cycle Next", keys=vars.kbWindowCycleNext}, hl.dsp.window.cycle_next(), repeating)
create_bind({__modesty_id="kbWindowCyclePrev", __modesty_label="Window Cycle Prev", keys=vars.kbWindowCyclePrev}, hl.dsp.window.cycle_next({ next = false }), repeating)
create_bind({__modesty_id="kbWindowGroupCycleNext", __modesty_label="Window Group Cycle Next", keys=vars.kbWindowGroupCycleNext}, hl.dsp.group.next(), repeating)
create_bind({__modesty_id="kbWindowGroupCyclePrev", __modesty_label="Window Group Cycle Prev", keys=vars.kbWindowGroupCyclePrev}, hl.dsp.group.prev(), repeating)
create_bind({__modesty_id="kbToggleGroup", __modesty_label="Toggle Group", keys=vars.kbToggleGroup}, hl.dsp.group.toggle())
create_bind({__modesty_id="kbUngroup", __modesty_label="Ungroup", keys=vars.kbUngroup}, hl.dsp.window.move({ out_of_group = true }))
create_bind({__modesty_id="kbGroupLockActive", __modesty_label="Group Lock Active", keys=vars.kbGroupLockActive}, hl.dsp.group.lock_active())

-- Window actions
for _, dir in ipairs({ "left", "right", "up", "down" }) do
    create_bind({__modesty_id="key_150febb36c", __modesty_label="SUPER +  dir", keys="SUPER + " .. dir}, hl.dsp.focus({ direction = dir }))
    create_bind({__modesty_id="key_62ed6a45c3", __modesty_label="SUPER + SHIFT +  dir", keys="SUPER + SHIFT + " .. dir}, hl.dsp.window.move({ direction = dir }))
end

create_bind({__modesty_id="kbWindowDecreaseWidth", __modesty_label="Window Decrease Width", keys=vars.kbWindowDecreaseWidth}, fn.resize_active_window(-10, 0), repeating)
create_bind({__modesty_id="kbWindowIncreaseWidth", __modesty_label="Window Increase Width", keys=vars.kbWindowIncreaseWidth}, fn.resize_active_window(10, 0), repeating)
create_bind({__modesty_id="kbWindowDecreaseHeight", __modesty_label="Window Decrease Height", keys=vars.kbWindowDecreaseHeight}, fn.resize_active_window(0, -10), repeating)
create_bind({__modesty_id="kbWindowIncreaseHeight", __modesty_label="Window Increase Height", keys=vars.kbWindowIncreaseHeight}, fn.resize_active_window(0, 10), repeating)

create_bind({__modesty_id="kbMoveWindow", __modesty_label="Move Window", keys={ vars.kbMoveWindow, "SUPER + mouse:272" }}, hl.dsp.window.drag(), mouse)
create_bind({__modesty_id="kbResizeWindow", __modesty_label="Resize Window", keys={ vars.kbResizeWindow, "SUPER + mouse:273" }}, hl.dsp.window.resize(), mouse)
create_bind({__modesty_id="kbCenterWindow", __modesty_label="Center Window", keys=vars.kbCenterWindow}, hl.dsp.window.center())
create_bind({__modesty_id="kbNormalizeWindow", __modesty_label="Normalize Window", keys=vars.kbNormalizeWindow}, function()
    hl.dispatch(hl.dsp.window.resize(fn.resize_by_screen(55, 70)))
    hl.dispatch(hl.dsp.window.center())
end)
create_bind({__modesty_id="kbWindowPip", __modesty_label="Window Pip", keys=vars.kbWindowPip}, function()
    local a = hl.get_active_window()
    if a then
        local pip = fn.move_actions(a) or {}
        if not a.floating then table.insert(pip, 1, hl.dsp.window.float()) end
        table.insert(pip, hl.dsp.window.pin({ action = "on", window = "address:" .. a.address }))

        for _, x in ipairs(pip) do
            hl.dispatch(x)
        end
    end
end)
create_bind({__modesty_id="kbPinWindow", __modesty_label="Pin Window", keys=vars.kbPinWindow}, hl.dsp.window.pin())
create_bind({__modesty_id="kbWindowFullscreen", __modesty_label="Window Fullscreen", keys=vars.kbWindowFullscreen}, hl.dsp.window.fullscreen({ mode = "fullscreen" }))
create_bind({__modesty_id="kbWindowBorderedFullscreen", __modesty_label="Window Bordered Fullscreen", keys=vars.kbWindowBorderedFullscreen}, hl.dsp.window.fullscreen({ mode = "maximized" }))
create_bind({__modesty_id="kbToggleWindowFloating", __modesty_label="Toggle Window Floating", keys=vars.kbToggleWindowFloating}, hl.dsp.window.float())
create_bind({__modesty_id="kbCloseWindow", __modesty_label="Close Window", keys=vars.kbCloseWindow}, hl.dsp.window.close())

-- Special workspace toggles
create_bind({__modesty_id="kbSpecialWs", __modesty_label="Special Ws", keys=vars.kbSpecialWs}, fn.toggle("specialws"))
create_bind({__modesty_id="kbSystemMonitorWs", __modesty_label="System monitor", keys=vars.kbSystemMonitorWs}, fn.toggle("sysmon"))
create_bind({__modesty_id="kbMusicWs", __modesty_label="Spotify · Music workspace", keys=vars.kbMusicWs}, fn.toggle("music"))
create_bind({__modesty_id="kbCommunicationWs", __modesty_label="Discord · Chat workspace", keys=vars.kbCommunicationWs}, fn.toggle("communication"))
create_bind({__modesty_id="kbTodoWs", __modesty_label="Tasks workspace", keys=vars.kbTodoWs}, fn.toggle("todo"))

-- Apps
create_bind({__modesty_id="kbTerminal", __modesty_label="Terminal · Foot", keys=vars.kbTerminal}, hl.dsp.exec_cmd(vars.terminal))
create_bind({__modesty_id="kbBrowser", __modesty_label="Browser · Zen", keys=vars.kbBrowser}, hl.dsp.exec_cmd(vars.browser))
create_bind({__modesty_id="kbEditor", __modesty_label="Editor · Obsidian", keys=vars.kbEditor}, hl.dsp.exec_cmd(vars.editor))
create_bind({__modesty_id="kbFileExplorer", __modesty_label="Files · Thunar", keys=vars.kbFileExplorer}, hl.dsp.exec_cmd(vars.fileExplorer))
create_bind({__modesty_id="kbAudioSettings", __modesty_label="Audio Settings", keys=vars.kbAudioSettings}, hl.dsp.exec_cmd(vars.audioSettings))

-- Utilities
create_bind({__modesty_id="kbScreenshot", __modesty_label="Screenshot", keys=vars.kbScreenshot}, hl.dsp.exec_cmd("python3 @MODESTY_ROOT@/scripts/screenshot.py"), locked)
create_bind({__modesty_id="kbScreenshotFreeze", __modesty_label="Screenshot Freeze", keys=vars.kbScreenshotFreeze}, hl.dsp.exec_cmd("python3 @MODESTY_ROOT@/scripts/screenshot.py"))
create_bind({__modesty_id="kbScreenshotRegion", __modesty_label="Screenshot Region", keys=vars.kbScreenshotRegion}, hl.dsp.exec_cmd("python3 @MODESTY_ROOT@/scripts/screenshot.py"))
create_bind({__modesty_id="kbRecord", __modesty_label="Record", keys=vars.kbRecord}, hl.dsp.exec_cmd("python3 @MODESTY_ROOT@/scripts/recording.py toggle"))
create_bind({__modesty_id="kbRecordSound", __modesty_label="Record Sound", keys=vars.kbRecordSound}, hl.dsp.exec_cmd("python3 @MODESTY_ROOT@/scripts/recording.py toggle --sound"))
create_bind({__modesty_id="kbRecordRegion", __modesty_label="Record Region", keys=vars.kbRecordRegion}, hl.dsp.exec_cmd("python3 @MODESTY_ROOT@/scripts/recording.py toggle --region"))
create_bind({__modesty_id="kbColorPicker", __modesty_label="Color Picker", keys=vars.kbColorPicker}, hl.dsp.exec_cmd("hyprpicker -a"))

-- Brightness
create_bind({__modesty_id="key_a01726b8b1", __modesty_label="XF86MonBrightnessUp", keys="XF86MonBrightnessUp"}, hl.dsp.global("caelestia:brightnessUp"), locked)
create_bind({__modesty_id="key_c6387d15a4", __modesty_label="XF86MonBrightnessDown", keys="XF86MonBrightnessDown"}, hl.dsp.global("caelestia:brightnessDown"), locked)

-- Media
create_bind({__modesty_id="kbMediaToggle", __modesty_label="Media Toggle", keys={ vars.kbMediaToggle, "XF86AudioPlay", "XF86AudioPause" }}, hl.dsp.global("caelestia:mediaToggle"), locked)
create_bind({__modesty_id="kbMediaNext", __modesty_label="Media Next", keys={ vars.kbMediaNext, "XF86AudioNext" }}, hl.dsp.global("caelestia:mediaNext"), locked)
create_bind({__modesty_id="kbMediaPrev", __modesty_label="Media Prev", keys={ vars.kbMediaPrev, "XF86AudioPrev" }}, hl.dsp.global("caelestia:mediaPrev"), locked)
create_bind({__modesty_id="kbMediaStop", __modesty_label="Media Stop", keys={ vars.kbMediaStop, "XF86AudioStop" }}, hl.dsp.global("caelestia:mediaStop"), locked)

-- Volume
create_bind({__modesty_id="kbVolumeMute", __modesty_label="Volume Mute", keys={ vars.kbVolumeMute, "XF86AudioMute" }}, hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), locked)
create_bind({__modesty_id="key_34644c8d89", __modesty_label="XF86AudioMicMute", keys="XF86AudioMicMute"}, hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), locked)
create_bind({__modesty_id="key_ac4a353b3a", __modesty_label="XF86AudioRaiseVolume", keys="XF86AudioRaiseVolume"}, hl.dsp.global("caelestia:volumeUp"), locked)
create_bind({__modesty_id="key_d5d35018e4", __modesty_label="XF86AudioLowerVolume", keys="XF86AudioLowerVolume"}, hl.dsp.global("caelestia:volumeDown"), locked)

-- Sleep
create_bind({__modesty_id="kbSleep", __modesty_label="Sleep", keys=vars.kbSleep}, hl.dsp.exec_cmd(vars.sleepGestureCmd), locked)

-- Clipboard and emoji picker
create_bind({__modesty_id="kbClipboard", __modesty_label="Clipboard", keys=vars.kbClipboard}, hl.dsp.exec_cmd("pkill fuzzel || python3 @MODESTY_ROOT@/scripts/desktop-picker.py clipboard"))
create_bind({__modesty_id="kbClipboardDel", __modesty_label="Clipboard Del", keys=vars.kbClipboardDel}, hl.dsp.exec_cmd("pkill fuzzel || python3 @MODESTY_ROOT@/scripts/desktop-picker.py delete"))
create_bind({__modesty_id="kbEmoji", __modesty_label="Emoji", keys=vars.kbEmoji}, hl.dsp.exec_cmd("pkill fuzzel || python3 @MODESTY_ROOT@/scripts/desktop-picker.py emoji"))
create_bind({__modesty_id="kbClipboardPasteLatest", __modesty_label="Clipboard Paste Latest", keys=vars.kbClipboardPasteLatest},
    hl.dsp.exec_cmd('sleep 0.5s && cliphist list | head -1 | cliphist decode | wtype -'),
    locked
)

-- Testing
create_bind({__modesty_id="key_4288d74f3d", __modesty_label="SUPER + ALT + F12", keys="SUPER + ALT + F12"},
    hl.dsp.exec_cmd(
        "notify-send -u low -i dialog-information-symbolic 'Test notification' " ..
        [["Here's a really long message to test truncation and wrapping\nYou can middle click or flick this notification to dismiss it!"]] ..
        " -a 'Shell' -A 'Test1=I got it!' -A 'Test2=Another action'"
    )
)

-- Modesty settings
create_bind({__modesty_id="key_0eb7f75261", __modesty_label="SUPER + comma", keys="SUPER + comma"}, hl.dsp.exec_cmd("quickshell ipc -p @MODESTY_ROOT@/shell.qml call island toggle settings"))

modestyBindings:write()
