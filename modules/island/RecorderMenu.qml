import QtQuick
import QtQuick.Layouts
import qs.components
import qs.services
import qs.theme
ColumnLayout {
    spacing:12
    PanelHeader {title:"Screen recording"}
    PanelText {Layout.fillWidth:true;visible:Recorder.active;text:Recorder.label;wrapMode:Text.Wrap;elide:Text.ElideNone;font.pixelSize:12;color:Theme.subtext}
    GridLayout {visible:!Recorder.active;columns:2;Layout.fillWidth:true;rowSpacing:8;columnSpacing:8
        Repeater {model:[{name:"Full screen",region:false,sound:false},{name:"Region",region:true,sound:false},{name:"Full screen + sound",region:false,sound:true},{name:"Region + sound",region:true,sound:true}]
            ActionButton {
                id:modeButton
                required property var modelData
                Layout.fillWidth:true;Layout.preferredHeight:56;text:modelData.name
                background:Rectangle {
                    radius:12
                    color:Theme.withAlpha(Theme.text,modeButton.pressed?.10:modeButton.hovered?.07:.025)
                    border.width:1;border.color:modeButton.activeFocus?Theme.accent:Theme.withAlpha(Theme.text,modeButton.hovered?.19:.09)
                    Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                    Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}
                }
                onClicked:Recorder.start(modelData.region,modelData.sound)
            }
        }
    }
    RowLayout {visible:Recorder.active;Layout.fillWidth:true
        ActionButton {Layout.fillWidth:true;visible:Recorder.recording;text:Recorder.phase==="paused"?"Resume":"Pause";onClicked:Recorder.pause()}
        ActionButton {Layout.fillWidth:true;primary:true;text:Recorder.recording?"Stop and save":"Cancel";enabled:Recorder.phase!=="saving";onClicked:Recorder.stop()}
    }
    PanelText {Layout.fillWidth:true;visible:Recorder.phase==="error";text:Recorder.status.error||"";font.pixelSize:12;color:Theme.red;wrapMode:Text.Wrap;elide:Text.ElideNone}
    Item {Layout.fillHeight:true}
    ActionButton {Layout.fillWidth:true;text:"Open recordings folder";onClicked:Recorder.openFolder()}
}
