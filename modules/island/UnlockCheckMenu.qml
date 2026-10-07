import QtQuick
import QtQuick.Layouts
import qs.services
import qs.components
import qs.theme

FocusScope {
    ColumnLayout {
        anchors.fill: parent; spacing: 12
        PanelHeader { title: "Verify unlock"; backPanel: "settings" }
        PanelText { Layout.fillWidth: true; text: "Verify your login password. Your desktop stays unlocked."; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Theme.subtext; font.pixelSize: 12 }
        Item { Layout.fillHeight: true }
        EntryField { id: password; objectName: "unlockCheckPassword"; Layout.fillWidth: true; echoMode: Session.verifyResponseVisible ? TextInput.Normal : TextInput.Password; placeholderText: Session.verifyPrompt; enabled: !Session.verifyAuthenticating; onAccepted: { Session.verifyPassword(text); clear(); } }
        PanelText { Layout.fillWidth: true; visible: Session.authenticationCheckResult.length > 0; text: Session.authenticationCheckResult; wrapMode: Text.WordWrap; elide: Text.ElideNone; color: Session.authenticationVerified ? Theme.accent : Theme.red; font.pixelSize: Tokens.captionSize }
        ActionButton { Layout.alignment: Qt.AlignRight; text: Session.verifyAuthenticating ? "Checking…" : "Verify password"; primary: true; enabled: !Session.verifyAuthenticating && password.text.length > 0; onClicked: { Session.verifyPassword(password.text); password.clear(); } }
    }
    Component.onDestruction: { password.clear(); Session.cancelVerification(); }
}
