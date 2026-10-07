pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import qs.theme
Singleton {
    id:root
    property real progress:0
    property string greeting:""
    Behavior on progress {NumberAnimation {duration:Tokens.reducedMotion?0:420;easing.type:Easing.OutCubic}}
    Timer {interval:16;running:true;onTriggered:root.progress=1}
    Timer {id:welcome;interval:650;onTriggered:if(Preferences.welcomeAtLogin&&!IslandState.menuOpen&&!Session.isLocked())Context.show("welcome",root.greeting,"",0)}
    Process {running:!Preferences.preview;command:["python3",Qt.resolvedUrl("../scripts/welcome.py").toString().replace("file://","")]
        stdout:StdioCollector {onStreamFinished:{try{const result=JSON.parse(text);if(result.first){root.greeting=result.message;welcome.start();}}catch(e){}}}
    }
}
