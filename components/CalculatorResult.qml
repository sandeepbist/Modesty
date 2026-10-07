import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.services
import qs.theme
Rectangle {
    id:root
    property string query:""
    property string result:""
    property string error:""
    property bool copied:false
    readonly property bool requested:Preferences.launcherCalculator&&(query.trim().startsWith("=")||/^(?:[\d.(+-][\d.\s]*(?:[+*/^%()-]|\s+[a-z])|(?:sqrt|sin|cos|tan|log|ln|abs)\s*\()/i.test(query.trim()))
    readonly property bool valid:requested&&result.length>0
    implicitHeight:requested?126:0
    visible:requested;clip:true;radius:16;color:Theme.surfaceSolid
    border.width:1.5;border.color:valid?Theme.accent:Theme.withAlpha(Theme.text,.1)
    function copy():void {if(valid&&!Preferences.preview){Quickshell.clipboardText=result;copied=true;feedback.restart();}}
    onQueryChanged:{result="";error="";copied=false;delay.restart();}
    Timer {id:feedback;interval:1400;onTriggered:root.copied=false}
    Timer {id:delay;interval:120;onTriggered:{
        if(!root.requested)return;
        if(worker.running){restart();return;}
        worker.command=["python3",Qt.resolvedUrl("../scripts/calculator.py").toString().replace("file://",""),root.query];worker.running=true;
    }}
    Process {id:worker;stdout:StdioCollector {onStreamFinished:{try{const d=JSON.parse(text);if(d.query===root.query){root.result=d.result;root.error=d.error;}}catch(e){root.error="Couldn't calculate this expression";}}}}
    Column {anchors.fill:parent;anchors.margins:16;spacing:9
        PanelText {text:"Calculator";font.pixelSize:11;color:Theme.subtext}
        PanelText {width:parent.width;text:root.result||root.error||"Calculating…";font.pixelSize:root.result?23:13;font.weight:Font.Medium;maximumLineCount:2;wrapMode:Text.Wrap}
        PanelText {visible:root.copied;text:"Copied";font.pixelSize:11;color:Theme.subtext}
    }
    MouseArea {anchors.fill:parent;enabled:root.valid;cursorShape:Qt.PointingHandCursor;onClicked:root.copy()}
}
