//@ pragma Env QT_QPA_PLATFORMTHEME=generic
//@ pragma Env MODESTY_PREVIEW=1
import QtQuick
import Quickshell
import "modules/island" as Island
import "modules/settings" as Settings
import qs.services
ShellRoot {
    FloatingWindow { visible:false; implicitWidth:1920;implicitHeight:1080;Island.IslandSurface {id:surface;availableWidth:1920} }
    LazyLoader {active:IslandState.settingsOpen;Settings.SettingsWindow {visible:false} }
    property int index:0
    property int attempts:0
    property bool checking:false
    property var names:["media","clock","quicksettings","wifi","bluetooth","display","sound","privacy","performance","focus","recorder","notifhistory","calendar","wallpapers","themes","launcher","dropcue","files","authentication","unlockcheck","power","settings"]
    Timer {interval:80;repeat:true;running:true;onTriggered:{
        if(index>=names.length){console.log("VALIDATION COMPLETE");Qt.quit();return;}
        if(!checking){IslandState.openMenu(names[index]);checking=true;attempts=0;return;}
        const entries=surface.diagnostics().stages.reduce((all,s)=>all.concat(s.entries),[]).filter(e=>e.selected);
        if(names[index]==="settings" || (entries.length===1 && entries[0].status===1)) {index++;checking=false;}
        else if(++attempts>35 || entries.some(e=>e.status===3)){console.error("VALIDATION FAILED: "+names[index]);Qt.quit();}
    }}
}
