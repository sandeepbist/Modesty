#!/usr/bin/env python3
"""Check light lifecycle without microphone access or assistant requests."""
from qml import run

run('''import QtQuick
import Quickshell
import qs.components
import qs.services
import qs.theme
ShellRoot {
    FloatingWindow {
        visible:true;implicitWidth:500;implicitHeight:180
        Rectangle {anchors.fill:parent;color:Theme.bgSolid}
        LumaVoiceLight {id:light;anchors.fill:parent;radius:24;edge:true;activity:"idle";active:false;revealOnActivate:true}
        LumaVoiceLight {id:ribbon;width:240;height:76;active:false}
        LumaVoiceLight {id:initialRibbon;width:48;height:26}
    }
    property int phase:0
    property double since:Date.now()
    function next():void {phase++;since=Date.now();}
    function check(ok,label):void {if(!ok)throw new Error(label+" phase="+phase+" "+JSON.stringify({border:light.diagnostics(),ribbon:ribbon.diagnostics()}));}
    Timer {interval:40;running:true;repeat:true;onTriggered:{try {
        const elapsed=Date.now()-since;
        check(elapsed<3500,"Light did not settle");
        const state=light.diagnostics();
        if(phase===0){
            check(!state.rendering&&!state.orbitRunning&&!state.sweepRunning,"Closed light retained work");
            check(initialRibbon.diagnostics().ribbonOpacity<.2&&initialRibbon.diagnostics().entranceRunning,"Initially active ribbon skipped entrance");
            light.active=true;next();
        }
        else if(phase===1&&elapsed>100){check(state.sweepRunning&&!state.orbitRunning,"Search did not start one sweep");next();}
        else if(phase===2&&elapsed>1600){
            check(!state.rendering&&!state.moving&&!state.sweepRunning&&!state.orbitRunning,"Idle search retained rendering");
            check(initialRibbon.diagnostics().ribbonOpacity===1&&!initialRibbon.diagnostics().entranceRunning,"Initially active ribbon did not settle");
            initialRibbon.active=false;light.active=false;next();
        }
        else if(phase===3){light.active=true;next();}
        else if(phase===4&&elapsed>100){check(state.sweepRunning,"Reopening did not replay sweep");light.activity="listening";light.level=.6;next();}
        else if(phase===5&&elapsed>160){
            check(state.orbitRunning&&!state.sweepRunning&&light.energy>0,"Voice lost orbit or energy response");
            check(state.primaryColor===String(Theme.accent)&&state.secondaryColor===String(Theme.secondary),"Light did not use palette colors");
            light.visible=false;next();
        }else if(phase===6){check(!state.rendering&&!state.moving&&!state.orbitRunning,"Hidden voice retained animation");light.visible=true;Preferences.motion="instant";next();}
        else if(phase===7){check(state.rendering&&!state.moving&&!state.orbitRunning&&!state.sweepRunning,"Reduced motion did not retain static voice feedback");Preferences.lumaEffects=false;next();}
        else if(phase===8){check(!state.rendering&&!state.moving,"Disabled effects retained rendering");Preferences.lumaEffects=true;Preferences.motion="fluid";light.activity="error";next();}
        else if(phase===9){check(state.rendering&&!state.moving&&state.primaryColor===String(Theme.red),"Error lost static palette feedback");light.active=false;next();}
        else if(phase===10){
            check(!state.rendering&&!state.orbitRunning&&!state.sweepRunning,"Close retained animation");
            ribbon.active=true;
            check(ribbon.diagnostics().ribbonOpacity===0,"Ribbon snapped to full strength on activation");next();
        }else if(phase===11&&elapsed>80){
            const before=ribbon.diagnostics().ribbonOpacity;
            check(before>0&&before<1&&ribbon.diagnostics().entranceRunning,"Ribbon lost intermediate entrance frames");
            ribbon.level=.8;ribbon.activity="finishing";
            check(ribbon.diagnostics().ribbonOpacity===before,"Voice activity restarted ribbon reveal");next();
        }else if(phase===12&&elapsed>500){
            check(ribbon.diagnostics().ribbonOpacity===1&&!ribbon.diagnostics().entranceRunning,"Ribbon entrance did not settle");
            ribbon.visible=false;next();
        }else if(phase===13){
            check(ribbon.diagnostics().ribbonOpacity===0&&!ribbon.diagnostics().rendering,"Hidden ribbon did not reset reveal");
            ribbon.visible=true;next();
        }else if(phase===14&&elapsed>80){
            check(ribbon.diagnostics().ribbonOpacity>0&&ribbon.diagnostics().ribbonOpacity<1,"Ribbon reappeared abruptly");
            Preferences.motion="instant";next();
        }else if(phase===15){
            check(ribbon.diagnostics().ribbonOpacity===1&&!ribbon.diagnostics().entranceRunning&&!ribbon.diagnostics().moving,"Reduced motion stranded ribbon mid-reveal");
            Preferences.motion="fluid";ribbon.active=false;next();
        }else if(phase===16){
            check(ribbon.diagnostics().ribbonOpacity===0,"Inactive ribbon did not reset");ribbon.active=true;next();
        }else if(phase===17&&elapsed>80){
            check(ribbon.diagnostics().ribbonOpacity>0&&ribbon.diagnostics().ribbonOpacity<1,"Reopening ribbon snapped");
            ribbon.active=false;next();
        }else if(phase===18){
            check(ribbon.diagnostics().ribbonOpacity===0&&!ribbon.diagnostics().entranceRunning&&!ribbon.diagnostics().orbitRunning,"Interrupted entrance retained animation");
            Preferences.motion="instant";ribbon.active=true;next();
        }else if(phase===19){
            check(ribbon.diagnostics().ribbonOpacity===1&&!ribbon.diagnostics().entranceRunning,"Reduced motion animated ribbon activation");
            Preferences.lumaEffects=false;next();
        }else if(phase===20){
            check(!ribbon.diagnostics().rendering&&ribbon.diagnostics().ribbonOpacity===0,"Disabled ribbon retained rendering");
            console.log("LUMA LIGHT CHECK PASS: one sweep per open, idle/hidden shutdown, voice energy, palette, reduced motion and effects toggle; smooth ribbon activation, retargeting, reopening and interrupted reveal");Qt.quit();
        }
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''', 'LUMA LIGHT CHECK PASS: one sweep per open, idle/hidden shutdown, voice energy, palette, reduced motion and effects toggle; smooth ribbon activation, retargeting, reopening and interrupted reveal')
