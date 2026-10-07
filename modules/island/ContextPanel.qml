import QtQuick
import QtQuick.Layouts
import qs.components
import qs.services
import qs.theme
Item {
    id:root
    property string kind:Context.kind
    property string label:Context.label
    property string icon:Context.icon
    property real value:Context.value
    function diagnostics(): var {return {kind:root.kind,label:root.label,value:root.value,active:Context.active};}
    RowLayout {
        visible:["volume","brightness"].includes(root.kind)
        anchors.fill:parent;anchors.leftMargin:14;anchors.rightMargin:14;spacing:10
        Icon {icon:root.icon;size:16;color:Theme.accent}
        Rectangle {
            visible:["volume","brightness"].includes(root.kind);Layout.fillWidth:true;Layout.preferredHeight:4;radius:2;color:Theme.withAlpha(Theme.text,.13)
            Rectangle {width:parent.width*Math.min(1,root.value);height:4;radius:2;color:Theme.accent;Behavior on width {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:90;reversingMode:SmoothedAnimation.Immediate}}}
        }
        PanelText {visible:["volume","brightness"].includes(root.kind);Layout.preferredWidth:37;text:Math.round(root.value*100)+"%";font.family:Tokens.clockFont;font.pixelSize:12;font.weight:Tokens.pillTextWeight;font.features:({tnum:1});color:Theme.subtext;horizontalAlignment:Text.AlignRight}
    }
    RowLayout {
        anchors.fill:parent;anchors.leftMargin:16;anchors.rightMargin:16;spacing:10
        visible:!["volume","brightness","workspace","welcome"].includes(root.kind)
        Icon {icon:root.icon;size:17;color:Theme.accent}
        PanelText {Layout.fillWidth:true;text:root.label;font.pixelSize:13;font.weight:Font.Medium;horizontalAlignment:Text.AlignHCenter}
        Icon {visible:root.kind==="audiooutput";icon:"chevron_right";size:13;color:Theme.subtext}
    }
}
