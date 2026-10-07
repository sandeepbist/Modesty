import QtQuick
import QtQuick.Layouts
import qs.services
import qs.theme

RowLayout {
    id: root
    property string title: ""
    property string backPanel: "quicksettings"
    default property alias controls: trailing.data
    Layout.fillWidth: true
    implicitHeight: Math.max(32, trailing.implicitHeight)
    spacing: 8
    data: [IconButton {
        icon: "arrow_back"; size: 16
        label: root.backPanel === "quicksettings" ? "Control center" : "Back"
        onClicked: IslandState.openMenu(root.backPanel)
    },
    PanelText {
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignVCenter
        text: root.title
        font.pixelSize: 15; font.weight: Font.Medium
    },
    RowLayout { id: trailing; spacing: 8 }]
}
