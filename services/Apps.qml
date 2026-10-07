pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "vendor/fuzzysort.js" as Fuzzy
Singleton {
    id: root
    property var usage: ({})
    property string error: ""
    readonly property bool launching: launcher.running
    readonly property bool closing: closer.running
    signal launched()
    signal closed(string appId, bool succeeded, string status)
    readonly property var apps: DesktopEntries.applications.values.filter(a => !a.noDisplay).map(a => ({
        id:a.id, name:a.name, icon:a.icon||"application-x-executable", entry:a,
        nameSearch:Fuzzy.prepare(a.name),
        metadataSearch:Fuzzy.prepare([a.genericName,a.comment,...a.keywords,a.id].join(" "))
    }))
    function launch(app): void {
        if (Preferences.preview || launching || !app) return;
        error="";
        launcher.appId=app.id;
        launcher.command=["python3",Qt.resolvedUrl("../scripts/launch-app.py").toString().replace("file://",""),app.id,Preferences.terminal];
        launcher.running=true;
    }
    function close(app): bool {
        if(Preferences.preview||closing||!app)return false;
        error="";closer.appId=app.id;closer.result={};
        closer.command=["python3",Qt.resolvedUrl("../scripts/launch-app.py").toString().replace("file://",""),"--close",app.id];
        closer.running=true;return true;
    }
    function search(query: string): var {
        const text=query.trim();
        if(!text)return apps.slice().sort((a,b)=>(Preferences.rememberApps?(usage[b.id]||0)-(usage[a.id]||0):0)||a.name.localeCompare(b.name));
        if(!Preferences.fuzzyApps)return apps.filter(a=>(a.name+" "+a.entry.genericName+" "+a.entry.keywords.join(" ")).toLowerCase().includes(text.toLowerCase()));
        return Fuzzy.go(text,apps,{keys:["nameSearch","metadataSearch"],threshold:.15,
            scoreFn:r=>Math.max(r[0].score,r[1].score*.72)
        }).map(r=>r.obj);
    }
    Process {
        id:launcher
        property string appId:""
        stdout:StdioCollector {onStreamFinished:{try{const result=JSON.parse(text);if(!result.ok)root.error=result.error;}catch(e){root.error="Couldn't start this application";}}}
        onExited:code=>{
            if(code!==0){if(!root.error)root.error="Couldn't start this application";return;}
            if(Preferences.rememberApps){root.usage=Object.assign({},root.usage,{[appId]:(root.usage[appId]||0)+1});usageFile.setText(JSON.stringify(root.usage));}
            root.launched();
        }
    }
    FileView {id:usageFile;path:Preferences.preview?"":Preferences.stateDir+"/app-usage.json";printErrors:false;onLoaded:{try{root.usage=JSON.parse(text());}catch(e){root.usage={};}}}
    Process {
        id:closer;property string appId:"";property var result:({})
        stdout:StdioCollector {onStreamFinished:{try{closer.result=JSON.parse(text);if(!closer.result.ok)root.error=closer.result.error;}catch(e){root.error="Couldn't close this application";}}}
        onExited:code=>root.closed(appId,code===0&&result.ok===true,result.status||"failed")
    }
}
