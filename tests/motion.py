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

run('''import QtQuick
import Quickshell
import "modules/island" as Island
import qs.components
import qs.services
ShellRoot {
    property int phase:0
    FloatingWindow {visible:true;implicitWidth:1000;implicitHeight:300
        Island.IslandSurface {id:surface;availableWidth:1000}
        RollingText {id:marquee;y:60;width:80;height:30;marquee:true;text:"A long media title that needs horizontal scrolling"}
        RollingText {id:label;y:100;width:120;height:30;text:"Alpha"}
        SlidingDigits {id:digits;y:140;width:120;height:40;text:"09"}
    }
    function check(ok,message):void {if(!ok)throw new Error(message+" phase="+phase);}
    function walk(item) {let items=[item];for(const child of item.children||[])items=items.concat(walk(child));return items;}
    Component.onCompleted:Preferences.motion="fluid"
    Timer {id:steps;interval:950;running:true;onTriggered:{try {
        if(phase===0) {
            check(marquee.scrollOffset>0,"Marquee fixture did not start");
            label.text="Beta";digits.text="10";Context.show("welcome","Hello","",0);steps.interval=70;
        } else if(phase===1) {
            check(label.travel<1&&!!label.outgoingText,"Rolling label fixture did not animate");
            check(walk(digits).some(item=>item.progress!==undefined&&item.progress<1),"Digit fixture did not animate");
            check(surface.diagnostics().welcomeProgress>0&&surface.diagnostics().welcomeProgress<1,"Welcome fixture did not animate");
            Preferences.motion="instant";steps.interval=10;
        } else if(phase===2) {
            check(marquee.scrollOffset===0&&marquee.outgoingOffset===0,"Instant mode retains marquee offset");
            check(label.travel===1&&label.outgoingText===""&&label.currentText==="Beta","Instant mode leaves active rolling text");
            for(const item of walk(digits).filter(item=>item.progress!==undefined))check(item.progress===1&&item.outgoing===""&&item.shown===item.value,"Instant mode leaves active digit motion");
            const viewport=walk(surface).find(item=>item.welcomeAmount!==undefined);
            const overlay=walk(viewport).find(item=>item instanceof WelcomeWord).parent;
            check(viewport.welcomeAmount===1&&overlay.reveal===1,"Instant mode leaves welcome partly drawn");
            label.text="Gamma";digits.text="23";steps.interval=800;
        } else if(phase===3) {
            check(label.currentText==="Gamma"&&label.travel===1,"Instant update rolls new text");
            check(marquee.scrollOffset===0,"Instant mode restarts marquee timer");
            for(const item of walk(digits).filter(item=>item.progress!==undefined))check(item.progress===1&&item.outgoing===""&&item.shown===item.value,"Instant digit update animates");
            const viewport=walk(surface).find(item=>item.welcomeAmount!==undefined);
            check(viewport.welcomeAmount===1&&walk(viewport).find(item=>item instanceof WelcomeWord).parent.reveal===1,"Stopped welcome changes after instant selection");
            Context.clear();steps.interval=10;
        } else if(phase===4) {
            check(surface.diagnostics().welcomeProgress===0,"Instant welcome exit leaves overlay");
            Preferences.motion="fluid";steps.interval=900;
        } else if(phase===5) {
            check(marquee.scrollOffset>0,"Fluid mode does not resume marquee");
            console.log("INSTANT TEXT CHECK PASS");Qt.quit();return;
        }
        phase++;steps.restart();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''', 'INSTANT TEXT CHECK PASS')
