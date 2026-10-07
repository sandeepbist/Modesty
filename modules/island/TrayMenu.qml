import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import Quickshell
import qs.services
import qs.components
import qs.theme
Rectangle {
    id:root
    width:280
    property real maximumHeight:540
    height:Math.min(maximumHeight,Math.max(78,activeHeight))
    property real activeHeight:78
    radius:18;color:Theme.surfaceSolid;antialiasing:true;border.width:1;border.color:Theme.withAlpha(Theme.text,.09)
    property bool inFooter:false
    opacity:Tray.open&&Tray.inFooter===inFooter?1:0;visible:opacity>0;enabled:Tray.open&&Tray.inFooter===inFooter;z:60
    Behavior on opacity {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
    Behavior on height {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
    HoverHandler {onHoveredChanged:hovered?Tray.enter("menu"):Tray.exit("menu")}
    Keys.onEscapePressed:Tray.close()
    Repeater {
        model:Tray.inFooter===root.inFooter?Tray.path:[]
        Item {
            id:level;required property var modelData;required property int index;anchors.fill:parent;visible:index===Tray.path.length-1
            QsMenuOpener {id:opener;menu:level.modelData.handle}
            onVisibleChanged:if(visible)root.activeHeight=column.implicitHeight+16
            Flickable {
                id: scroll
                anchors.fill: parent
                contentHeight: column.implicitHeight + 16
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
            ColumnLayout {
                id:column;x:8;y:8;width:parent.width-16;spacing:4
                onImplicitHeightChanged:if(level.visible)root.activeHeight=implicitHeight+16
                RowLayout {Layout.fillWidth:true;Layout.preferredHeight:34
                    IconButton {icon:"arrow_back";label:"Back";size:12;visible:level.index>0;onClicked:Tray.back()}
                    PanelText {Layout.fillWidth:true;Layout.leftMargin:8;text:level.modelData.title;font.pixelSize:13;font.weight:Font.Medium}
                    IconButton {icon:"close";label:"Close menu";size:12;onClicked:Tray.close()}
                }
                Repeater {
                    model:opener.children
                    AbstractButton {
                        id:entry;required property var modelData;Layout.fillWidth:true;Layout.preferredHeight:modelData.isSeparator?9:36
                        enabled:modelData.enabled&&!modelData.isSeparator;text:modelData.text.replace(/&&/g,"\u0001").replace(/&/g,"").replace(/\u0001/g,"&")
                        hoverEnabled:true;onClicked:Tray.activate(modelData)
                        background:Rectangle {radius:9;color:entry.hovered?Theme.withAlpha(Theme.text,.085):"transparent";Behavior on color {ColorAnimation {duration:Tokens.animFast}}Rectangle {anchors.centerIn:parent;width:parent.width-12;height:1;color:Theme.withAlpha(Theme.text,.08);visible:entry.modelData.isSeparator}}
                        contentItem:RowLayout {visible:!entry.modelData.isSeparator;spacing:10
                            Icon {icon:entry.modelData.checkState===Qt.Checked?"check":"";size:14;color:Theme.accent}
                            PanelText {Layout.fillWidth:true;text:entry.text;font.pixelSize:12;color:entry.enabled?Theme.text:Theme.subtext}
                            Icon {icon:"chevron_right";size:14;color:Theme.subtext;visible:entry.modelData.hasChildren}
                        }
                    }
                }
                PanelText {visible:!opener.children.values.length;Layout.margins:8;text:"Loading menu…";font.pixelSize:11;color:Theme.subtext}
            }
            }
        }
    }
}
