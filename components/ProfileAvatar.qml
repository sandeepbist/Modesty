import QtQuick
import Quickshell
import Quickshell.Widgets
import qs.services
import qs.theme

ClippingRectangle {
    id: root
    implicitWidth: 48; implicitHeight: 48
    radius: width / 2
    color: Theme.surfaceSolid
    readonly property bool hasImage: picture.status === Image.Ready
    Image {
        id: picture
        anchors.fill: parent
        source: Preferences.profileImage === "none" || (Preferences.preview && !Preferences.profileImage) ? "" : Preferences.profileImage || ("file://" + Quickshell.env("HOME") + "/.face")
        sourceSize: Qt.size(192,192)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
    }
    Icon {anchors.centerIn:parent;icon:"person";size:parent.width*.48;visible:!root.hasImage;color:Theme.subtext}
}
