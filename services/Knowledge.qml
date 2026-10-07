pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root
    property var stats: ({documents:0, passages:0, updated:0})
    property string error: ""
    property string payload: ""
    readonly property bool busy: worker.running
    function rebuild():void {
        if (busy || Preferences.preview || Session.isLocked()) return;
        payload=JSON.stringify({roots:Preferences.lumaKnowledgeRoots});error="";
        worker.command=["python3",Qt.resolvedUrl("../scripts/luma-knowledge.py").toString().replace("file://",""),"build"];
        worker.running=true;
    }
    function refresh():void {
        if(busy||Preferences.preview)return;
        worker.command=["python3",Qt.resolvedUrl("../scripts/luma-knowledge.py").toString().replace("file://",""),"status"];
        worker.running=true;
    }
    Process {
        id:worker;stdinEnabled:true
        onStarted:if(command[2]==="build"){write(root.payload+"\n");root.payload="";}
        stdout:StdioCollector {onStreamFinished:{
            try{const data=JSON.parse(text);if(data.ok){root.stats=data;root.error=data.limited?"Index limit reached. Choose fewer folders.":data.skipped?data.skipped+" documents could not be read.":"";}else root.error=data.error||"Could not refresh index.";}
            catch(e){root.error="Could not read index status.";}
        }}
    }
}
