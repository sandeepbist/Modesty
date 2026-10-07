import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.services
import qs.components
import qs.theme

FocusScope {
    id: root
    property int selected: 0
    property string pending: ""
    readonly property var actions: [
        {icon:"lock", label:"Lock", action:"lock"},
        {icon:"dark_mode", label:"Sleep", action:"suspend"},
        {icon:"logout", label:"Log out", action:"logout"},
        {icon:"restart_alt", label:"Restart", action:"reboot"},
        {icon:"power_settings_new", label:"Power off", action:"poweroff"}
    ]
    function measure():void { IslandState.measurePanel("power", body.implicitHeight + Preferences.innerPadding * 2); }
    function choose(index:int):void {
        selected=index;
        const action=actions[index].action;
        if(action==="lock" || action==="suspend") { action==="suspend" ? Session.requestSleep("suspend") : Session.lock(false); return; }
        if(pending===action) { SystemInfo.action(action, ""); pending=""; }
        else pending=action;
    }
    function diagnostics():var { return {selected,pending,height:body.implicitHeight}; }
    Component.onCompleted:Qt.callLater(measure)
    Keys.onLeftPressed:{selected=Math.max(0,selected-1);pending="";}
    Keys.onRightPressed:{selected=Math.min(actions.length-1,selected+1);pending="";}
    Keys.onReturnPressed:choose(selected)
    Keys.onEnterPressed:choose(selected)
    Keys.onEscapePressed:event=>{if(pending)pending="";else event.accepted=false;}
    ColumnLayout {
        id:body;anchors.fill:parent;spacing:0
        onImplicitHeightChanged:root.measure()
        Item {
            Layout.fillWidth:true;implicitHeight:64
            Rectangle {
                x:root.selected*(parent.width+4)/5
                width:(parent.width-16)/5;height:64;radius:14
                color:Theme.withAlpha(root.pending?Theme.red:Theme.text,.055)
                border.width:1;border.color:Theme.withAlpha(root.pending?Theme.red:Theme.accent,root.pending?.35:.25)
                Behavior on x {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animFast;reversingMode:SmoothedAnimation.Immediate}}
                Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}
            }
            Row {
                anchors.fill:parent;spacing:4
                Repeater {
                    model:root.actions
                    AbstractButton {
                        id:button;required property var modelData;required property int index
                        width:(body.width-16)/5;height:64
                        text:modelData.label;Accessible.name:text
                        hoverEnabled:true;scale:pressed?.96:1
                        Behavior on scale {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                        onHoveredChanged:if(hovered&&!root.pending)root.selected=index
                        onClicked:root.choose(index)
                        HoverHandler {cursorShape:Qt.PointingHandCursor}
                        contentItem:Column {
                            spacing:8
                            topPadding:10
                            Icon {anchors.horizontalCenter:parent.horizontalCenter;icon:button.modelData.icon;size:20;color:root.pending===button.modelData.action?Theme.red:root.selected===button.index?Theme.text:Theme.subtext;Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                            PanelText {width:parent.width;text:button.text;font.pixelSize:12;font.weight:Font.Medium;horizontalAlignment:Text.AlignHCenter;color:root.selected===button.index?Theme.text:Theme.subtext}
                        }
                        background:Rectangle {radius:14;color:"transparent";border.width:button.activeFocus?1:0;border.color:Theme.accent}
                    }
                }
            }
        }
        Item {
            Layout.fillWidth:true;Layout.preferredHeight:amount*44;Layout.topMargin:amount*12
            property real amount:root.pending?1:0
            visible:amount>0;opacity:amount;clip:true;enabled:!!root.pending
            Behavior on amount {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}}
            Rectangle {width:parent.width;height:1;color:Theme.withAlpha(Theme.text,.07)}
            RowLayout {
                y:10;width:parent.width;spacing:8
                PanelText {Layout.fillWidth:true;text:root.pending?root.actions.find(a=>a.action===root.pending).label+"?":"";font.pixelSize:13;font.weight:Font.Medium}
                IconButton {icon:"close";size:16;label:"Cancel";onClicked:root.pending=""}
                ActionButton {text:"Confirm";implicitHeight:32;onClicked:root.choose(root.selected)}
            }
        }
    }
}
