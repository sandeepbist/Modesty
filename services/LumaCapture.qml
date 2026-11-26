pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

Singleton {
    id:root
    readonly property string backend:Qt.resolvedUrl("../scripts/luma-capture.py").toString().replace("file://", "")
    property var state:null
    property string operation:""
    property string error:""
    readonly property bool privateReady:available&&state!==null&&state.enabled&&state.loaded&&state.supported&&state.inputProtocol===1
    property string inputDestination:"closed"
    property double generation:0
    property double revision:0
    property string monitorName:""
    property var pendingInput:null
    property var currentInput:null
    property bool wantsInput:false
    property int startupChecks:0
    property var pasteTarget:null
    property var pasteSelection:null
    signal privateEnded(string reason)
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
        if(state.enabled&&state.loaded&&state.inputProtocol!==1)return "Saved on, but private interaction is unavailable. Stop sharing, then turn this setting off and on to upgrade.";
        if(state.enabled&&state.loaded)return "Active. Luma is hidden from supported screen sharing. Click Luma to type, click elsewhere to return typing, and press Escape to close.";
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
        CanvasState.close("mode-change");
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
                    next={enabled:data.enabled,loaded:data.loaded,supported:data.supported,inputProtocol:data.inputProtocol===1?1:0};
            }catch(e){}
        }
        state=next;
        const message=failed?(detail||"Could not check protection status (exit "+code+")."):next===null?"Could not read protection status.":detail;
        if(message)error+=(error?"\n":"")+message;
        operation="";
        if(next===null&&CanvasState.pendingOpen){SystemInfo.error=error;CanvasState.close("protection-loss");}
    }
    function openPrivate(identity,monitor=""):void {
        if(!privateReady){failPrivate("Private Luma is unavailable. "+status);return;}
        if(monitor)monitorName=monitor;
        if(identity!==generation)inputDestination="closed";
        generation=identity;revision=0;wantsInput=true;
        pendingInput={action:"open",generation:identity};pumpInput();
    }
    function closePrivate(reason:string):void {
        wantsInput=false;
        pasteWorker.running=false;pasteTarget=null;pasteSelection=null;
        pendingInput={action:"close",generation:generation};pumpInput();
    }
    function pumpInput():void {
        if(inputWorker.running||pendingInput===null)return;
        currentInput=pendingInput;pendingInput=null;
        inputWorker.command=["hyprctl","luma-private",currentInput.action,String(currentInput.generation),String(Quickshell.processId),monitorName];
        inputWorker.running=true;
    }
    function failPrivate(message:string):void {
        error=message;inputDestination="closed";wantsInput=false;
        SystemInfo.error=message;
        privateEnded("protection-loss");
        if(available&&!busy)start("status");
    }
    function acceptInput(data):void {
        if(data.protocol!==1||data.generation!==generation||data.revision<revision)return;
        revision=data.revision;inputDestination=data.destination;
        if(data.destination==="closed"&&wantsInput){
            wantsInput=false;
            if(!["escape","lock","shutdown","closed"].includes(data.reason)){
                error="Private interaction ended ("+(data.reason||"protection-loss")+").";SystemInfo.error=error;
            }
            privateEnded(data.reason||"protection-loss");
        }
    }
    function clipboardKey(editor,event):bool {
        if(!CanvasState.privateSession||!(event.modifiers&Qt.ControlModifier))return false;
        if(event.key===Qt.Key_C||event.key===Qt.Key_X){
            if(editor.selectedText)Quickshell.clipboardText=editor.selectedText;
            if(event.key===Qt.Key_X&&!editor.readOnly)editor.remove(editor.selectionStart,editor.selectionEnd);
        }else if(event.key===Qt.Key_V&&!editor.readOnly){
            if(pasteWorker.running){error="A clipboard transfer is already in progress.";event.accepted=true;return true;}
            pasteTarget=editor;pasteSelection={generation:generation,text:editor.text,start:editor.selectionStart,end:editor.selectionEnd,cursor:editor.cursorPosition};
            pasteWorker.running=true;
        }else return false;
        event.accepted=true;return true;
    }
    Process {
        id:pasteWorker
        command:["wl-paste","--type","text","--no-newline"]
        stdout:StdioCollector {id:pasteOutput}
        stderr:StdioCollector {id:pasteErrors}
        onExited:(code,exitStatus)=>{
            const editor=root.pasteTarget;const selection=root.pasteSelection;
            root.pasteTarget=null;root.pasteSelection=null;
            if(!editor||!selection||selection.generation!==root.generation||!CanvasState.privateSession)return;
            if(code!==0||exitStatus!==0){root.error=pasteErrors.text.trim()||"Could not read clipboard text.";return;}
            if(editor.text!==selection.text||editor.cursorPosition!==selection.cursor||editor.selectionStart!==selection.start||editor.selectionEnd!==selection.end){root.error="Clipboard paste cancelled because the selection changed.";return;}
            editor.remove(selection.start,selection.end);
            editor.insert(editor.cursorPosition,pasteOutput.text);
        }
    }
    Timer {interval:3000;running:pasteWorker.running;onTriggered:{pasteWorker.running=false;root.pasteTarget=null;root.pasteSelection=null;root.error="Clipboard transfer timed out.";}}
    Connections {target:Hyprland;function onRawEvent(event){
        if(event.name==="luma_private"){
            try{root.acceptInput(JSON.parse(event.data));}catch(e){root.failPrivate("Could not read private input event.");}
        }
    }}
    Connections {target:Session;function onLockedChanged(){if(!Session.locked)root.refresh();}}
    Timer {interval:500;repeat:true;running:root.available&&!root.busy&&root.state!==null&&root.state.enabled&&root.state.supported&&!root.state.loaded&&root.startupChecks<12;
        onTriggered:{root.startupChecks++;root.start("status");}
    }
    Timer {interval:750;repeat:true;running:root.wantsInput;onTriggered:{
        if(!inputWorker.running&&root.pendingInput===null){root.pendingInput={action:"status",generation:root.generation};root.pumpInput();}
    }}
    Process {
        id:inputWorker
        stdout:StdioCollector {id:inputOutput}
        stderr:StdioCollector {id:inputErrors}
        onExited:(code,exitStatus)=>{
            const request=root.currentInput;
            if(request.generation===root.generation){
                try{
                    if(code!==0||exitStatus!==0)throw new Error(inputErrors.text||"Private input command failed.");
                    let data=JSON.parse(inputOutput.text);if(typeof data==="string")data=JSON.parse(data);
                    if(data.protocol!==1)throw new Error(data.error||"Private input protocol is unavailable.");
                    root.acceptInput(data);
                }catch(e){if(root.wantsInput)root.failPrivate(String(e));else if(request.action!=="status")root.error=String(e);}
            }
            Qt.callLater(root.pumpInput);
        }
    }
    Process {
        id:worker
        stdout:StdioCollector {id:output}
        stderr:StdioCollector {id:diagnostics}
        onExited:(code,exitStatus)=>root.finish(code,exitStatus)
    }
}
