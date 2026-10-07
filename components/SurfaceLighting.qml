import QtQuick
import qs.theme

// Native edge light. Only real work animates continuously; hover is passive.
Item {
    id:root
    property real radius:16
    property bool active:true
    property bool focused:false
    property bool working:false
    property bool interactive:true
    property real phase:0
    property real acknowledgement:0
    property real position:working?.18+.64*phase:hover.hovered?Math.max(0,Math.min(1,hover.point.position.x/Math.max(1,width))):.5
    readonly property real strength:active?Math.max(acknowledgement,working?.72:focused?.48:hover.hovered?.36:.12):0
    opacity:strength
    Behavior on opacity {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutQuint}}
    Behavior on position {enabled:!root.working;SmoothedAnimation {velocity:-1;duration:Tokens.animMedium}}
    function acknowledge():void {if(active&&!Tokens.reducedMotion)completion.restart();}
    onWorkingChanged:if(!working)acknowledge()
    HoverHandler {id:hover;enabled:root.interactive&&root.active;blocking:false}
    SequentialAnimation on phase {
        running:root.active&&root.working&&root.visible&&!Tokens.reducedMotion
        loops:Animation.Infinite
        NumberAnimation {to:1;duration:1400;easing.type:Easing.InOutSine}
        NumberAnimation {to:0;duration:1400;easing.type:Easing.InOutSine}
    }
    SequentialAnimation {
        id:completion
        NumberAnimation {target:root;property:"acknowledgement";to:.7;duration:Tokens.animFast;easing.type:Easing.OutCubic}
        NumberAnimation {target:root;property:"acknowledgement";to:0;duration:Tokens.animSlow;easing.type:Easing.OutQuint}
    }
    Rectangle {
        x:root.radius;y:0;width:Math.max(0,parent.width-root.radius*2);height:1
        gradient:Gradient {orientation:Gradient.Horizontal;GradientStop {position:0;color:"transparent"}GradientStop {position:.5;color:Theme.withAlpha(Theme.text,.3)}GradientStop {position:1;color:"transparent"}}
    }
    Rectangle {
        width:Math.max(0,Math.min(parent.width-root.radius*2,parent.width*.38));height:1.5
        x:root.radius+Math.max(0,parent.width-root.radius*2-width)*root.position;y:0
        gradient:Gradient {orientation:Gradient.Horizontal;GradientStop {position:0;color:"transparent"}GradientStop {position:.5;color:Theme.accent}GradientStop {position:1;color:"transparent"}}
    }
}
