import QtQuick
import qs.services
import qs.components
import qs.theme
Item {
    Icon {x:13;anchors.verticalCenter:parent.verticalCenter;size:17;icon:FocusTimer.phase==="finished"?"check":"timer";color:Theme.accent}
    RollingText {x:35;width:parent.width-71;height:parent.height;slideDigits:FocusTimer.phase!=="finished";text:FocusTimer.phase==="finished"?"Done":FocusTimer.timeText;font.family:Tokens.clockFont;font.pixelSize:14;font.weight:Font.Medium;font.features:({tnum:1});horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
    MouseArea {anchors.fill:parent;anchors.rightMargin:35;cursorShape:Qt.PointingHandCursor;onClicked:IslandState.openMenu("focus")}
    IconButton {anchors.right:parent.right;anchors.rightMargin:4;anchors.verticalCenter:parent.verticalCenter;icon:FocusTimer.phase==="finished"?"close":FocusTimer.phase==="paused"?"play_arrow":"pause";label:FocusTimer.phase==="finished"?"Dismiss timer":FocusTimer.phase==="paused"?"Resume timer":"Pause timer";size:14;onClicked:FocusTimer.phase==="finished"?FocusTimer.cancel():FocusTimer.pause()}
}
