-- Retain native action closures so editing a key never substitutes its behavior.
local json = require("utils.json")
local state = (os.getenv("XDG_STATE_HOME") or os.getenv("HOME") .. "/.local/state") .. "/modesty/"
local registry = { rows = {}, counts = {}, overrides = {} }
local file = io.open(state .. "desktop-bindings.json", "r")
if file then
    local ok, data = pcall(json.decode, file:read("*a")); file:close()
    if ok and type(data) == "table" then registry.overrides = data end
end
function registry:flags(entry, chord)
    local source = entry.flagsSource
    if type(source) == "function" then source = source(chord) end
    local flags = {}
    for k,v in pairs(source or {}) do flags[k] = v end
    flags.description = "Modesty desktop:" .. entry.id
    return flags
end
function registry:register(base, label, chord, action, flags)
    self.counts[base] = (self.counts[base] or 0) + 1
    local entry = {id = base .. ":" .. self.counts[base], label = label, original = chord, action = action, flagsSource = flags}
    entry.chord = self.overrides[entry.id] or chord
    if entry.chord ~= "" then
        local ok, handle = pcall(hl.bind, entry.chord, action, self:flags(entry, entry.chord))
        if ok then entry.handle = handle else
            entry.chord = chord
            entry.handle = hl.bind(chord, action, self:flags(entry, chord))
        end
    end
    self.rows[#self.rows+1] = entry
end
function registry:write()
    local rows = {}
    for _,entry in ipairs(self.rows) do
        local flags = self:flags(entry, entry.chord ~= "" and entry.chord or entry.original)
        rows[#rows+1] = {id=entry.id,label=entry.label,chord=entry.chord,original=entry.original,mouse=flags.mouse or false,release=flags.release or false}
    end
    local out = assert(io.open(state .. "desktop-bindings-live.json.tmp", "w"))
    out:write(json.encode(rows));out:close()
    assert(os.rename(state .. "desktop-bindings-live.json.tmp", state .. "desktop-bindings-live.json"))
end
function registry:set(id, chord)
    for _,entry in ipairs(self.rows) do
        if entry.id == id then
            if entry.chord == chord then return end
            local handle
            if chord ~= "" then handle = hl.bind(chord, entry.action, self:flags(entry, chord)) end
            if entry.handle then entry.handle:unbind() end
            entry.handle = handle; entry.chord = chord
            self:write();return
        end
    end
    error("Shortcut no longer exists. Refresh Settings.")
end
_modesty_desktop_bindings = registry
return registry
