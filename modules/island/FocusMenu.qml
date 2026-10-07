import QtQuick
import QtQuick.Layouts
import qs.components
import qs.services
import qs.theme
ColumnLayout {
    id:root
    spacing:12
    property int minutes:Preferences.focusMinutes
    PanelHeader {title:"Focus timer"}
    ColumnLayout {Layout.fillWidth:true;spacing:6
        PanelText {Layout.fillWidth:true;horizontalAlignment:Text.AlignHCenter;visible:FocusTimer.active;text:FocusTimer.active?FocusTimer.label+(FocusTimer.phase==="paused"?" · Paused":FocusTimer.phase==="finished"?" complete":""):"";font.pixelSize:12;color:Theme.subtext}
        RollingText {Layout.fillWidth:true;Layout.preferredHeight:56;slideDigits:true;text:FocusTimer.active?FocusTimer.timeText:String(root.minutes).padStart(2,"0")+":00";font.family:Tokens.clockFont;font.pixelSize:42;font.weight:Font.Medium;font.features:({tnum:1});horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
        Rectangle {visible:FocusTimer.active;Layout.fillWidth:true;Layout.preferredHeight:3;radius:2;color:Theme.withAlpha(Theme.text,.09)
            Rectangle {width:parent.width*(FocusTimer.active?FocusTimer.progress:0);height:parent.height;radius:2;color:Theme.accent;Behavior on width {NumberAnimation {duration:Tokens.reducedMotion?0:240;easing.type:Easing.OutCubic}}}
        }
    }
    RowLayout {visible:!FocusTimer.active;Layout.fillWidth:true;spacing:8
        Repeater {model:[15,25,45,60]
            ActionButton {id:preset;required property int modelData;Layout.fillWidth:true;text:modelData+" min";onClicked:root.minutes=modelData
                background:Rectangle {radius:10;color:Theme.withAlpha(Theme.text,preset.hovered?.07:.025);border.width:1;border.color:root.minutes===preset.modelData?Theme.accent:Theme.withAlpha(Theme.text,.08);Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}}
            }
        }
    }
    PreferenceSlider {visible:!FocusTimer.active;Layout.fillWidth:true;label:"Duration";display:root.minutes+" min";from:1;to:120;stepSize:1;value:root.minutes;onMoved:value=>root.minutes=value}
    Item {Layout.fillHeight:true}
    PanelText {visible:!!FocusTimer.error;Layout.fillWidth:true;text:FocusTimer.error;font.pixelSize:11;color:Theme.red;wrapMode:Text.Wrap}
    RowLayout {Layout.fillWidth:true;visible:!FocusTimer.active
        ActionButton {Layout.fillWidth:true;text:"Start focus";primary:true;enabled:FocusTimer.loaded;onClicked:FocusTimer.start(root.minutes,false)}
        ActionButton {text:Preferences.breakMinutes+" min break";enabled:FocusTimer.loaded;onClicked:FocusTimer.start(Preferences.breakMinutes,true)}
    }
    RowLayout {Layout.fillWidth:true;visible:FocusTimer.phase==="running"||FocusTimer.phase==="paused"
        ActionButton {Layout.fillWidth:true;primary:true;text:FocusTimer.phase==="paused"?"Resume":"Pause";onClicked:FocusTimer.pause()}
        ActionButton {text:"End session";onClicked:FocusTimer.cancel()}
    }
    RowLayout {Layout.fillWidth:true;visible:FocusTimer.phase==="finished"
        ActionButton {Layout.fillWidth:true;primary:true;text:FocusTimer.kind==="focus"?"Take a break":"Start focus";onClicked:FocusTimer.start(FocusTimer.kind==="focus"?Preferences.breakMinutes:Preferences.focusMinutes,FocusTimer.kind==="focus")}
        ActionButton {text:"Done";onClicked:FocusTimer.cancel()}
    }
}
