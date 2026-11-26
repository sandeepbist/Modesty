from qml import run

run('''import QtQuick
import QtQuick.Window
import Quickshell
import qs.components
import qs.services
ShellRoot {
    FloatingWindow {
        visible:true;implicitWidth:360;implicitHeight:220
        IconButton {id:button;x:260;y:20;icon:"document_scanner";label:"Analyze Page · sends exposed document text and the visible window image to your configured AI provider"}
        HintBubble {id:tip;wrap:true}
        HintBubble {id:standard}
    }
    property int phase:0
    property double since:Date.now()
    Timer {interval:30;running:true;repeat:true;onTriggered:{try {
        if(Date.now()-since>4000)throw new Error("Tooltip did not settle");
        if(phase===0){
            if(standard.wrap||standard.height!==30)throw new Error("Default tooltip behavior changed");
            Preferences.tooltipDelay=0;button.forceActiveFocus();Hints.show(button,button.label);phase=1;
        }else if(phase===1&&tip.opacity>.99){
            if(tip.heldText!==button.label||tip.height<=30||tip.width>320||!button.activeFocus||tip.activeFocus)
                throw new Error("Tooltip text, wrapping, bounds or focus failed");
            Hints.hide(button);phase=2;
        }else if(phase===2&&tip.opacity===0){
            console.log("LUMA PAGE QML PASS: connected inline tooltip, complete disclosure, wrapped bounds, unchanged focus and default tooltip behavior");Qt.quit();
        }
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''','LUMA PAGE QML PASS: connected inline tooltip, complete disclosure, wrapped bounds, unchanged focus and default tooltip behavior')
