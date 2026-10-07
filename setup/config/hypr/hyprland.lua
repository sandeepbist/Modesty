local home   = os.getenv("HOME")
local hypr   = home .. "/.config/hypr"
package.path = package.path .. ";" .. home .. "/.config/modesty/desktop/?.lua"

-- Create a file if it doesn't exist, optionally with initial content
local function maybe_create(file, content)
    local f = io.open(file)

    if f then
        f:close()
        return
    end

    f = io.open(file, "w")
    if f then
        if content then f:write(content) end
        f:close()
    end
end

-- Copy src to dst, but only if dst doesn't already exist
local function maybe_copy(src, dst)
    local out = io.open(dst)
    if out then
        out:close()
        return
    end

    local input = io.open(src, "r")
    if not input then return end

    out = io.open(dst, "w")
    if out then
        out:write(input:read("*a"))
        out:close()
    end
    input:close()
end

-- Maybe set current colours to defaults
maybe_copy(hypr .. "/scheme/default.lua", hypr .. "/scheme/current.lua")

-- User variables
maybe_create(home .. "/.config/modesty/desktop/hypr-vars.lua", "return {}\n")
local overrides = require("hypr-vars")
if type(overrides) == "table" then
    local vars = require("variables")
    for k, v in pairs(overrides) do
        vars[k] = v
    end
end

-- Default monitor conf
hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = 1,
})

-- Configs
require("hyprland.env")
require("hyprland.general")
require("hyprland.input")
require("hyprland.misc")
require("hyprland.animations")
require("hyprland.decoration")
require("hyprland.group")
require("hyprland.execs")
require("hyprland.rules")
require("hyprland.gestures")
require("hyprland.keybinds")

-- User configs
maybe_create(home .. "/.config/modesty/desktop/hypr-user.lua")
require("hypr-user")

-- ~/.config/hypr/hyprland.lua

-- Native scrolling works without the optional overview plugin.
hl.config({ general = { layout = "scrolling" } })
if hl.plugin and hl.plugin.scrolloverview then
    hl.config({ plugin = { scrolloverview = {
        scale = 0.5,
        workspace_gap = 80,
        gesture_distance = 200,
    } } })
end

-- 4. Overview Toggle Keybind
hl.bind("SUPER + tab", function()
    if hl.plugin and hl.plugin.scrolloverview then
        hl.plugin.scrolloverview.overview("toggle all")
    end
end)

-- 5. Keyboard Navigation Submap for Overview
hl.define_submap("scrolloverview", function()
    hl.bind("left", function()
        if hl.plugin and hl.plugin.scrolloverview then hl.plugin.scrolloverview.navigate("left") end
    end)
    hl.bind("right", function()
        if hl.plugin and hl.plugin.scrolloverview then hl.plugin.scrolloverview.navigate("right") end
    end)
    hl.bind("up", function()
        if hl.plugin and hl.plugin.scrolloverview then hl.plugin.scrolloverview.navigate("up") end
    end)
    hl.bind("down", function()
        if hl.plugin and hl.plugin.scrolloverview then hl.plugin.scrolloverview.navigate("down") end
    end)
    hl.bind("return", function()
        if hl.plugin and hl.plugin.scrolloverview then
            hl.plugin.scrolloverview.window("select")
            hl.plugin.scrolloverview.overview("off")
        end
    end)
    hl.bind("escape", function()
        if hl.plugin and hl.plugin.scrolloverview then hl.plugin.scrolloverview.overview("off") end
    end)
end)


--
--
--
--
--

if hl.plugin and hl.plugin.dynamic_cursors then
hl.config { plugin = { dynamic_cursors = {

    -- enables the plugin
    enabled = true,

    -- sets the cursor behaviour, supports these values:
    -- tilt    - tilt the cursor based on x-velocity
    -- rotate  - rotate the cursor based on movement direction
    -- stretch - stretch the cursor shape based on direction and velocity
    -- none    - do not change the cursor's behaviour
    mode = "stretch",

    -- minimum angle difference in degrees after which the shape is changed
    -- smaller values are smoother, but more expensive for hw cursors
    threshold = 2,

    -- for mode = "rotate"
    rotate = {

        -- length in px of the simulated stick used to rotate the cursor
        -- most realistic if this is your actual cursor size
        length = 20,

        -- clockwise offset applied to the angle in degrees
        -- this will apply to ALL shapes
        offset = 0.0,
    },

    -- for mode = "tilt"
    tilt = {

        -- controls how powerful the tilt is, the lower, the more power
        -- this value controls at which speed (px/s) the full tilt is reached
        limit = 5000,

        -- relationship between speed and tilt, supports these values:
        -- linear             - a linear function is used
        -- quadratic          - a quadratic function is used (most realistic to actual air drag)
        -- negative_quadratic - negative version of the quadratic one, feels more aggressive
        -- see `activation` in `src/mode/utils.cpp` for how exactly the calculation is done
        activation = "negative_quadratic",

        -- time window (ms) over which the speed is calculated
        -- higher values will make slow motions smoother but more delayed
        window = 100,

        -- full tilt for each side (°)
        full = 60,
    },

    -- for mode = "stretch"
    stretch = {

        -- controls how much the cursor is stretched
        -- this value controls at which speed (px/s) the full stretch is reached
        -- the full stretch being twice the original length
        limit = 3000,

        -- relationship between speed and stretch amount, supports these values:
        -- linear             - a linear function is used
        -- quadratic          - a quadratic function is used
        -- negative_quadratic - negative version of the quadratic one, feels more aggressive
        -- see `activation` in `src/mode/utils.cpp` for how exactly the calculation is done
        activation = "quadratic",

        -- time window (ms) over which the speed is calculated
        -- higher values will make slow motions smoother but more delayed
        window = 100,
    },

    -- configure shake to find
    -- magnifies the cursor if its is being shaken
    shake = {

        -- enables shake to find
        enabled = true,

        -- controls how soon a shake is detected
        -- lower values mean sooner
        threshold = 5.0,

        -- magnification level immediately after shake start
        base = 4.0,
        -- magnification increase per second when continuing to shake
        speed = 4.0,
        -- how much the speed is influenced by the current shake intensity
        influence = 0.0,

        -- maximal magnification the cursor can reach
        -- values below 1 disable the limit (e.g. 0)
        limit = 0.0,

        -- time in milliseconds the cursor will stay magnified after a shake has ended
        timeout = 1000,

        -- show cursor behaviour `tilt`, `rotate`, etc. while shaking
        effects = true,

        -- enable ipc events for shake
        -- see the `ipc` section below
        ipc = false,
    },

    -- use hyprcursor to get a higher resolution texture when the cursor is magnified
    -- see the `hyprcursor` section below
    hyprcursor = {

        -- use nearest-neighbour (pixelated) scaling when magnifying beyond texture size
        -- this will also have effect without hyprcursor support being enabled
        -- 0 - never use pixelated scaling
        -- 1 - use pixelated when no highres image
        -- 2 - always use pixelated scaling
        nearest = 1,

        -- enable dedicated hyprcursor support
        enabled = true,

        -- resolution in pixels to load the magnified shapes at
        -- be warned that loading a very high-resolution image will take a long time and might impact memory consumption
        -- -1 means we use [normal cursor size] * [shake:base option]
        resolution = -1,

        -- shape to use when clientside cursors are being magnified
        -- see the shape-name property of shape rules for possible names
        -- specifying clientside will use the actual shape, but will be pixelated
        fallback = "clientside",
    },
}}}
end
