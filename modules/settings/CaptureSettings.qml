import QtQuick
import QtQuick.Layouts
import qs.services
import qs.components
import qs.theme

ColumnLayout {
    id:root
    spacing:10
    function reveal(key){return privacyToggle.enabled?privacyToggle:captureStatus;}
    Component.onCompleted:LumaCapture.refresh()
    RowLayout {
        Layout.fillWidth:true;spacing:12
        PanelText {Layout.fillWidth:true;text:"Hide Luma from screen sharing";font.pixelSize:13;font.weight:Font.Medium;wrapMode:Text.WordWrap}
        Toggle {
            id:privacyToggle;objectName:"custom-private-capture"
            implicitWidth:40;implicitHeight:32
            text:"Hide Luma from screen sharing"
            Accessible.description:captureStatus.text
            checked:LumaCapture.state?.enabled===true
            enabled:LumaCapture.canToggle
            onToggled:{LumaCapture.setEnabled(checked);checked=Qt.binding(()=>LumaCapture.state?.enabled===true);}
        }
    }
    PanelText {
        id:captureStatus;objectName:"custom-private-capture-status"
        Layout.fillWidth:true;wrapMode:Text.WordWrap
        activeFocusOnTab:!privacyToggle.enabled
        Accessible.name:text
        text:LumaCapture.status
        font.pixelSize:12;color:Theme.subtext
    }
    PanelText {
        objectName:"custom-private-capture-error"
        Layout.fillWidth:true;wrapMode:Text.WordWrap
        visible:!!LumaCapture.error;text:LumaCapture.error
        font.pixelSize:12;color:Theme.red
    }
    ActionButton {
        objectName:"custom-private-capture-refresh"
        text:"Refresh";implicitHeight:28
        enabled:LumaCapture.available&&!LumaCapture.busy
        Accessible.description:"Check the saved setting and active screen sharing protection."
        onClicked:LumaCapture.refresh()
    }
    PanelText {
        Layout.fillWidth:true;wrapMode:Text.WordWrap
        text:"Also hides the entire island, dock, clock and shared cursor. Stop sharing before changing this setting. Experimental, for supported desktop captures only. Other capture methods may still show Luma; verify what viewers see."
        font.pixelSize:12;color:Theme.subtext
    }
}
