import QtQuick
import Quickshell
import Quickshell.Hyprland
import "LevelRepeat.js" as LevelRepeat

Scope {
    id: root

    readonly property string client: Quickshell.env("MODESTY_COMPAT") === "1" ? "caelestia" : "modesty"
    property var heldLevels: ({})
    property var releasedLevels: ({})
    function changeLevel(kind:string,direction:int,step:real):void {
        if(kind==="brightness")SystemInfo.setBrightness(SystemInfo.brightness+direction*step);
        else Audio.setVolume(direction>0?Math.min(1,Audio.volume+step):Audio.volume-step);
    }
    function beginLevel(kind:string,direction:int):void {
        if(heldLevels[kind]?.direction===direction)return;
        const now=Date.now(),held=LevelRepeat.begin(releasedLevels[kind],direction,now);
        heldLevels=Object.assign({},heldLevels,{[kind]:held});
        changeLevel(kind,direction,.01*LevelRepeat.multiplier(now-held.since));
    }
    function endLevel(kind:string,direction:int):void {
        if(heldLevels[kind]?.direction!==direction)return;
        releasedLevels=Object.assign({},releasedLevels,{[kind]:Object.assign({},heldLevels[kind],{ended:Date.now()})});
        const next=Object.assign({},heldLevels);delete next[kind];heldLevels=next;
    }
    Timer {
        interval:70;repeat:true;running:Object.keys(root.heldLevels).length>0
        onTriggered:{
            const now=Date.now();
            for(const kind of Object.keys(root.heldLevels)){
                const held=root.heldLevels[kind],elapsed=now-held.since;
                if(elapsed>=350)root.changeLevel(kind,held.direction,.01*LevelRepeat.multiplier(elapsed));
            }
        }
    }

    GlobalShortcut { appid: root.client; name: "settings"; description: "Modesty Settings"; onPressed: IslandState.toggle("settings") }
    GlobalShortcut { appid: "modesty"; name: "canvas"; description: "Quick Search"; onPressed: CanvasState.toggle() }
    GlobalShortcut { appid: "modesty"; name: "voice"; description: "Luma hold-to-talk"; onPressed: Voice.begin(); onReleased: Voice.release() }

    GlobalShortcut {
        appid: root.client
        name: "launcher"
        description: "Applications"
        onPressed: IslandState.toggle("launcher")
    }

    GlobalShortcut {
        appid: root.client
        name: "session"
        description: "Power menu"
        onPressed: IslandState.toggle("power")
    }

    GlobalShortcut {
        appid: root.client
        name: "sidebar"
        description: "Control center"
        onPressed: IslandState.toggle("quicksettings")
    }

    GlobalShortcut {
        appid: root.client
        name: "showall"
        description: "Control center"
        onPressed: IslandState.toggle("quicksettings")
    }

    GlobalShortcut {
        appid: root.client
        name: "clearNotifs"
        description: "Clear notifications"
        onPressed: Notifications.clearAll()
    }

    GlobalShortcut {
        appid: root.client
        name: "lock"
        description: "Lock session"
        onPressed: Session.lock(false)
    }

    GlobalShortcut {
        appid: root.client
        name: "brightnessUp"
        description: "Increase brightness"
        onPressed: root.beginLevel("brightness",1)
        onReleased: root.endLevel("brightness",1)
    }

    GlobalShortcut {
        appid: root.client
        name: "brightnessDown"
        description: "Decrease brightness"
        onPressed: root.beginLevel("brightness",-1)
        onReleased: root.endLevel("brightness",-1)
    }

    GlobalShortcut {appid:root.client;name:"volumeUp";description:"Increase volume";onPressed:root.beginLevel("volume",1);onReleased:root.endLevel("volume",1)}
    GlobalShortcut {appid:root.client;name:"volumeDown";description:"Decrease volume";onPressed:root.beginLevel("volume",-1);onReleased:root.endLevel("volume",-1)}

    GlobalShortcut {
        appid: root.client
        name: "mediaToggle"
        description: "Play or pause"
        onPressed: Media.togglePlaying()
    }

    GlobalShortcut {
        appid: root.client
        name: "mediaNext"
        description: "Next track"
        onPressed: Media.next()
    }

    GlobalShortcut {
        appid: root.client
        name: "mediaPrev"
        description: "Previous track"
        onPressed: Media.previous()
    }

    GlobalShortcut {
        appid: root.client
        name: "mediaStop"
        description: "Stop playback"
        onPressed: Media.stop()
    }

}
