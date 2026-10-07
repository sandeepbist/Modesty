import QtQuick
import qs.services
import qs.components
import qs.theme
Item {
    Rectangle {x:14;anchors.verticalCenter:parent.verticalCenter;width:7;height:7;radius:4;color:Recorder.phase==="paused"?Theme.yellow:Theme.red}
    PanelText {x:30;width:parent.width-64;height:parent.height;text:Recorder.label;font.pixelSize:13;font.weight:Font.Medium;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignHCenter;font.features:({tnum:1})}
    MouseArea {anchors.fill:parent;anchors.rightMargin:34;cursorShape:Qt.PointingHandCursor;onClicked:IslandState.openMenu("recorder")}
    IconButton {anchors.right:parent.right;anchors.rightMargin:4;anchors.verticalCenter:parent.verticalCenter;icon:"stop";size:13;color:Theme.red;label:"Stop recording";enabled:Recorder.phase!=="saving";onClicked:Recorder.stop()}
}
