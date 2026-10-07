pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Singleton {
    id:root
    property string phase:"idle"
    property string kind:"focus"
    property int duration:1500
    property int remaining:1500
    property double deadline:0
    property bool loaded:Preferences.preview
    property string error:""
    property bool quietOwned: false
    property bool previousDnd: false
    property bool settingDnd: false
    property bool quietOverridden: false
    function syncQuiet(): void {
        const wanted = loaded && !Preferences.preview && Preferences.focusQuiet
            && kind === "focus" && ["running", "paused"].includes(phase) && !quietOverridden;
        if (wanted && !quietOwned) {
            previousDnd = Notifications.dnd;
            quietOwned = true;
            settingDnd = true;
            Notifications.dnd = true;
            settingDnd = false;
            save();
        } else if (!wanted && quietOwned) {
            quietOwned = false;
            settingDnd = true;
            Notifications.dnd = previousDnd;
            settingDnd = false;
            save();
        }
    }
    onPhaseChanged: syncQuiet()
    onLoadedChanged: syncQuiet()
    Connections {
        target: Notifications
        function onDndChanged() {
            // A manual change takes precedence for the rest of this session.
            if (root.quietOwned && !root.settingDnd) {
                root.quietOwned = false;
                root.quietOverridden = true;
            }
            if (root.loaded && root.active && !root.settingDnd) root.save();
        }
    }
    Connections { target: Preferences; function onFocusQuietChanged() { root.syncQuiet(); } }
    readonly property bool active:phase!=="idle"
    readonly property string label:kind==="break"?"Break":"Focus"
    readonly property string timeText:String(Math.floor(remaining/60)).padStart(duration>=6000?3:2,"0")+":"+String(remaining%60).padStart(2,"0")
    readonly property real progress:duration>0?Math.max(0,Math.min(1,1-remaining/duration)):0
    readonly property string script:Qt.resolvedUrl("../scripts/focus-state.py").toString().replace("file://","")
    function snapshot():var {return {phase,kind,duration,remaining,deadline,quietOwned,previousDnd,quietOverridden,quietDnd:Notifications.dnd};}
    function save():void {if(loaded&&!Preferences.preview)saveDelay.restart();}
    function start(minutes:int,isBreak:bool):void {
        if(!loaded||Preferences.preview||Session.isLocked())return;
        // Release any previous session before capturing the user's current state.
        phase="idle";syncQuiet();quietOverridden=false;
        kind=isBreak?"break":"focus";duration=Math.max(60,Math.min(7200,minutes*60));remaining=duration;deadline=Date.now()+duration*1000;phase="running";save();IslandState.closeMenu();
    }
    function update():void {
        if(phase!=="running")return;
        remaining=Math.max(0,Math.min(duration,Math.ceil((deadline-Date.now())/1000)));
        if(remaining===0){phase="finished";deadline=0;save();Context.show("notice",kind==="break"?"Break complete":"Focus complete","timer",0);}
    }
    function pause():void {
        if(!loaded||Preferences.preview||Session.isLocked())return;
        if(phase==="running"){update();if(phase==="finished")return;phase="paused";deadline=0;}
        else if(phase==="paused"){deadline=Date.now()+remaining*1000;phase="running";}
        else return;
        save();
    }
    function cancel():void {if(!loaded||Preferences.preview||Session.isLocked())return;phase="idle";deadline=0;remaining=duration;save();}
    Timer {interval:1000;running:root.loaded&&root.phase==="running";repeat:true;onTriggered:root.update()}
    Timer {id:saveDelay;interval:80;onTriggered:{if(writer.running){restart();return;}writer.command=["python3",root.script,JSON.stringify(root.snapshot())];writer.running=true;}}
    Process {id:writer;onExited:code=>root.error=code===0?"":"Could not save the timer"}
    Process {
        running:!Preferences.preview;command:["python3",root.script]
        stdout:StdioCollector {onStreamFinished:{
            try {
                const d=JSON.parse(text);
                if(["idle","running","paused","finished"].includes(d.phase)&&["focus","break"].includes(d.kind)&&Number.isFinite(d.duration)&&d.duration>=60&&d.duration<=7200&&Number.isFinite(d.remaining)&&d.remaining>=0&&d.remaining<=d.duration&&Number.isFinite(d.deadline)&&d.deadline>=0&&d.deadline<=1e13){
                    root.duration=d.duration;root.remaining=d.remaining;root.deadline=d.deadline;root.kind=d.kind;root.phase=d.phase;
                    if (d.kind === "focus" && ["running", "paused"].includes(d.phase)
                        && [d.quietOwned,d.previousDnd,d.quietOverridden,d.quietDnd].every(v=>typeof v==="boolean")) {
                        root.settingDnd=true;
                        Notifications.dnd=d.quietDnd;
                        root.previousDnd=d.previousDnd;
                        root.quietOverridden=d.quietOverridden;
                        root.quietOwned=d.quietOwned;
                        root.settingDnd=false;
                    }
                }
            }catch(e){root.error="Could not restore the timer";}
            root.loaded=true;root.update();
        }}
    }
}
