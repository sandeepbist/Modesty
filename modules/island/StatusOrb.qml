import QtQuick
import QtQuick.Shapes
import qs.services
import qs.components
import qs.theme
Item {
    id:root
    property real dockProgress:0
    property bool deviceOnly:false
    readonly property real dockImplicitWidth:signals.dockImplicitWidth
    implicitWidth:deviceOnly?26:26+(dockImplicitWidth-26)*dockProgress
    width:implicitWidth;height:26
    readonly property bool laptopKnown:SystemInfo.hasBattery&&Number.isFinite(SystemInfo.batteryPercent)
    readonly property string laptopState:SystemInfo.batteryState??(SystemInfo.hasBattery?"known":"absent")
    readonly property bool deviceShown:DeviceStatus.available
    readonly property bool batteryKnown:deviceShown?DeviceStatus.batteryAvailable:root.laptopKnown
    readonly property string glyph:deviceShown?DeviceStatus.icon:SystemInfo.wifiEnabled?"wifi":"wifi_off"
    readonly property var network:Wireless.networks.find(n=>n.connected)??null
    readonly property bool levelKnown:batteryKnown
    property real level:batteryKnown?(deviceShown?DeviceStatus.battery:SystemInfo.batteryPercent/100):0
    readonly property color ringColor:batteryKnown&&(deviceShown?DeviceStatus.low:SystemInfo.batteryPercent<=20)?Theme.red:Theme.text
    readonly property real wifiStrength:Wireless.available&&SystemInfo.wifiEnabled&&network&&Number.isFinite(network.signalStrength)?Math.max(0,Math.min(1,network.signalStrength)):0
    readonly property int wifiDots:Math.ceil(wifiStrength*4)
    readonly property string batteryText:root.laptopKnown?"Laptop battery "+Math.round(SystemInfo.batteryPercent)+"%"+(SystemInfo.charging?", plugged in":""):"Laptop battery unavailable"
    readonly property string wifiText:!Wireless.available?"Wi-Fi unavailable":!SystemInfo.wifiEnabled?"Wi-Fi off":network?"Wi-Fi connected"+(Wireless.connectedName?" to "+Wireless.connectedName:"")+", "+Math.round(wifiStrength*100)+"% signal":"Wi-Fi disconnected"
    readonly property string statusText:(deviceShown?DeviceStatus.name+(batteryKnown?", "+Math.round(DeviceStatus.battery*100)+"% battery"+(DeviceStatus.low?", low battery":""):", battery unavailable")+" · ":"")+batteryText+" · "+wifiText
    Behavior on level {NumberAnimation {duration:Tokens.reducedMotion?0:420;easing.type:Easing.OutCubic}}
    Shape {
        opacity:1-root.dockProgress
        width:26;height:26
        preferredRendererType:Shape.CurveRenderer
        ShapePath {
            strokeWidth:1.7;strokeColor:Theme.withAlpha(Theme.text,.18);fillColor:"transparent";capStyle:ShapePath.RoundCap
            PathAngleArc {centerX:13;centerY:13;radiusX:11.25;radiusY:11.25;startAngle:170;sweepAngle:200}
        }
        ShapePath {
            strokeWidth:1.7;strokeColor:root.levelKnown?root.ringColor:"transparent";fillColor:"transparent";capStyle:ShapePath.RoundCap
            PathAngleArc {centerX:13;centerY:13;radiusX:11.25;radiusY:11.25;startAngle:170;sweepAngle:Math.max(0,Math.min(200,200*root.level))}
            Behavior on strokeColor {ColorAnimation {duration:Tokens.animMedium}}
        }
    }
    Repeater {
        model:[54,78,102,126]
        Rectangle {
            required property int modelData
            required property int index
            opacity:1-root.dockProgress
            width:1.8;height:1.8;radius:.9;antialiasing:true
            x:13+11.25*Math.cos(modelData*Math.PI/180)-width/2
            y:13+11.25*Math.sin(modelData*Math.PI/180)-height/2
            color:Theme.withAlpha(Theme.text,index>=4-root.wifiDots?.78:.3)
            Behavior on color {ColorAnimation {duration:Tokens.animMedium}}
        }
    }
    Repeater {model:["earbuds","headphones"]
        Icon {
            required property string modelData
            readonly property bool selected:root.glyph===modelData
            icon:modelData;size:modelData==="earbuds"?17:14;x:(26-width)/2;y:(root.height-height)/2
            color:Theme.text;opacity:selected?(root.deviceOnly?1:1-root.dockProgress):0;visible:opacity>0
        }
    }
    Text {anchors.horizontalCenter:parent.horizontalCenter;y:20;text:root.batteryKnown?Math.round(root.level*100)+"%":"?";font.pixelSize:7;color:Theme.text;opacity:root.dockProgress;visible:root.deviceOnly}
    DockSignals {id:signals;visible:!root.deviceOnly;anchors.fill:parent;dockProgress:root.dockProgress;compactWifi:!root.deviceShown}
    Accessible.role:Accessible.StaticText
    Accessible.name:statusText
}
