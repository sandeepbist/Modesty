pragma Singleton
import QtQuick
import Quickshell
Singleton {
    id:root
    function isAirpods(device):bool {return /airpods/i.test((device?.deviceName||"")+" "+(device?.name||""));}
    readonly property var connected:Radio.devices.filter(d=>d.connected)
    readonly property var device:connected.find(d=>isAirpods(d))||connected.find(d=>/head|audio/.test(d.icon||""))||null
    readonly property bool available:Preferences.deviceIndicator&&!!device
    readonly property string name:device?.name||"Headphones"
    readonly property string icon:isAirpods(device)?"earbuds":"headphones"
    readonly property bool batteryAvailable:!!device?.batteryAvailable&&Number.isFinite(device?.battery)&&device.battery>=0&&device.battery<=1
    readonly property real battery:batteryAvailable?device.battery:0
    readonly property bool low:batteryAvailable&&battery<=.20
    property string previousDevice:""
    property bool wasLow:false
    onLowChanged:checkBattery()
    onDeviceChanged:checkBattery()
    function checkBattery():void {
        const id=device?.address||"";
        if(id!==previousDevice){previousDevice=id;wasLow=false;}
        if(low&&!wasLow&&Context.ready&&Preferences.contextDevices)Context.show("connection",name+" · Low battery",icon,0);
        wasLow=low;
    }
    property string outputName:""
    Timer {id:outputDelay;interval:450;onTriggered:{
        const name=Audio.sink?.description||Audio.sink?.name||"";
        if(Context.ready&&Preferences.contextDevices&&name&&root.outputName&&name!==root.outputName)Context.show("audiooutput",name,/bluez/i.test(Audio.sink?.name||"")?root.icon:"speaker",0);
        if(name)root.outputName=name;
    }}
    Connections {target:Audio;function onSinkChanged(){outputDelay.restart();}}
    Component.onCompleted:outputDelay.start()
}
