pragma Singleton
import QtQuick
import Quickshell

Singleton {
    id: root
    property bool opened: false
    property bool privateSession:false
    property bool pendingOpen:false
    property bool pendingConversation:false
    property double identity:0
    signal conversationRequested()
    signal typingRequested()
    function conversation():void {pendingConversation=true;show();if(opened){pendingConversation=false;conversationRequested();}}
    function show(): void {
        if (Session.isLocked() || Recorder.selecting) return;
        if(!Preferences.preview){
            if(LumaCapture.busy){pendingOpen=true;return;}
            if(LumaCapture.state===null){pendingOpen=true;LumaCapture.refresh();return;}
            if(LumaCapture.state.enabled&&!LumaCapture.privateReady){
                pendingOpen=LumaCapture.state.supported&&!LumaCapture.state.loaded&&LumaCapture.startupChecks<12;
                SystemInfo.error=LumaCapture.error||LumaCapture.status;return;
            }
        }
        if(opened){if(privateSession){LumaCapture.openPrivate(identity);typingRequested();}return;}
        IslandState.closeMenu();
        Tray.close();
        privateSession=!Preferences.preview&&LumaCapture.privateReady;
        identity=Math.max(Date.now(),identity+1);
        pendingOpen=false;
        opened = true;
    }
    function close(reason="incidental"): void {
        const safety=["escape","lock","shutdown","protection-loss","mode-change","target-gone","monitor-gone","focus-replaced"].includes(reason);
        if(privateSession&&!safety)return;
        pendingOpen=false;pendingConversation=false;
        if(privateSession)LumaCapture.closePrivate(reason);
        opened=false;privateSession=false;
    }
    function toggle(): void { if (opened&&!privateSession) close(); else show(); }
    function settle():void {
        if(LumaCapture.busy)return;
        if(opened&&!privateSession&&LumaCapture.state?.enabled)close("mode-change");
        if(pendingOpen&&LumaCapture.state!==null){const conversation=pendingConversation;show();if(opened&&conversation){pendingConversation=false;conversationRequested();}}
    }
    Connections {target:LumaCapture;
        function onStateChanged(){
            if(root.opened&&root.privateSession&&!LumaCapture.privateReady)root.close("protection-loss");
            root.settle();
        }
        function onBusyChanged(){root.settle();}
        function onPrivateEnded(reason){root.close(reason==="escape"?"escape":"protection-loss");}
    }
    Connections {target:Session;function onLockedChanged(){if(Session.locked)root.close("lock")}}
    Connections {target:IslandState;function onMenuChanged(){if(IslandState.menuOpen)root.close()}function onSettingsOpenChanged(){if(IslandState.settingsOpen)root.close()}}
}
