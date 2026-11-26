import QtQuick
import qs.components
import qs.services
import qs.theme

TextInput {
    id: password
    required property bool preview
    required property bool departing
    readonly property bool busy: !preview && Session.authenticating
    readonly property bool responseVisible: !preview && Session.responseVisible
    signal submitting()

    objectName: "lockPassword"
    verticalAlignment: TextInput.AlignVCenter
    horizontalAlignment: TextInput.AlignHCenter
    color: responseVisible ? Theme.wallpaperText : "transparent"
    font.family: Tokens.font
    font.pixelSize: 16
    font.letterSpacing: responseVisible ? 0 : 2
    selectionColor: Theme.accent
    selectedTextColor: color
    renderType: Tokens.textRenderType
    Accessible.name: "Login password"
    echoMode: responseVisible ? TextInput.Normal : TextInput.Password
    passwordCharacter: "•"
    passwordMaskDelay: 0
    clip: true
    focus: true
    enabled: !busy && !departing
    selectByMouse: false
    cursorDelegate: InputCaret {
        editor: password
        caretWidth: 1
        color: Theme.wallpaperText
        reveal: password.responseVisible && password.length > 0
    }

    function submit(): void {
        if (preview || !enabled || !length) return;
        submitting();
        Session.submit(text);
        clear();
    }
    onAccepted: submit()
    Keys.onEscapePressed: clear()
    Keys.onTabPressed: event => { event.accepted = true; }
    Keys.onBacktabPressed: event => { event.accepted = true; }
    Component.onDestruction: clear()
}
