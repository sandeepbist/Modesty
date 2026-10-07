import QtQuick
import qs.services
import qs.theme

Rectangle {
    id:root
    property real maximumY:Math.max(8,(parent?.height||0)-height-8)
    property point heldPosition:Qt.point(8,8)
    property string heldText:""
    property Item heldTarget:null
    readonly property bool requested:Hints.shown&&!!Hints.target&&Hints.target.visible&&Hints.target.enabled&&!!Window.window&&Hints.target.Window.window===Window.window
    function reconcile():void {
        fade.stop();
        if(requested){
            const point=Hints.target.mapToItem(parent,Hints.target.width/2,Hints.target.height);
            if(!Number.isFinite(point.x)||!Number.isFinite(point.y))return;
            // Never move a still-visible outgoing tooltip to a new target.
            if(heldTarget!==Hints.target)opacity=0;
            heldText=Hints.text;heldTarget=Hints.target;
            const bubbleWidth=Math.min(320,Math.max(24,parent.width-16),label.implicitWidth+22);
            heldPosition=Qt.point(Math.round(Math.max(8,Math.min(parent.width-bubbleWidth-8,point.x-bubbleWidth/2))),Math.round(Math.max(8,Math.min(maximumY,point.y+7))));
        }
        fade.to=requested?1:0;fade.restart();
    }
    onRequestedChanged:reconcile()
    width:Math.min(320,Math.max(24,(parent?.width||0)-16),label.implicitWidth+22)
    height:30;radius:10;x:heldPosition.x;y:heldPosition.y;z:100
    color:Theme.surfaceSolid;border.width:1;border.color:Theme.withAlpha(Theme.text,.1)
    opacity:0;visible:opacity>0
    PanelText {id:label;anchors.centerIn:parent;width:parent.width-22;text:root.heldText;font.pixelSize:Tokens.captionSize}
    NumberAnimation {id:fade;target:root;property:"opacity";duration:Tokens.animFast;easing.type:Easing.OutCubic}
}
