pragma Singleton
import QtQuick
import Quickshell
Singleton {
    id:root
    property bool active:false
    property string error:""
    property real until:0
    property real now:Date.now()
    readonly property int remaining:until?Math.max(0,Math.ceil((until-now)/60000)):0
    function setActive(value:bool):void {until=0;error="";active=value;}
    function setFor(seconds:real):bool {
        if(!Number.isFinite(seconds)||seconds<1||seconds>86400)return false;
        error="";now=Date.now();until=now+seconds*1000;active=true;return true;
    }
    function toggle(): void {setActive(!active);}
    onActiveChanged:if(!active)until=0
    Timer {interval:1000;repeat:true;running:root.active&&root.until>0;onTriggered:{root.now=Date.now();if(root.now>=root.until)root.setActive(false);}}
    Connections {target:Session;function onSecureChanged(){if(Session.secure)root.active=false;}}
}
