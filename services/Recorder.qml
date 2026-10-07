pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Singleton {
    id:root
    property var status:({})
    readonly property string phase:status.phase||"idle"
    readonly property bool active:["preparing","selecting","countdown","recording","paused","saving"].includes(phase)
    readonly property bool recording:["recording","paused"].includes(phase)
    readonly property bool selecting:phase==="selecting"
    readonly property int elapsed:status.elapsed||0
    readonly property string timeText:Math.floor(elapsed/60)+":"+String(elapsed%60).padStart(2,"0")
    readonly property string label:phase==="countdown"?"Starting in "+status.remaining:phase==="paused"?"Paused · "+timeText:phase==="saving"?"Saving…":phase==="recording"?timeText:"Preparing…"
    readonly property string script:Qt.resolvedUrl("../scripts/recording.py").toString().replace("file://","")
    function start(region:bool,sound:bool):void {if(Preferences.preview||active||Session.isLocked())return;IslandState.closeMenu();const args=["python3",script,"start"];if(region)args.push("--region");if(sound)args.push("--sound");Quickshell.execDetached(args);}
    function stop():void {if(!Preferences.preview&&active)Quickshell.execDetached(["python3",script,"stop"]);}
    function pause():void {if(!Preferences.preview&&recording)Quickshell.execDetached(["python3",script,"pause"]);}
    function openFolder():void {if(!Preferences.preview)Quickshell.execDetached(["python3",script,"folder"]);}
    FileView {id:file;path:Preferences.preview?"":Preferences.stateDir+"/recording.json";watchChanges:true;printErrors:false;onFileChanged:reload();onLoaded:{try{const next=JSON.parse(text());if(root.active&&next.phase==="saved")Context.show("notice","Recording saved","check",0);if(root.active&&next.phase==="error")Context.show("notice","Recording failed","error",0);root.status=next;}catch(e){}}}
    Process {running:!Preferences.preview;command:["python3",root.script,"status"];stdout:StdioCollector {onStreamFinished:{try{root.status=JSON.parse(text);}catch(e){}}}}
}
