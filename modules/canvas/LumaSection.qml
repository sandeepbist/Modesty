import QtQuick
import qs.theme

// Keep content at its final size while revealing or retiring its vertical space.
Item {
    id: root
    default property alias contents: body.data
    property bool expanded: true
    property bool animate: true
    property real reveal: expanded ? 1 : 0
    property real targetHeight:-1
    readonly property real naturalHeight:targetHeight>=0?targetHeight:body.childrenRect.height
    height: naturalHeight * reveal
    visible: reveal > .001
    enabled: expanded
    clip: reveal < .999
    opacity: Math.min(1, reveal * 3)
    Behavior on reveal {
        enabled: root.animate&&!Tokens.reducedMotion
        SmoothedAnimation {velocity:-1;duration:root.expanded?Tokens.animSlow:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}
    }
    Item {id:body;width:root.width;height:childrenRect.height}
}
