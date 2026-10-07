return {
    volumeStep = 1,
    -- Apps
    browser = os.execute("command -v zen-browser >/dev/null 2>&1") == true and "zen-browser" or "firefox",
    audioSettings = os.execute("command -v pwvucontrol >/dev/null 2>&1") == true and "pwvucontrol" or "pavucontrol",
    editor = "obsidian",
    terminal = "foot",
    fileExplorer = "thunar",

    -- Core App Shortcuts
    kbBrowser = "SUPER + W",
    kbEditor = "SUPER + O",
    kbTerminal = "SUPER + T",
    kbFileExplorer = "SUPER + E",

    -- Workspaces & Navigation
    kbNextWs = "CTRL + SUPER + Right",
    kbPrevWs = "CTRL + SUPER + Left",
    kbSpecialWs = "SUPER + S",

    -- Special Workspace Toggles
    kbSystemMonitorWs = "CTRL + SHIFT + Escape",
    kbMusicWs = "SUPER + M",
    kbCommunicationWs = "SUPER + D",
    kbTodoWs = "SUPER + R",

    -- Window Actions
    kbMoveWindow = "SUPER + Z",
    kbResizeWindow = "SUPER + X",
    kbWindowPip = "SUPER + ALT + Backslash",
    kbPinWindow = "SUPER + P",
    kbWindowFullscreen = "SUPER + F",
    kbWindowBorderedFullscreen = "SUPER + ALT + F",
    kbToggleWindowFloating = "SUPER + ALT + Space",
    kbCloseWindow = "SUPER + Q",

    -- Session & Controls
    kbSession = "CTRL + ALT + Delete",
    kbClearNotifs = "CTRL + ALT + C",
    kbShowPanels = "SUPER + K",
    kbLock = "SUPER + L",
    kbRestoreLock = "SUPER + ALT + L",
}
