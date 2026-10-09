import QtQuick
import QtQuick.Controls
import qs.theme

ScrollBar {
    objectName: "settings-scrollbar"
    policy: ScrollBar.AsNeeded
    active: true
    visible: size < 1
    implicitWidth: 12
    minimumSize: .08
    contentItem: Rectangle {
        implicitWidth: 4
        radius: 2
        color: Theme.withAlpha(Theme.text, parent.pressed ? .5 : parent.hovered ? .36 : .22)
    }
}
