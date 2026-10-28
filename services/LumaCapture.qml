pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id:root
    readonly property string backend:Qt.resolvedUrl("../scripts/luma-capture.py").toString().replace("file://", "")
    property var state:null
    property string operation:""
    property string error:""
    readonly property bool busy:operation!==""
    readonly property bool available:!Preferences.preview&&!Session.locked
    readonly property bool canToggle:available&&!busy&&state!==null&&(state.enabled||state.supported)
    readonly property string status: {
        if(Preferences.preview)return "Screen sharing privacy is unavailable in preview.";
        if(Session.locked)return "Unlock your session to change screen sharing privacy.";
        if(operation==="enable")return "Enabling privacy. Stop sharing until this finishes…";
        if(operation==="disable")return "Disabling privacy. Stop sharing until this finishes…";
        if(operation==="status")return "Checking saved setting and active protection…";
        if(state===null)return "Protection status is unknown. Refresh to check.";
        if(!state.supported)return state.enabled?"Saved on, but this session is unsupported. Protection is not verified. You can turn it off.":"Unavailable on this session. This experimental feature requires a supported desktop version.";
        if(state.enabled&&state.loaded)return "Active. Luma is hidden from supported screen sharing.";
        if(state.enabled)return "Saved on, but protection is inactive. Stop sharing, then turn it off and on again.";
        if(state.loaded)return "Saved off, but protection is still loaded. Stop sharing and check your session.";
        return "Off. Luma remains visible in screen sharing.";
    }
    function start(command:string):void {
        operation=command;
        worker.command=["python3",backend,command];
        worker.running=true;
    }
    function refresh():void {
        if(!available||busy)return;
        error="";
        start("status");
    }
    function setEnabled(enabled:bool):void {
        if(!canToggle||enabled===state.enabled||(enabled&&!state.supported))return;
        error="";
        start(enabled?"enable":"disable");
    }
    function finish(code:int,exitStatus:int):void {
        const command=operation;
        const detail=diagnostics.text.trim();
        const failed=code!==0||exitStatus!==0;
        if(command!=="status"){
            error=detail||(failed?"Could not "+command+" screen sharing privacy (exit "+code+").":"");
            operation="status";
            Qt.callLater(()=>root.start("status"));
            return;
        }
        let next=null;
        if(!failed){
            try {
                const data=JSON.parse(output.text);
                if(data!==null&&typeof data.enabled==="boolean"&&typeof data.loaded==="boolean"&&typeof data.supported==="boolean")
                    next={enabled:data.enabled,loaded:data.loaded,supported:data.supported};
            }catch(e){}
        }
        state=next;
        const message=failed?(detail||"Could not check protection status (exit "+code+")."):next===null?"Could not read protection status.":detail;
        if(message)error+=(error?"\n":"")+message;
        operation="";
    }
    Process {
        id:worker
        stdout:StdioCollector {id:output}
        stderr:StdioCollector {id:diagnostics}
        onExited:(code,exitStatus)=>root.finish(code,exitStatus)
    }
}
