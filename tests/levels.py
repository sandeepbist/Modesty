#!/usr/bin/env python3
"""Check repeated volume/brightness events during opening, closing and interruption."""
from qml import run

run('''import QtQuick
import Quickshell
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    FloatingWindow {visible:true;implicitWidth:1000;implicitHeight:160;Island.IslandSurface{id:surface;availableWidth:1000}}
    property int phase:0
    property int ticks:0
    property double since:Date.now()
    property double deadline:Date.now()+14000
    property string kind:"volume"
    function next():void {phase++;ticks=0;since=Date.now();}
    function check(ok,label):void {if(!ok)throw new Error(label+" phase="+phase+" progress="+surface.levelProgress);}
    Timer {interval:35;running:true;repeat:true;onTriggered:{try {
        check(Date.now()<deadline,"Timed out");ticks++;
        if(phase===0&&ticks>10){Preferences.motion="gentle";Preferences.motionSpeed=1.2;Context.clear();next();}
        else if(phase===1&&ticks>12){Context.show(kind,kind,"volume_up",.2);next();}
        else if(phase===2){
            const value=.2+Math.min(ticks,16)*.02;Context.show(kind,kind,"volume_up",value);
            if(Date.now()-since>Tokens.morphDuration+130){
                check(surface.levelProgress===1,"Repeated updates delayed reveal");
                check(Math.abs(surface.clockStage.width-surface.clockStage.targetWidth)<.1,"Repeated updates delayed aperture");
                check(surface.levelStatus.kind===kind&&Math.abs(surface.levelStatus.value-value)<.001,"Stale level feedback");
                check(surface.clockStage.height===Preferences.barHeight,"Level event changed resting height");
                if(ticks>24){Context.clear();next();}
            }
        } else if(phase===3&&ticks===2){kind=kind==="volume"?"brightness":"volume";Context.show(kind,kind,"light_mode",.65);next();}
        else if(phase===4){
            Context.show(kind,kind,"light_mode",.65);
            if(Date.now()-since>Tokens.morphDuration+140){check(surface.levelProgress===1,"Interrupted close did not recover");check(surface.levelStatus.kind===kind,"Wrong level kind");Preferences.motion="instant";Context.clear();next();}
        } else if(phase===5){Context.show("volume","Volume","volume_up",1);next();}
        else if(phase===6){check(surface.levelProgress===1,"Reduced motion did not settle");Context.clear();next();}
        else if(phase===7){check(surface.levelProgress===0,"Reduced-motion close did not settle");console.log("LEVEL CHECK PASS: repeated updates, live values, interrupted close and reduced motion");Qt.quit();}
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''', 'LEVEL CHECK PASS: repeated updates, live values, interrupted close and reduced motion')
