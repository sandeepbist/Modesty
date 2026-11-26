import QtQuick
import qs.components
import qs.theme

Item {
    id: root
    property alias text: input.text
    property alias placeholderText: input.placeholderText
    property alias editor: input
    property bool horizontal: false
    property int textSize: 12
    signal step(int delta)
    signal submit()

    implicitHeight: 28

    Icon {
        id: searchIcon
        x: 3
        anchors.verticalCenter: parent.verticalCenter
        icon: "search"
        size: root.textSize + 1
        color: input.activeFocus ? Theme.accent : Theme.subtext
    }

    EntryField {
        id: input
        anchors.left: searchIcon.right
        anchors.leftMargin: 8
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        height: parent.height
        leftPadding: 0
        rightPadding: 0
        font.pixelSize: Tokens.textSize(root.textSize)
        Accessible.name: placeholderText
        background: null
        Keys.onUpPressed: root.step(-1)
        Keys.onDownPressed: root.step(1)
        Keys.onLeftPressed: event => {
            event.accepted = root.horizontal && !text;
            if (event.accepted) root.step(-1);
        }
        Keys.onRightPressed: event => {
            event.accepted = root.horizontal && !text;
            if (event.accepted) root.step(1);
        }
        onAccepted: root.submit()
    }
}
