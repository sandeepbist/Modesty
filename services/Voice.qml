pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id:root
    readonly property string backend:Qt.resolvedUrl("../scripts/luma-voice.py").toString().replace("file://", "")
    property string phase:"idle"
    readonly property bool active:["starting","listening","finishing"].includes(phase)
    property bool held:false
    property bool ready:false
    property bool workerStarted:false
    property bool refreshPending:false
    property bool available:true
    property string identity:""
    property int sequence:0
    property string transcript:""
    property string error:""
    property real level:0
    property real loadSeconds:0
    property int peakMiB:0
    property string runtime:""
    readonly property string installer:Qt.resolvedUrl("../install.py").toString().replace("file://", "")
    property bool installed:false
    readonly property bool installing:setup.running
    readonly property bool checking:installationStatus.running
    property string setupMessage:""
    function checkInstallation():void {if(!installationStatus.running)installationStatus.running=true;}
    function install():void {
        if(installing||active||Preferences.preview||Session.isLocked())return;
        setupMessage="Setup window opened. Follow download progress there.";
        error="";refreshPending=false;stopWorker();setup.running=true;
    }
    Process {
        id:installationStatus;command:["python3",root.backend,"--status"]
        stdout:StdioCollector {onStreamFinished:{try{root.installed=!!JSON.parse(text).installed;}catch(e){root.setupMessage="Couldn't check voice installation.";}}}
    }
    Process {
        id:setup;command:["foot","--title=Luma voice setup","python3",root.installer,"--install-voice"]
        onExited:code=>{
            root.setupMessage=code===0?"Setup finished. Hold Ctrl + backtick to speak.":code===130?"Setup cancelled. Voice settings unchanged.":"Setup interrupted or failed. Retry installation.";
            if(code===0){root.available=true;root.error="";Preferences.set("lumaVoice",true);if(Preferences.lumaVoiceWarm)root.prepare();}
            root.checkInstallation();
        }
    }
    readonly property string status:error||(!ready&&active?"Preparing voice…":phase==="starting"?"Opening microphone…":phase==="listening"?"Listening":phase==="finishing"?"Finishing…":"")
    signal started()
    signal submitted(string text)
    signal cancelled()
    IpcHandler {
        target:"voice"
        function status():string {return JSON.stringify({phase:root.phase,held:root.held,ready:root.ready,available:root.available,error:root.error,loadSeconds:root.loadSeconds,peakMiB:root.peakMiB,runtime:root.runtime});}
        function cancel():void {root.cancel();}
        function refresh():bool {
            if(root.active||Session.isLocked()||Preferences.preview||!Preferences.lumaVoice)return false;
            if(worker.running){root.refreshPending=true;root.stopWorker();}
            else root.prepare();
            return true;
        }
    }

    function stopWorker():void {
        if(!worker.running)return;
        worker.running=false;shutdown.restart();
    }
    function prepare():void {
        if(installing||Preferences.preview||!Preferences.lumaVoice||Session.isLocked())return;
        if(!worker.running){ready=false;available=true;worker.running=true;}
        idle.restart();
    }
    function begin():void {
        if(installing||held||active||!Preferences.lumaVoice||Preferences.preview||Session.isLocked()||Luma.busy||Recorder.selecting)return;
        CanvasState.show();if(!CanvasState.opened)return;
        error="";transcript="";level=0;held=true;identity=Date.now().toString(36)+"-"+(++sequence);phase="starting";
        started();prepare();
        if(workerStarted)send("start");
        timeout.interval=60000;timeout.restart();
    }
    function send(command:string):void {
        if(workerStarted&&worker.running&&identity)worker.write(JSON.stringify({command,id:identity})+"\n");
    }
    function release():void {
        held=false;
        if(!active||phase==="finishing")return;
        phase="finishing";send("stop");level=0;timeout.interval=ready?30000:120000;timeout.restart();
    }
    function cancel():void {
        if(!active)return;
        send("cancel");identity="";held=false;phase="idle";level=0;transcript="";error="";timeout.stop();idle.restart();cancelled();
    }
    function fail(message:string):void {
        if(active)send("cancel");
        identity="";held=false;phase="idle";level=0;error=message;timeout.stop();idle.restart();
    }
    function receive(data:var):void {
        if(data.event==="ready"){
            ready=true;available=true;loadSeconds=data.loadSeconds||0;peakMiB=data.peakMiB||0;runtime=data.runtime||"cpu";
            if(phase==="finishing"){timeout.interval=30000;timeout.restart();}
            return;
        }
        if(data.event==="unavailable"){available=false;ready=false;fail(data.text||"Voice unavailable");root.stopWorker();return;}
        if(!identity||data.id!==identity||!active)return;
        if(data.event==="listening"&&held)phase="listening";
        else if(data.event==="partial")transcript=(data.text||"").slice(0,6000);
        else if(data.event==="level"&&held)level=Math.max(0,Math.min(1,data.value||0));
        else if(data.event==="error")fail(data.text||"Voice failed. Request not submitted.");
        else if(data.event==="final"){
            const text=(data.text||"").trim().slice(0,6000);
            identity="";held=false;phase="idle";level=0;timeout.stop();idle.restart();
            if(text){transcript=text;submitted(text);}else error="No speech heard. Try again.";
        }
    }
    Process {
        id:worker;command:["python3",root.backend];stdinEnabled:true
        onStarted:{root.workerStarted=true;if(root.active){root.send("start");if(!root.held)root.send("stop");}}
        stdout:SplitParser {onRead:line=>{try{root.receive(JSON.parse(line));}catch(e){}}}
        onExited:{shutdown.stop();root.workerStarted=false;root.ready=false;if(root.active)root.fail("Voice stopped. Your request was not submitted.");if(root.refreshPending){root.refreshPending=false;root.prepare();}}
    }
    // Bound shutdown if a native inference call delays termination.
    Timer {id:shutdown;interval:3000;onTriggered:if(worker.running)worker.signal(9)}
    Timer {id:idle;interval:180000;onTriggered:{if(root.active||Preferences.lumaVoiceWarm){restart();return;}root.stopWorker();}}
    Timer {id:timeout;interval:60000;onTriggered:{root.fail(root.phase==="finishing"?"Voice took too long. Request not submitted.":"Voice reached its 60-second limit. Try a shorter request.");}}
    Connections {target:CanvasState;function onOpenedChanged(){if(!CanvasState.opened)root.cancel();}}
    Connections {target:Session;function onLockedChanged(){if(Session.isLocked()){root.cancel();if(!Preferences.lumaVoiceWarm)root.stopWorker();}else if(Preferences.lumaVoiceWarm)root.prepare();}}
    Connections {target:Preferences;function onLumaVoiceChanged(){if(!Preferences.lumaVoice){root.cancel();root.stopWorker();}else if(Preferences.lumaVoiceWarm)root.prepare();}function onLumaVoiceWarmChanged(){if(Preferences.lumaVoiceWarm)root.prepare();else idle.restart();}}
    Component.onCompleted:if(Preferences.lumaVoiceWarm)prepare()
}
