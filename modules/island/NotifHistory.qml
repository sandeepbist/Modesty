import QtQuick
import QtQuick.Layouts
import qs.components
import qs.services
import qs.theme

ColumnLayout {
    spacing: 10

    PanelHeader {
        title: "Notifications"
        IconButton {
            icon: "delete_sweep"
            label: "Clear all"
            onClicked: Notifications.clearAll()
        }

    }

    NotificationFeed {Layout.fillWidth:true;Layout.fillHeight:true;showHeader:false}
}
