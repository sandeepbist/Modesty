import QtQuick
import QtQuick.Shapes
import qs.services
import qs.components
import qs.theme
Item {
    id:root
    width:26;height:26
    readonly property bool deviceShown:DeviceStatus.available
    readonly property bool batteryKnown:deviceShown&&DeviceStatus.batteryAvailable
    readonly property string glyph:deviceShown?DeviceStatus.icon:SystemInfo.wifiEnabled?"wifi":"wifi_off"
    readonly property var network:Wireless.networks.find(n=>n.connected)??null
    readonly property bool levelKnown:batteryKnown||(!deviceShown&&!!network)
    property real level:batteryKnown?DeviceStatus.battery:!deviceShown&&network?network.signalStrength:0
    readonly property color ringColor:root.batteryKnown&&DeviceStatus.low?Theme.red:Theme.text
    Behavior on level {NumberAnimation {duration:Tokens.reducedMotion?0:420;easing.type:Easing.OutCubic}}
    Shape {
        anchors.fill:parent
        preferredRendererType:Shape.CurveRenderer
        ShapePath {
            strokeWidth:1.7;strokeColor:Theme.withAlpha(Theme.text,.18);fillColor:"transparent";capStyle:ShapePath.RoundCap
            PathAngleArc {centerX:13;centerY:13;radiusX:11.25;radiusY:11.25;startAngle:150;sweepAngle:240}
        }
        ShapePath {
            strokeWidth:1.7;strokeColor:root.levelKnown?root.ringColor:"transparent";fillColor:"transparent";capStyle:ShapePath.RoundCap
            PathAngleArc {centerX:13;centerY:13;radiusX:11.25;radiusY:11.25;startAngle:150;sweepAngle:Math.max(0,Math.min(240,240*root.level))}
            Behavior on strokeColor {ColorAnimation {duration:Tokens.animMedium}}
        }
    }
    Repeater {
        model:[54,78,102,126]
        Rectangle {
            required property int modelData
            width:1.8;height:1.8;radius:.9;antialiasing:true
            x:13+11.25*Math.cos(modelData*Math.PI/180)-width/2
            y:13+11.25*Math.sin(modelData*Math.PI/180)-height/2
            color:Theme.withAlpha(Theme.text,root.levelKnown?.78:.3)
            Behavior on color {ColorAnimation {duration:Tokens.animMedium}}
        }
    }
    CompactGlyph {
        anchors.centerIn:parent;glyph:"wifi";size:16
        opacity:root.glyph==="wifi"?1:0;visible:opacity>0
        Behavior on opacity {NumberAnimation {duration:Tokens.reducedMotion?0:160;easing.type:Easing.OutCubic}}
    }
    Repeater {model:["wifi_off","earbuds","headphones"]
        Icon {
            required property string modelData
            readonly property bool selected:root.glyph===modelData
            icon:modelData;size:modelData==="earbuds"?17:14;x:(root.width-width)/2;y:(root.height-height)/2+(selected?0:3)
            color:Theme.text;opacity:selected?1:0;visible:opacity>0
            Behavior on opacity {NumberAnimation {duration:Tokens.reducedMotion?0:160;easing.type:Easing.OutCubic}}
            Behavior on y {NumberAnimation {duration:Tokens.reducedMotion?0:180;easing.type:Easing.OutCubic}}
        }
    }
    HoverHandler {onHoveredChanged:{if(hovered)Hints.show(root,root.deviceShown?DeviceStatus.name+(DeviceStatus.batteryAvailable?DeviceStatus.low?" · Low battery":"":" · Battery unavailable"):Wireless.connectedName||"Control center");else Hints.hide(root);}}
    Accessible.role:Accessible.StaticText
    Accessible.name:deviceShown?DeviceStatus.name+(batteryKnown?DeviceStatus.low?", low battery":"":", battery unavailable"):"Wi-Fi status"
}
