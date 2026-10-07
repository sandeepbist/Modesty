import QtQuick
import QtQuick.Controls
import Quickshell
import qs.services
import qs.theme

Rectangle {
    id: root
    property var notification: null
    property bool expanded: false
    property bool interactive: true
    property bool popup: false
    readonly property bool canExpand: !!notification?.body || !!notification?.actions.length
    signal toggleExpanded()
    signal dismissed()
    implicitHeight: Math.max(popup?100:60,content.y+content.implicitHeight+(popup?18:14))
    radius:14;color:popup?"transparent":Theme.withAlpha(Theme.text,.035)
    border.width:popup?0:1;border.color:Theme.withAlpha(Theme.text,.045)
    antialiasing:true
    Behavior on height {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
    Rectangle {
        x:root.popup?14:12;y:root.popup?17:13;width:root.popup?38:28;height:width;radius:root.popup?12:9;color:Theme.withAlpha(Theme.text,.04)
        Image {id:appIcon;anchors.centerIn:parent;width:root.popup?30:22;height:width;source:root.notification?.appIcon?Quickshell.iconPath(root.notification.appIcon,true):"";sourceSize:Qt.size(60,60);asynchronous:true;visible:status===Image.Ready}
        Icon {anchors.centerIn:parent;icon:"notifications";size:root.popup?24:19;color:Theme.accent;visible:appIcon.status!==Image.Ready}
    }
    Column {
        id:content;x:root.popup?64:50;y:root.popup?16:12;width:Math.max(0,parent.width-x-38);spacing:root.popup?7:5
        PanelText {width:parent.width;text:root.notification?.appName||"Notification";font.pixelSize:root.popup?11:10;font.weight:Font.Medium;color:Theme.subtext}
        PanelText {width:parent.width;text:root.notification?.summary||"";font.pixelSize:root.popup?14:13;font.weight:Font.Medium;wrapMode:Text.Wrap;maximumLineCount:root.expanded||root.popup?2:1}
        PanelText {width:parent.width;visible:Preferences.notificationBody&&!!text;text:root.notification?.body||"";font.pixelSize:12;color:Theme.subtext;wrapMode:Text.Wrap;maximumLineCount:root.expanded?100:root.popup?2:1;elide:Text.ElideRight;lineHeight:1.15}
        PanelText {visible:root.expanded;text:root.notification?Qt.formatDateTime(root.notification.receivedAt,"ddd, h:mm ap"):"";font.pixelSize:10;color:Theme.subtext}
        Flow {
            width:parent.width;spacing:6;visible:root.expanded||root.popup
            Repeater {model:root.notification?.actions.filter(a=>a.identifier!=="default")??[]
                ActionButton {required property var modelData;text:modelData.text;width:Math.min(implicitWidth,parent.width);implicitHeight:30;enabled:root.interactive;onClicked:root.notification.invokeAction(modelData.identifier)}
            }
        }
    }
    MouseArea {
        x:0;y:0;width:parent.width-38;height:content.y+content.children[1].height+24
        enabled:root.interactive;cursorShape:Qt.PointingHandCursor
        onClicked:{if(root.popup){const action=root.notification?.actions.find(a=>a.identifier==="default");if(action)root.notification.invokeAction(action.identifier);else IslandState.openMenu("notifhistory");}else if(root.canExpand)root.toggleExpanded();}
    }
    IconButton {anchors.right:parent.right;anchors.rightMargin:5;y:7;icon:"close";label:"Dismiss notification";size:12;enabled:root.interactive;onClicked:root.dismissed()}
    IconButton {anchors.right:parent.right;anchors.rightMargin:5;y:38;icon:root.expanded?"expand_less":"expand_more";label:root.expanded?"Collapse message":"Expand message";size:12;visible:!root.popup&&root.canExpand;enabled:root.interactive;onClicked:root.toggleExpanded()}
}
