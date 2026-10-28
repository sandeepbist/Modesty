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
    readonly property var secondaryActions: notification?.actions.filter(a=>a.identifier!=="default")??[]
    readonly property bool canExpand: !!notification?.body || !!notification?.actions.length
    signal toggleExpanded()
    signal dismissed()
    implicitHeight: Math.max(popup?0:60,content.y+content.implicitHeight+14)
    radius:14;color:popup?"transparent":Theme.withAlpha(Theme.text,.035)
    border.width:popup?0:1;border.color:Theme.withAlpha(Theme.text,.045)
    antialiasing:true
    Behavior on height {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
    Rectangle {
        objectName:"notificationIcon"
        x:root.popup?14:12;y:root.popup?15:13;width:root.popup?18:28;height:width;radius:9;color:root.popup?"transparent":Theme.withAlpha(Theme.text,.04)
        Image {id:appIcon;anchors.centerIn:parent;width:root.popup?18:22;height:width;source:root.notification?.appIcon?Quickshell.iconPath(root.notification.appIcon,true):"";sourceSize:Qt.size(60,60);asynchronous:true;visible:status===Image.Ready}
        Icon {anchors.centerIn:parent;icon:"notifications";size:root.popup?18:19;color:root.popup?Theme.subtext:Theme.accent;visible:appIcon.status!==Image.Ready}
    }
    Column {
        id:content;x:root.popup?14:50;y:root.popup?10:12;width:Math.max(0,parent.width-x-(root.popup?14:38));spacing:root.popup?6:5
        Item {
            width:parent.width;height:root.popup?28:appName.implicitHeight
            PanelText {id:appName;objectName:"notificationAppName";x:root.popup?24:0;anchors.verticalCenter:parent.verticalCenter;width:Math.max(0,parent.width-x-(root.popup?26:0));text:root.notification?.appName||"Notification";font.pixelSize:root.popup?11:10;font.weight:Font.Medium;color:Theme.subtext}
        }
        PanelText {id:summary;objectName:"notificationSummary";width:parent.width;text:root.notification?.summary||"";font.pixelSize:root.popup?14:13;font.weight:Font.Medium;wrapMode:Text.Wrap;maximumLineCount:root.expanded||root.popup?2:1}
        PanelText {id:body;objectName:"notificationBody";width:parent.width;visible:Preferences.notificationBody&&!!text;text:root.notification?.body||"";font.pixelSize:12;color:Theme.subtext;wrapMode:Text.Wrap;maximumLineCount:root.expanded?100:root.popup?2:1;elide:Text.ElideRight;lineHeight:1.15}
        PanelText {objectName:"notificationTimestamp";visible:root.expanded;text:root.notification?Qt.formatDateTime(root.notification.receivedAt,"ddd, h:mm ap"):"";font.pixelSize:10;color:Theme.subtext}
        Flow {
            id:actions;objectName:"notificationActions"
            width:parent.width;spacing:6;visible:root.popup?root.secondaryActions.length>0:root.expanded
            Repeater {model:root.secondaryActions
                ActionButton {
                    id:action
                    required property var modelData
                    objectName:"notificationAction-"+modelData.identifier
                    text:modelData.text;width:Math.min(implicitWidth,parent.width);implicitHeight:root.popup?Math.max(30,actionLabel.implicitHeight+12):30
                    topPadding:root.popup?6:Math.min(padding,Math.max(2,(height-actionLabel.implicitHeight)/2));bottomPadding:topPadding
                    enabled:root.interactive;onClicked:root.notification.invokeAction(modelData.identifier)
                    background:Rectangle {
                        radius:root.popup?9:12;color:root.popup?Theme.withAlpha(Theme.text,.045):Theme.surfaceSolid
                        border.width:action.activeFocus?1:0;border.color:Theme.accent
                        Rectangle {anchors.fill:parent;radius:parent.radius;color:Theme.withAlpha(Theme.text,action.pressed?.12:action.hovered?(root.popup?.065:.14):0);Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                    }
                    contentItem:PanelText {
                        id:actionLabel;text:action.text;font.pixelSize:12;font.weight:Font.Medium
                        horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter
                        wrapMode:root.popup?Text.WrapAnywhere:Text.NoWrap;elide:root.popup?Text.ElideNone:Text.ElideRight
                    }
                }
            }
        }
    }
    AbstractButton {
        id:activate
        objectName:"notificationActivate"
        x:0;y:0;width:root.popup?parent.width:parent.width-38;height:root.popup?(actions.visible?content.y+actions.y-6:content.y+content.implicitHeight):content.y+summary.height+24
        enabled:root.interactive;focusPolicy:Qt.StrongFocus
        Accessible.name:[root.notification?.appName,root.notification?.summary].filter(Boolean).join(". ")
        Accessible.description:root.popup?(root.notification?.actions.find(a=>a.identifier==="default")?.text||"Open notification history"):root.expanded?"Collapse message":"Expand message"
        Keys.onReturnPressed:clicked()
        Keys.onEnterPressed:clicked()
        HoverHandler {cursorShape:Qt.PointingHandCursor}
        background:Rectangle {radius:root.radius;color:"transparent";border.width:activate.activeFocus?1:0;border.color:Theme.accent}
        contentItem:Item {}
        onClicked:{if(root.popup){const action=root.notification?.actions.find(a=>a.identifier==="default");if(action)root.notification.invokeAction(action.identifier);else IslandState.openMenu("notifhistory");}else if(root.canExpand)root.toggleExpanded();}
    }
    IconButton {objectName:"notificationDismiss";anchors.right:parent.right;anchors.rightMargin:5;y:root.popup?8:7;width:root.popup?32:implicitWidth;height:root.popup?32:implicitHeight;icon:"close";label:"Dismiss notification";size:12;color:root.popup?Theme.subtext:Theme.text;enabled:root.interactive;onClicked:root.dismissed()}
    IconButton {anchors.right:parent.right;anchors.rightMargin:5;y:38;icon:root.expanded?"expand_less":"expand_more";label:root.expanded?"Collapse message":"Expand message";size:12;visible:!root.popup&&root.canExpand;enabled:root.interactive;onClicked:root.toggleExpanded()}
}
