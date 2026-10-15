#!/usr/bin/env python3
from qml import run

run('''import QtQuick
import QtTest
import Quickshell
import qs.components
import qs.services
import "modules/island" as Island
ShellRoot {
    id:root
    property int phase:0
    property real goal:0
    FloatingWindow {
        id:window;visible:true;implicitWidth:650;implicitHeight:450
        Item {id:host}
        FrameSpring {id:motion;owner:host;targetValue:root.goal}
        ActionButton {id:button;x:520;y:20;text:"Press"}
        Island.Stage {id:stage;stage:"clock";restingWidth:90;targetWidth:90;maximumWidth:600}
    }
    TestCase {id:keyboard;when:false}
    function check(ok,label){if(!ok)throw new Error(label+" phase="+root.phase);}
    Timer {interval:80;running:true;repeat:true;onTriggered:{try{
        if(root.phase===0){Preferences.motion="fluid";root.goal=360;stage.panel="launcher";stage.targetWidth=490;}
        else if(root.phase===1){check(motion.value>0&&motion.value<360&&motion.running,"Spring did not move");const value=motion.value,v=motion.velocity;root.goal=150;check(motion.value===value&&motion.velocity===v,"Retarget reset spring state");const width=stage.apertureWidth;stage.inlineContext=true;check(Math.abs(stage.apertureWidth-width)<.01,"Entering inline snapped");}
        else if(root.phase===2){const width=stage.apertureWidth;stage.inlineContext=false;check(Math.abs(stage.apertureWidth-width)<.01,"Leaving inline snapped");Preferences.motionSpeed=.65;Preferences.motion="gentle";check(motion.running&&Number.isFinite(motion.velocity),"Live preferences reset state");}
        else if(root.phase===3){stage.inlineContext=true;stage.targetWidth=320;}
        else if(root.phase===4){const width=stage.apertureWidth;stage.inlineContext=false;check(Math.abs(stage.apertureWidth-width)<.01,"Active inline handoff snapped");Preferences.motion="instant";check(motion.value===150&&!motion.running&&motion.velocity===0,"Reduced motion retained spring work");root.goal=230;check(motion.value===230&&!motion.running,"Reduced motion started new work");}
        else if(root.phase===5){Preferences.motion="fluid";Preferences.motionSpeed=1;stage.continuousWidth=true;stage.targetWidth=350;check(stage.apertureWidth===350,"Continuous width not exact");root.goal=450;}
        else if(root.phase===6){stage.continuousWidth=false;check(stage.apertureWidth===350,"Continuous handoff snapped");stage.targetWidth=500;host.visible=false;check(motion.value===450&&!motion.running,"Hidden owner kept frame work");}
        else if(root.phase===7){stage.inlineContext=true;stage.targetWidth=300;}
        else if(root.phase===8){stage.visible=false;}
        else if(root.phase===9){check(!stage.resizing&&stage.apertureWidth===300,"Hidden inline stage kept work");button.forceActiveFocus();keyboard.keyPress(Qt.Key_Space,Qt.NoModifier,0);keyboard.wait(30);check(button.scale<.999&&button.scale>.96,"Fast press lost native scale amplitude");keyboard.keyRelease(Qt.Key_Space,Qt.NoModifier,0);check(button.scale<.999&&button.scale>.96&&!button.pressed,"Fast release lost spring motion");}
        else if(root.phase===10){button.visible=false;check(button.scale===1,"Hidden press did not settle");console.log("FRAME SPRING PASS");Qt.quit();}
        root.phase++;
    }catch(error){console.error(error);Qt.exit(1);}}}
}''','FRAME SPRING PASS')
