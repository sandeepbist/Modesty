import QtQuick
import QtQuick.Controls
import qs.services
import qs.components
import qs.theme
Item {
    id:root
    property bool interactive:true
    property bool showHeader:true
    property bool showTitle:true
    property bool collapsed:false
    property int expandedId:-1
    readonly property bool compact:height<95||width<160
    readonly property bool headerVisible:showHeader&&!compact&&(showTitle||Notifications.list.length>0)
    Item {
        x:14;y:9;width:parent.width-28;height:26;visible:root.headerVisible
        PanelText {anchors.left:parent.left;anchors.verticalCenter:parent.verticalCenter;width:Math.max(0,parent.width-headerControls.width-8);visible:root.showTitle;text:"Notifications"+(Notifications.list.length?"  ·  "+Notifications.list.length:"");font.pixelSize:12;font.weight:Font.Medium}
        Icon {anchors.left:parent.left;anchors.verticalCenter:parent.verticalCenter;visible:!root.showTitle;icon:Notifications.dnd?"notifications_paused":"notifications_none";size:18;color:Theme.subtext}
        Row {id:headerControls;anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter;spacing:2
            IconButton {icon:"check";label:"Clear all notifications";size:14;visible:Notifications.list.length>0;enabled:root.interactive;onClicked:Notifications.clearAll()}
            IconButton {icon:root.collapsed?"expand_more":"expand_less";label:root.collapsed?"Expand notifications":"Collapse notifications";size:14;visible:Notifications.list.length>0;enabled:root.interactive;onClicked:root.collapsed=!root.collapsed}
        }
    }
    Item {
        id:viewport;x:8;y:root.headerVisible?42:0;width:parent.width-16;height:Math.max(0,parent.height-y-8);clip:true
        Column {
            anchors.centerIn:parent;spacing:8
            visible:!Notifications.list.length||root.compact||root.collapsed
            Icon {anchors.horizontalCenter:parent.horizontalCenter;icon:Notifications.dnd?"notifications_paused":"notifications_none";size:root.compact?22:26;color:Theme.subtext}
            PanelText {anchors.horizontalCenter:parent.horizontalCenter;visible:root.width>90;text:Notifications.list.length?Notifications.list.length+" waiting":Notifications.dnd?"Peace is on":"You're all caught up";font.pixelSize:12;color:Theme.subtext}
        }
        MouseArea {anchors.fill:parent;enabled:root.interactive&&(root.compact||root.collapsed);cursorShape:Qt.PointingHandCursor;onClicked:if(root.compact)IslandState.openMenu("notifhistory");else root.collapsed=false}
        ListView {
            id:list;anchors.fill:parent;clip:true;spacing:8
            visible:!root.compact&&!root.collapsed;enabled:root.interactive
            model:Notifications.historyModel;boundsBehavior:Flickable.StopAtBounds
            add:Transition {ParallelAnimation {NumberAnimation {property:"opacity";from:0;to:1;duration:Tokens.animMedium} NumberAnimation {property:"y";from:-12;duration:Tokens.animMedium;easing.type:Easing.OutCubic}}}
            displaced:Transition {NumberAnimation {properties:"x,y";duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
            ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded;minimumSize:.15}
            delegate:NotificationCard {
                id:historyCard
                required property var record
                width:list.width-4;height:implicitHeight
                notification:record;interactive:root.interactive&&!record.closing
                expanded:root.expandedId===record?.serial
                onToggleExpanded:root.expandedId=expanded?-1:record.serial
                onDismissed:Notifications.close(record)
                property real departure:0
                transform:Translate {x:historyCard.departure*24}
                opacity:1-departure
                SequentialAnimation {running:historyCard.record.closing;PauseAnimation {duration:historyCard.record.removalDelay} NumberAnimation {target:historyCard;property:"departure";to:1;duration:Tokens.animMedium;easing.type:Easing.InCubic}}
            }
        }
    }
}
