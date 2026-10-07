pragma Singleton
import QtQuick
import Quickshell
Singleton {
    id:root
    readonly property bool recording:Recorder.active&&!Recorder.selecting
    readonly property bool focus:FocusTimer.active
    readonly property bool dual:recording&&focus
    property string selected:"recording"
    readonly property string primary:recording&&(!focus||selected==="recording")?"recording":"focus"

    readonly property bool headphones:DeviceStatus.available&&!dual
    readonly property int primaryWidth:recording&&Recorder.phase!=="recording"?192:138
    readonly property int focusWidth:dual?40:0
    readonly property int deviceWidth:headphones?40:0
    readonly property int width:primaryWidth+focusWidth+deviceWidth
    function cycle():void {if(dual)selected=primary==="recording"?"focus":"recording";}
    onRecordingChanged:if(recording)selected="recording"
}
