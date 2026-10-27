import QtQuick
import QtQuick.Controls
import qs.theme
import qs.services

Item {
    id: root

    property string icon: ""
    property string label: ""
    property real size: 16
    property color color: Theme.text
    property color background: "transparent"
    property int heldKey: 0
    readonly property bool pressed: enabled && (mouse.pressed || heldKey !== 0)

    signal clicked()

    implicitWidth: size + 16
    implicitHeight: size + 16
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: label || icon
    function pressKey(event): void {
        if(event.key===Qt.Key_Escape&&heldKey){heldKey=0;event.accepted=true;return;}
        if(!activeFocus||!enabled||![Qt.Key_Space,Qt.Key_Return,Qt.Key_Enter].includes(event.key))return;
        event.accepted=true;
        if(event.isAutoRepeat||heldKey)return;
        heldKey=event.key;Hints.hide(root);
        if(event.key!==Qt.Key_Space)clicked();
    }
    function releaseKey(event): void {
        if(event.isAutoRepeat){if(heldKey)event.accepted=true;return;}
        const key=heldKey;heldKey=0;
        if(!key||event.key!==key)return;
        event.accepted=true;
        if(key===Qt.Key_Space&&enabled&&activeFocus)clicked();
    }
    Keys.onPressed:event=>pressKey(event)
    Keys.onReleased:event=>releaseKey(event)
    onActiveFocusChanged:if(!activeFocus)heldKey=0
    onEnabledChanged:if(!enabled)heldKey=0
    onVisibleChanged:if(!visible)heldKey=0
    opacity: enabled ? 1 : 0.35

    Rectangle {
        anchors.fill: parent
        antialiasing: true
        radius: height / 2
        color: root.background
        border.width: root.activeFocus ? 1 : 0
        border.color: Theme.accent

        Rectangle {
            anchors.fill: parent
            antialiasing: true
            radius: parent.radius
            color: Theme.withAlpha(root.color, root.pressed ? 0.13 : mouse.containsMouse ? 0.065 : 0)
            Behavior on color { ColorAnimation { duration: Tokens.animFast } }
        }

        Behavior on color {
            ColorAnimation {
                duration: Tokens.animFast
            }

        }

    }

    Icon {
        anchors.centerIn: parent
        icon: root.icon
        size: root.size
        color: root.color
        Behavior on color { ColorAnimation { duration: Tokens.animFast } }
    }

    MouseArea {
        id: mouse

        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onEntered: Hints.show(root, root.label)
        onExited: Hints.hide(root)
        onPressed: Hints.hide(root)
        onClicked: root.clicked()
    }

    scale: pressMotion.value
    FrameSpring { id:pressMotion;owner:root;targetValue:root.pressed ? 0.96 : 1;pressFeedback:true;positionTolerance:.0002 }

}
