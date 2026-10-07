import QtQuick
import qs.theme

Item {
    id:root
    property string kind:"working"
    property bool running:true
    implicitWidth:16;implicitHeight:16
    ActivityPulse {
        anchors.centerIn:parent;width:14;height:14
        opacity:root.kind==="working"?1:0;visible:opacity>0;running:root.running&&opacity>0
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
    }
    Repeater {model:["waiting","completed","error","interrupted"]
        Icon {
            id:stateIcon
            required property string modelData
            anchors.centerIn:parent;size:15
            icon:modelData==="waiting"?"chat_bubble":modelData==="completed"?"check":modelData==="interrupted"?"pause":"error"
            color:modelData==="completed"?Theme.accent:modelData==="error"?Theme.red:Theme.yellow
            opacity:root.kind===modelData?1:0;visible:opacity>0
            transform:Translate {y:3*(1-stateIcon.opacity)}
            Behavior on opacity {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
        }
    }
}
