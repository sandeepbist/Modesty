import QtQuick
import QtQuick.Layouts
import qs.services
import qs.components
import qs.theme

ColumnLayout {
    spacing:12
    Component.onCompleted:Updates.refresh()
    PanelText {Layout.fillWidth:true;text:"Installed · "+(Updates.state.current?.slice(0,8)||"Checking…");font.pixelSize:12;font.weight:Font.Medium}
    PanelText {Layout.fillWidth:true;text:Updates.state.message||"Check for updates when you are ready.";wrapMode:Text.WordWrap;elide:Text.ElideNone;font.pixelSize:12;color:Theme.subtext}
    PanelText {Layout.fillWidth:true;visible:!!Updates.state.title;text:Updates.state.title||"";wrapMode:Text.WordWrap;elide:Text.ElideNone;font.pixelSize:12}
    RowLayout {
        Layout.fillWidth:true;spacing:8
        ActionButton {text:"Check for updates";enabled:!Updates.busy&&!Preferences.preview;Accessible.name:text;onClicked:Updates.run("check")}
        ActionButton {text:"Download";visible:Updates.state.available&&!Updates.state.staged;enabled:!Updates.busy;Accessible.name:text;onClicked:Updates.run("download")}
        ActionButton {text:"Install and reload";primary:true;visible:!!Updates.state.staged;enabled:!Updates.busy;Accessible.name:text;onClicked:Updates.run("apply")}
        Item {Layout.fillWidth:true}
    }
    PanelText {Layout.fillWidth:true;visible:!!Updates.state.error;text:Updates.state.error||"";wrapMode:Text.WordWrap;elide:Text.ElideNone;font.pixelSize:11;color:Theme.red}
    PanelText {
        Layout.fillWidth:true;wrapMode:Text.WordWrap;elide:Text.ElideNone;font.pixelSize:11;color:Theme.subtext
        text:"Updates use checked main revisions and test the download before installation. Reload briefly closes Modesty’s panels. Finish assistant work, voice input and recording first."
    }
    PanelText {
        Layout.fillWidth:true;wrapMode:Text.WordWrap;elide:Text.ElideNone;font.pixelSize:11;color:Theme.subtext
        text:"Your desktop configs, packages, plugins and model files stay in place. Update system packages separately with a full Arch upgrade. Local checkout edits need a manual update."
    }
    Repeater {
        model:Updates.state.compatibility?.warnings||[]
        PanelText {required property string modelData;Layout.fillWidth:true;text:modelData;wrapMode:Text.WordWrap;elide:Text.ElideNone;font.pixelSize:11;color:Theme.subtext}
    }
    RowLayout {
        Layout.fillWidth:true;spacing:8
        ActionButton {text:"Reload shell";enabled:!Updates.busy&&!Preferences.preview;Accessible.name:text;onClicked:Updates.run("reload")}
        ActionButton {text:"Roll back";visible:!!Updates.state.rollback;enabled:!Updates.busy&&!Preferences.preview;Accessible.name:"Restore previous Modesty revision and reload";onClicked:Updates.run("rollback")}
        Item {Layout.fillWidth:true}
    }
}
