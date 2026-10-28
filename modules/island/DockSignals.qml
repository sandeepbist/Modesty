import QtQuick
import QtQuick.Shapes
import qs.services
import qs.theme

Item {
    id:root
    property real dockProgress:1
    property bool compactWifi:true
    readonly property real glyphScale:16/23
    readonly property real signalGap:8
    readonly property real wifiRight:13+(Math.max(22.85,badge.x+badge.implicitWidth)-13)*glyphScale
    readonly property real batteryX:wifiRight+signalGap
    readonly property real dockImplicitWidth:batteryX+19+5
    implicitWidth:26+(dockImplicitWidth-26)*dockProgress
    readonly property var network:Wireless.networks.find(n=>n.connected)??null
    readonly property string wifiState:!Wireless.available?"unavailable":(!Wireless.enabled||Wireless.hardwareEnabled===false)?"off":!network?"disconnected":!Number.isFinite(network.signalStrength)?"unknown":"known"
    readonly property real strength:wifiState==="known"?Math.max(0,Math.min(1,network.signalStrength)):0
    readonly property int arcs:wifiState==="known"?Math.ceil(strength*3):0
    readonly property string wifiText:wifiState==="known"?"Wi-Fi "+Wireless.connectedName+", "+Math.round(strength*100)+"% signal":"Wi-Fi "+wifiState
    readonly property string batteryText:SystemInfo.hasBattery?"Laptop battery "+Math.round(SystemInfo.batteryPercent)+"%"+(SystemInfo.charging?", plugged in":""):"Laptop battery "+SystemInfo.batteryState
    Item {
        objectName:"statusWifi"
        width:26;height:26
        opacity:root.compactWifi?1:root.dockProgress
        scale:root.glyphScale
    Shape {
        x:2;y:3;width:23;height:20
        preferredRendererType:Shape.CurveRenderer
        ShapePath {
            strokeWidth:1.7;capStyle:ShapePath.RoundCap;fillColor:"transparent"
            strokeColor:Theme.withAlpha(Theme.text,root.arcs>=3?1:.16)
            PathSvg {path:"M2 7 Q11 0 20 7"}
        }
        ShapePath {
            strokeWidth:1.7;capStyle:ShapePath.RoundCap;fillColor:"transparent"
            strokeColor:Theme.withAlpha(Theme.text,root.arcs>=2?1:.16)
            PathSvg {path:"M5 11 Q11 6 17 11"}
        }
        ShapePath {
            strokeWidth:1.7;capStyle:ShapePath.RoundCap;fillColor:"transparent"
            strokeColor:Theme.withAlpha(Theme.text,root.arcs>=1?1:.16)
            PathSvg {path:"M8 15 Q11 12.5 14 15"}
        }
        ShapePath {strokeColor:"transparent";fillColor:root.wifiState==="known"?Theme.text:Theme.withAlpha(Theme.text,.25);PathSvg {path:"M12 18 A1 1 0 1 1 10 18 A1 1 0 1 1 12 18"}}
        ShapePath {strokeWidth:1.5;strokeColor:["off","unavailable"].includes(root.wifiState)?Theme.text:"transparent";fillColor:"transparent";PathSvg {path:"M3 3 L19 19"}}
    }
    Text {id:badge;x:20;y:0;text:root.wifiState==="unknown"?"?":root.wifiState==="disconnected"?"×":root.wifiState==="unavailable"?"−":"";font.pixelSize:10;color:Theme.text}
    }
    Rectangle {
        objectName:"statusBattery"
        x:root.batteryX;y:9;width:17;height:8;radius:2;color:"transparent";border.width:.9;border.color:Theme.withAlpha(Theme.text,.7)
        opacity:root.dockProgress
        Rectangle {x:17;y:2.5;width:2;height:3;radius:.75;color:Theme.withAlpha(Theme.text,.6)}
        Rectangle {x:2;y:2;height:4;radius:.75;width:SystemInfo.hasBattery?13*Math.max(0,Math.min(1,SystemInfo.batteryPercent/100)):0;color:SystemInfo.batteryPercent<=20&&!SystemInfo.charging?Theme.red:Theme.text}
        Text {x:(parent.width-width)/2;y:(parent.height-height)/2;text:SystemInfo.hasBattery?(SystemInfo.charging?"ϟ":""):SystemInfo.batteryState==="absent"?"−":"?";font.pixelSize:8;color:Theme.text}
    }
    Accessible.role:Accessible.StaticText
    Accessible.name:wifiText+" · "+batteryText
}
