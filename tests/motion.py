#!/usr/bin/env python3
"""Exercise production spring geometry, retargeting and motion preferences."""
from qml import run

run('''import QtQuick
import Quickshell
import "modules/island" as Island
import qs.services
ShellRoot {
    FloatingWindow {
        visible:true;implicitWidth:700;implicitHeight:650
        Island.Stage {id:stage;stage:"clock";restingWidth:90;maximumWidth:550;targetWidth:90}
    }
    property var profiles:[{style:"fluid",speed:.65},{style:"fluid",speed:1.5},{style:"gentle",speed:.65},{style:"gentle",speed:1.5}]
    property int profile:0
    property int phase:0
    property double since:Date.now()
    property bool rebound:false
    function check(ok,label):void {if(!ok)throw new Error(label+" profile="+profile+" phase="+phase);}
    function next():void {phase++;since=Date.now();}
    function configure():void {
        Preferences.motion=profiles[profile].style;Preferences.motionSpeed=profiles[profile].speed;
        stage.panel="launcher";stage.targetWidth=460;stage.targetHeight=320;rebound=false;next();
    }
    Timer {interval:16;running:true;repeat:true;onTriggered:{try {
        check(Number.isFinite(stage.width)&&Number.isFinite(stage.height),"Invalid geometry");
        check(stage.width>=90&&stage.width<=550&&stage.height>=Preferences.barHeight,"Rebound escaped bounds");
        check(stage.inputRegion.width===stage.width+12&&stage.inputRegion.height===stage.height+7,"Input mask detached from surface");
        const elapsed=Date.now()-since;
        check(elapsed<4500,"Spring failed to settle");
        if(phase===0&&elapsed>100)configure();
        else if(phase===1){
            rebound=rebound||stage.width>stage.targetWidth+.2;
            if(elapsed>100&&!stage.resizing){
                check(Math.abs(stage.width-460)<.01&&Math.abs(stage.height-320)<.01,"Open stopped away from target");
                if(profiles[profile].style==="fluid"&&profiles[profile].speed===.65)check(rebound,"Fluid motion lost spring rebound");
                stage.targetWidth=300;stage.targetHeight=160;next();
            }
        }else if(phase===2&&elapsed>65){
            const width=stage.width,height=stage.height;
            stage.targetWidth=540;stage.targetHeight=410;
            check(Math.abs(stage.width-width)<.01&&Math.abs(stage.height-height)<.01,"Retarget snapped surface");next();
        }else if(phase===3&&elapsed>100&&!stage.resizing){
            check(Math.abs(stage.width-540)<.01&&Math.abs(stage.height-410)<.01,"Interrupted spring missed target");
            stage.panel="idle";stage.targetWidth=90;stage.targetHeight=Preferences.barHeight;next();
        }else if(phase===4&&elapsed>100&&!stage.resizing){
            check(stage.width===90&&stage.height===Preferences.barHeight,"Close missed resting size");
            profile++;
            if(profile<profiles.length){phase=0;configure();}
            else {stage.panel="launcher";stage.targetWidth=460;stage.targetHeight=320;next();}
        }else if(phase===5&&elapsed>65){
            Preferences.motion="instant";next();
        }else if(phase===6&&elapsed>40){
            check(stage.width===460&&stage.height===320&&!stage.resizing,"Reduced motion did not finish active springs");
            stage.targetWidth=300;stage.targetHeight=180;
            check(stage.width===300&&stage.height===180,"Reduced motion animated a new target");next();
        }else if(phase===7&&elapsed>100){
            check(!stage.resizing&&stage.width===300&&stage.height===180,"Reduced motion retained spring work");
            Preferences.motion="fluid";stage.continuousWidth=true;stage.targetWidth=320;
            check(stage.width===320,"Continuous aperture acquired a second animation");next();
        }else if(phase===8&&elapsed>100){
            check(!stage.resizing&&stage.width===320,"Continuous aperture kept spring work");
            stage.targetWidth=0;check(stage.width===0,"Hidden stage retained resting width");
            console.log("MOTION CHECK PASS: fluid/gentle speeds, rebound, bounds, input geometry, retargeting, reduced motion and continuous aperture");Qt.quit();
        }
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''', 'MOTION CHECK PASS: fluid/gentle speeds, rebound, bounds, input geometry, retargeting, reduced motion and continuous aperture', timeout=40)
