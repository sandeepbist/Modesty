import QtQuick
import QtQuick.Layouts
import qs.services
import qs.components
import qs.theme

ColumnLayout {
    function reveal(key){return voiceSetup.enabled?voiceSetup:setupStatus;}
    spacing:10
    Component.onCompleted:Voice.checkInstallation()
    PanelText {
        Layout.fillWidth:true
        text:"Moonshine Small · English · Local CPU"
        font.pixelSize:12;font.weight:Font.Medium
    }
    PanelText {
        Layout.fillWidth:true;wrapMode:Text.WordWrap
        text:"Install once to download the model and its isolated runtime. No API key or manual configuration. Audio stays on this PC."
        font.pixelSize:12;color:Theme.subtext
    }
    RowLayout {
        Layout.fillWidth:true;spacing:8
        ActionButton {
            id:voiceSetup;objectName:"custom-setup"
            text:Voice.installing?"Installing…":Voice.installed?"Repair installation":"Install local voice"
            enabled:!Voice.installing&&!Voice.checking&&!Voice.active&&!Preferences.preview&&!Session.isLocked()
            Accessible.name:text
            onClicked:Voice.install()
        }
        PanelText {
            Layout.fillWidth:true;wrapMode:Text.WordWrap
            text:Voice.checking?"Checking…":Voice.installed?"Installed":"Not installed"
            font.pixelSize:12;color:Voice.installed?Theme.green:Theme.subtext
        }
    }
    PanelText {
        id:setupStatus;objectName:"custom-setup-prerequisite";activeFocusOnTab:!voiceSetup.enabled
        Accessible.name:text
        Layout.fillWidth:true;wrapMode:Text.WordWrap
        text:Preferences.preview?"Voice installation is unavailable in preview.":Session.isLocked()?"Unlock your session to install local voice.":Voice.active?"Finish voice input before repairing installation.":Voice.installing?"Wait for voice installation to finish.":Voice.checking?"Wait for the voice installation check.":Voice.setupMessage||Voice.error||"Setup opens a terminal with download progress. Your password is requested only if a system dependency is missing."
        font.pixelSize:12;color:Theme.subtext
    }
}
