import QtQuick
import qs.services
import qs.components
import qs.theme
Item {
    id:root
    property bool condensed:false
    readonly property real condensedMinimumWidth:21+condensedMeasure.advanceWidth
    readonly property bool minimal:condensed&&width<condensedMinimumWidth
    TextMetrics {id:condensedMeasure;text:FocusTimer.phase==="finished"?"Done":FocusTimer.timeText;font.family:Tokens.clockFont;font.pixelSize:12;font.weight:Font.Medium;font.features:({tnum:1})}
    Rectangle {anchors.fill:parent;anchors.margins:2;radius:height/2;color:Theme.withAlpha(Theme.accent,.085)}
    Icon {x:root.condensed?3:13;anchors.verticalCenter:parent.verticalCenter;size:root.condensed?14:17;icon:FocusTimer.phase==="finished"?"check":"timer";color:Theme.accent}
    RollingText {x:root.condensed?19:35;width:Math.max(0,parent.width-(root.condensed?21:71));height:parent.height;visible:!root.minimal;countsDown:true;slideDigits:FocusTimer.phase!=="finished";text:condensedMeasure.text;font.family:Tokens.clockFont;font.pixelSize:root.condensed?condensedMeasure.font.pixelSize:14;font.weight:Font.Medium;font.features:({tnum:1});horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
    Item {
        id:detail;objectName:"focusDetail"
        width:root.condensed?parent.width:action.x;height:parent.height;activeFocusOnTab:true
        Rectangle {anchors.fill:parent;anchors.margins:2;radius:height/2;color:"transparent";border.width:detail.activeFocus?1:0;border.color:Theme.accent}
        MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:IslandState.openMenu("focus")}
        Keys.onReturnPressed:IslandState.openMenu("focus")
        Keys.onSpacePressed:IslandState.openMenu("focus")
        Accessible.role:Accessible.Button;Accessible.name:"Focus timer, "+FocusTimer.phase+", "+FocusTimer.timeText+". Open details"
        Accessible.onPressAction:IslandState.openMenu("focus")
    }
    IconButton {id:action;visible:!root.condensed;objectName:"focusAction";anchors.right:parent.right;anchors.rightMargin:4;anchors.verticalCenter:parent.verticalCenter;icon:FocusTimer.phase==="finished"?"close":FocusTimer.phase==="paused"?"play_arrow":"pause";label:FocusTimer.phase==="finished"?"Dismiss timer":FocusTimer.phase==="paused"?"Resume timer":"Pause timer";size:14;onClicked:FocusTimer.phase==="finished"?FocusTimer.cancel():FocusTimer.pause()}
}
