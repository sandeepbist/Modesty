import QtQuick
import qs.services
import qs.theme

IconButton {
    icon: Media.repeatIcon
    label: Media.repeatLabel
    enabled: Media.canRepeat
    color: Media.repeating ? Theme.accent : Theme.subtext
    onClicked: Media.cycleRepeat()
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom
        anchors.bottomMargin: 2; width: 3; height: 3; radius: 1.5
        color: Theme.accent; opacity: Media.repeating ? 1 : 0
        Behavior on opacity {NumberAnimation {duration: Tokens.animFast}}
    }
}
