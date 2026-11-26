import QtQuick
import qs.theme

// Receives character counts only. Passwords remain in the native input.
Item {
    id:root
    property int length:0
    property real maximumWidth:184
    property real pitch:14
    property real dotSize:8
    property real animatedSpan:-1
    property color color:Theme.text
    readonly property bool springPositioned: animatedSpan >= 0
    implicitWidth: springPositioned ? Math.max(0, maximumWidth)
        : Math.min(Math.max(0,length)*pitch,Math.max(0,maximumWidth))
    implicitHeight:22
    clip: springPositioned
    Behavior on implicitWidth {enabled:!root.springPositioned&&!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animFast;reversingMode:SmoothedAnimation.Immediate}}
    function reconcile():void {
        const count=Math.max(0,length);
        while(dotsModel.count<count)dotsModel.append({dot:true});
        while(dotsModel.count>count)dotsModel.remove(dotsModel.count-1);
        if (!springPositioned) Qt.callLater(dots.positionViewAtEnd);
    }
    onLengthChanged:reconcile()
    Component.onCompleted:reconcile()
    ListModel {id:dotsModel}
    ListView {
        id:dots
        x:root.springPositioned ? (root.width + Math.min(root.animatedSpan, root.width))/2 - root.animatedSpan : 0
        width:root.springPositioned ? Math.max(root.width, root.length*root.pitch) : root.width
        height:root.height
        orientation:ListView.Horizontal
        interactive:false;clip:!root.springPositioned;model:dotsModel;boundsBehavior:Flickable.StopAtBounds
        onWidthChanged: if (!root.springPositioned) Qt.callLater(positionViewAtEnd)
        delegate:Item {
            id: dot
            property real inkOffset: 0
            width:root.pitch;height:22
            Rectangle {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: dot.inkOffset
                width: root.dotSize; height: width; radius: width / 2
                color: root.color; antialiasing: true
            }
        }
        add:Transition {ParallelAnimation {
            NumberAnimation {property:"opacity";from:0;to:1;duration:Tokens.animFast;easing.type:Easing.OutCubic}
            NumberAnimation {property:"scale";from:root.springPositioned?.72:.65;to:1;duration:Tokens.animMedium;easing.type:Easing.OutCubic}
            NumberAnimation {property:"inkOffset";from:root.springPositioned?2.5:0;to:0;duration:Tokens.animFast;easing.type:Easing.OutCubic}
        }}
        remove:Transition {ParallelAnimation {
            NumberAnimation {property:"opacity";to:0;duration:Tokens.animFast}
            NumberAnimation {property:"scale";to:.7;duration:Tokens.animFast;easing.type:Easing.InCubic}
            NumberAnimation {property:"inkOffset";to:root.springPositioned?2.5:0;duration:Tokens.animFast;easing.type:Easing.InQuad}
        }}
    }
}
