pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Services.SystemTray
import qs.theme
Singleton {
    id:root
    readonly property var items:SystemTray.items.values
    property var selected:null
    property var path:[]
    property bool inFooter:false
    property string title:""
    readonly property bool open:selected!==null
    property var hoverOwners: []
    readonly property bool pointerInside: hoverOwners.length > 0
    function show(item,footer=false): void {
        leave.stop();
        Hints.clear();
        if(selected===item)return;
        if(!item.hasMenu)return;
        cleanup.stop();
        // Keep the source icon stationary if its neighbouring panel is open.
        inFooter=footer;selected=item;title=item.tooltipTitle||item.title||item.id;path=[{handle:item.menu,title:root.title}];
    }
    function close(): void {leave.stop();selected=null;cleanup.restart();}
    function enter(owner): void {
        if (!hoverOwners.includes(owner)) hoverOwners = hoverOwners.concat([owner]);
        leave.stop();
    }
    function exit(owner): void {
        hoverOwners = hoverOwners.filter(value => value !== owner);
        if (!pointerInside) leave.restart();
    }
    function descend(entry): void {path=path.concat([{handle:entry,title:entry.text.replace(/&/g,"")}]);}
    function back(): void {if(path.length>1)path=path.slice(0,-1);else close();}
    function activate(entry): void {if(!entry.enabled)return;if(entry.hasChildren){descend(entry);return;}if(!Preferences.preview){entry.triggered();close();if(inFooter)IslandState.closeMenu();}}
    onItemsChanged:if(selected&&!items.includes(selected))close()
    Timer {id:leave;interval:380;onTriggered:if(!root.pointerInside)root.close()}
    // Retain the native menu model until its outgoing opacity animation ends.
    Timer {id:cleanup;interval:Tokens.animFast+32;onTriggered:if(!root.open)root.path=[]}
    Connections {target:IslandState;function onMenuOpenChanged(){root.close();}function onStateChanged(){if(root.inFooter&&IslandState.state!=="quicksettings")root.close();}}
}
