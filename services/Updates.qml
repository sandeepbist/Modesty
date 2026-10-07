pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id:root
    readonly property string backend:Qt.resolvedUrl("../scripts/updates.py").toString().replace("file://", "")
    property var state:({phase:"idle",message:"Check for updates when you are ready."})
    readonly property bool busy:worker.running||["launching","checking","downloading","preparing","applying"].includes(state.phase)
    function receive(text:string):void {try{state=JSON.parse(text);}catch(e){state={phase:"failed",message:"Could not read update status.",error:text.slice(-600)};}}
    function refresh():void {if(!Preferences.preview&&!reader.running)reader.running=true;}
    function run(action:string):void {
        if(busy||Preferences.preview||Session.isLocked())return;
        const args=["python3",backend];
        if(["apply","rollback","reload"].includes(action))args.push("launch",action);
        else args.push(action);
        if(["download","apply"].includes(action))args.push(state.target||"");
        worker.command=args;worker.running=true;
    }
    IpcHandler {
        target:"updates"
        function status():string {return JSON.stringify(root.state);}
        function check():void {root.run("check");}
    }
    Process {
        id:worker
        stdout:SplitParser {onRead:line=>root.receive(line)}
        stderr:StdioCollector {onStreamFinished:{if(text&&!root.busy)root.state=Object.assign({},root.state,{phase:"failed",error:text.slice(-1200)});}}
        onExited:code=>{if(code!==0)root.state=Object.assign({},root.state,{phase:"failed",message:"Update operation stopped."});root.refresh();}
    }
    Process {id:reader;command:["python3",root.backend,"status"];stdout:StdioCollector {onStreamFinished:root.receive(text)}}
    Timer {interval:1000;repeat:true;running:!Preferences.preview&&root.busy;onTriggered:root.refresh()}
}
