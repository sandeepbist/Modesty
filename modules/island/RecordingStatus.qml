import QtQuick
import qs.services
import qs.components
import qs.theme
Item {
    id:root
    property bool condensed:false
    readonly property real condensedMinimumWidth:22+condensedMeasure.advanceWidth
    readonly property bool minimal:condensed&&width<condensedMinimumWidth
    TextMetrics {id:condensedMeasure;text:Recorder.phase==="recording"?Recorder.timeText:Recorder.phase==="paused"?"Paused":Recorder.phase==="saving"?"Saving":Recorder.phase==="countdown"?"In "+Recorder.status.remaining:"Preparing";font.family:Tokens.font;font.pixelSize:11;font.weight:Font.Medium;font.features:({tnum:1})}
    Rectangle {anchors.fill:parent;anchors.margins:2;radius:height/2;color:Theme.withAlpha(Theme.red,.085)}
    Icon {x:root.condensed?3:8;anchors.verticalCenter:parent.verticalCenter;size:15;icon:"video_camera_front";color:Recorder.phase==="paused"?Theme.yellow:Theme.red}
    PanelText {x:root.condensed?20:28;width:Math.max(0,parent.width-(root.condensed?22:62));height:parent.height;visible:!root.minimal;text:root.condensed?condensedMeasure.text:Recorder.label;font.pixelSize:root.condensed?condensedMeasure.font.pixelSize:13;font.weight:Font.Medium;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignHCenter;font.features:({tnum:1})}
    Item {
        id:detail;objectName:"recorderDetail"
        width:root.condensed?parent.width:action.x;height:parent.height;activeFocusOnTab:true
        Rectangle {anchors.fill:parent;anchors.margins:2;radius:height/2;color:"transparent";border.width:detail.activeFocus?1:0;border.color:Theme.accent}
        MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:IslandState.openMenu("recorder")}
        Keys.onReturnPressed:IslandState.openMenu("recorder")
        Keys.onSpacePressed:IslandState.openMenu("recorder")
        Accessible.role:Accessible.Button;Accessible.name:"Recording, "+Recorder.label+". Open details"
        Accessible.onPressAction:IslandState.openMenu("recorder")
    }
    IconButton {id:action;visible:!root.condensed;objectName:"recorderAction";anchors.right:parent.right;anchors.rightMargin:4;anchors.verticalCenter:parent.verticalCenter;icon:"stop";size:13;color:Theme.red;label:"Stop recording";enabled:Recorder.phase!=="saving";onClicked:Recorder.stop()}
}
