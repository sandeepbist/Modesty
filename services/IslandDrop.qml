pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
    id: root
    property var dragOwner: null
    readonly property bool dragging: dragOwner !== null
    property var files: []
    property string error: ""
    property string status: ""
    property string lastOutput: ""
    property bool exportOpen: false
    property bool toolsOpen: false
    property bool renameOpen: false
    property var renamePlan: []
    property string operation: ""
    property string payload: ""
    property bool received: false
    property string question: ""
    property real contentHeight: 0
    readonly property bool busy: worker.running
    readonly property bool images: files.length > 0 && files.every(f => f.kind === "image")
    readonly property bool askable: files.length > 0 && files.every(f=>f.attachable)
    readonly property bool archive: files.length===1&&files[0].kind==="archive"
    readonly property bool pdfs: files.length>1&&files.every(f=>f.kind==="pdf")
    readonly property bool readable: files.length > 0 && files.every(f => f.readable)
    readonly property int panelHeight: Math.ceil(Math.min(600, Math.max(176, contentHeight)))
    function beginDrag(owner: var): void { if (owner && !busy && !Session.isLocked() && !Session.secure) dragOwner = owner; }
    function endDrag(owner: var): void { if (dragOwner === owner) dragOwner = null; }
    function run(name: string, args: var): bool {
        if (busy || Preferences.preview || Session.isLocked() || Session.secure) return false;
        error = ""; status = ""; operation = name; received = false;
        payload = JSON.stringify(Object.assign({operation: name, paths: files.map(f => f.path)}, args || {}));
        worker.running = true; return true;
    }
    function accept(urls: var): bool {
        if (busy || Preferences.preview || Session.isLocked() || Session.secure) return false;
        const paths = Array.from(urls, u => u.toString());
        files = []; lastOutput = ""; exportOpen = false; toolsOpen = false; renameOpen = false; renamePlan = []; question = "";
        CanvasState.close(); IslandState.openMenu("files"); dragOwner = null;
        return run("inspect", {paths});
    }
    function perform(paths:var,name:string,args:var):bool {
        if(!["compress","merge","export"].includes(name)||!Array.isArray(paths)||paths.length<1||paths.length>3)return false;
        if(busy||Preferences.preview||Session.isLocked()||Session.secure)return false;
        files=[];lastOutput="";exportOpen=false;toolsOpen=false;renameOpen=false;renamePlan=[];question="";
        CanvasState.close();IslandState.openMenu("files");
        return run(name,Object.assign({},args||{},{paths}));
    }
    function ask(query: string): void {
        query = query.trim();
        if (!query || busy || Luma.busy || !askable || Session.isLocked() || Session.secure) return;
        const previous = Luma.attachments, previousText = Luma.sharedText;
        Luma.attachments = files.map(f => f.path); Luma.sharedText = "";
        if (Luma.send(query, "local")) CanvasState.conversation();
        else { Luma.attachments = previous; Luma.sharedText = previousText; error = "Luma is not ready yet. Try again shortly."; }
    }
    Process {
        id: worker
        command: ["python3", Qt.resolvedUrl("../scripts/island-files.py").toString().replace("file://", "")]
        stdinEnabled: true
        onStarted: { write(root.payload + "\n"); root.payload = ""; }
        stdout: StdioCollector { onStreamFinished: {
            try {
                const data = JSON.parse(text); root.received = true;
                if (!data.ok) { root.error = data.error; return; }
                if (data.files) root.files = data.files;
                if (data.plan) root.renamePlan = data.plan;
                root.status = data.status || "";
                root.lastOutput = data.outputs?.[0] || root.lastOutput;
                if (data.outputs) {root.exportOpen = false;root.renameOpen=false;root.renamePlan=[];}
                if (root.status && IslandState.menu !== "files" && !Session.isLocked()) Context.show("file", root.status, "description", 0);
            } catch (e) { root.error = "Could not read the file response."; }
        }}
        onExited: if (!root.received && !root.error) root.error = "File processing stopped. Try again."
    }
    Connections { target: Session; function onLockedChanged() { if (Session.locked) root.dragOwner = null; } }
}
