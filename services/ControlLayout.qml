pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "Layout.js" as Grid
Singleton {
    id: root
    property int columns: 7
    property var items: Grid.defaults()
    property var history: []
    property string error: ""
    readonly property var shapes: Grid.shapes
    readonly property int rows: Math.max(1,...items.map(a=>a.y+a.h))
    readonly property real cell: (Preferences.controlsWidth-Preferences.innerPadding*2-(columns-1)*Preferences.controlGap)/columns
    readonly property bool footerShown:Preferences.footerVisible&&(Preferences.footerPerformance||Preferences.footerThemes||Preferences.footerWallpapers||Preferences.footerPower||Preferences.footerSettings||(Preferences.footerTray&&Tray.items.length>0))
    readonly property int panelHeight: Math.ceil(rows*(cell+Preferences.controlGap)-Preferences.controlGap+Preferences.innerPadding*2+(footerShown?48:0))
    function snapshot(): var { return {version:2,columns,items}; }
    function commit(next: var, count: int): bool {
        if(!Grid.validate(next,count)){error="The layout is full. Reduce a tile or remove a control.";return false;}
        history=history.slice(-29).concat([Grid.copy(snapshot())]);columns=count;items=next;error="";save();return true;
    }
    function save(): void { if(!Preferences.preview) delay.restart(); }
    function move(id: string,x: int,y: int,w: int,h: int): bool { const next=previewMove(items,id,x,y,w,h);if(!next){error="The layout is full. Reduce a tile or remove a control.";return false;}return commit(next,columns); }
    function previewMove(base: var,id: string,x: int,y: int,w: int,h: int): var {
        w=Math.max(1,Math.min(columns,w));h=Math.max(1,Math.min(6,h));
        x=Math.max(0,Math.min(columns-w,x));y=Math.max(0,Math.min(12-h,y));
        return Grid.place(base,{id,x,y,w,h},columns);
    }
    function remove(id: string): void { commit(items.filter(a=>a.id!==id),columns); }
    function add(id: string): void { if(items.some(a=>a.id===id)||!shapes[id])return;const s=shapes[id].find(a=>a[0]<=columns);const item=Grid.firstSpace(items,{id,w:s[0],h:s[1]},columns);if(item)commit(items.concat([item]),columns); }
    function tidy(count: int): void { const next=Grid.tidy(items,count);if(next)commit(next,count); }
    function reset(): void { commit(Grid.defaults(),7); }
    function undo(): void { if(!history.length)return;const old=history[history.length-1];history=history.slice(0,-1);columns=old.columns;items=old.items;error="";save(); }
    Timer { id: delay; interval: 350; onTriggered: {if(writer.running){restart();return;}writer.command=["python3",Qt.resolvedUrl("../scripts/control-layout.py").toString().replace("file://",""),JSON.stringify(root.snapshot())];writer.running=true;} }
    Process { id: writer; onExited: code=>{if(code!==0)root.error="Could not save the control layout";} }
    FileView { path: Preferences.preview?"":Preferences.stateDir+"/control-layout.json"; printErrors:false; onLoaded: {try{const d=JSON.parse(text());if(Grid.validate(d.items,d.columns)){root.columns=d.columns;root.items=d.items;if(!d.version){for(const id of ["appearance","awake"])if(!root.items.some(a=>a.id===id)){const next=Grid.firstSpace(root.items,{id,w:1,h:1},root.columns);if(next)root.items=root.items.concat([next]);}root.save();}}}catch(e){root.error="Saved layout could not be read";}} }
}
