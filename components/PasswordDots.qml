import QtQuick
import qs.theme

// Receives character counts only. Passwords remain in the native input.
Item {
    id:root
    property int length:0
    property real maximumWidth:184
    property color color:Theme.text
    implicitWidth:Math.min(Math.max(0,length)*14,Math.max(0,maximumWidth))
    implicitHeight:22
    Behavior on implicitWidth {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animFast;reversingMode:SmoothedAnimation.Immediate}}
    function reconcile():void {
        const count=Math.max(0,length);
        while(dotsModel.count<count)dotsModel.append({dot:true});
        while(dotsModel.count>count)dotsModel.remove(dotsModel.count-1);
        Qt.callLater(()=>dots.positionViewAtEnd());
    }
    onLengthChanged:reconcile()
    Component.onCompleted:reconcile()
    ListModel {id:dotsModel}
    ListView {
        id:dots;anchors.fill:parent;orientation:ListView.Horizontal
        interactive:false;clip:true;model:dotsModel;boundsBehavior:Flickable.StopAtBounds
        delegate:Item {
            width:14;height:22
            Rectangle {anchors.centerIn:parent;width:8;height:8;radius:4;color:root.color;antialiasing:true}
        }
        add:Transition {ParallelAnimation {
            NumberAnimation {property:"opacity";from:0;to:1;duration:Tokens.animFast;easing.type:Easing.OutCubic}
            NumberAnimation {property:"scale";from:.65;to:1;duration:Tokens.animMedium;easing.type:Easing.OutCubic}
        }}
        remove:Transition {ParallelAnimation {
            NumberAnimation {property:"opacity";to:0;duration:Tokens.animFast}
            NumberAnimation {property:"scale";to:.7;duration:Tokens.animFast;easing.type:Easing.InCubic}
        }}
    }
}
