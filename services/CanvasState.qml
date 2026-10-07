pragma Singleton
import QtQuick
import Quickshell

Singleton {
    id: root
    property bool opened: false
    signal conversationRequested()
    function conversation():void {show();if(opened)conversationRequested();}
    function show(): void {
        if (Session.isLocked() || Recorder.selecting) return;
        IslandState.closeMenu();
        Tray.close();
        opened = true;
    }
    function close(): void { opened = false; }
    function toggle(): void { if (opened) close(); else show(); }
    Connections {target:Session;function onLockedChanged(){if(Session.locked)root.close()}}
    Connections {target:IslandState;function onMenuChanged(){if(IslandState.menuOpen)root.close()}function onSettingsOpenChanged(){if(IslandState.settingsOpen)root.close()}}
}
