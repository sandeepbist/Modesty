#!/usr/bin/env python3
from pathlib import Path
from unittest.mock import patch
import tempfile
import qml

qml.run('''import QtQuick
import Quickshell
import qs.services
ShellRoot {Timer {interval:50;running:true;onTriggered:{try{
 function check(ok,label){if(!ok)throw new Error(label);}
 for(const [device,state] of [[null,"unknown"],[{ready:false,isPresent:true,isLaptopBattery:true,percentage:.5},"unknown"],[{ready:true,isPresent:false,isLaptopBattery:true,percentage:0},"absent"],[{ready:true,isPresent:true,isLaptopBattery:false,percentage:1},"absent"],[{ready:true,isPresent:true,isLaptopBattery:true,percentage:NaN},"unknown"],[{ready:true,isPresent:true,isLaptopBattery:true,percentage:Infinity},"unknown"],[{ready:true,isPresent:true,isLaptopBattery:true,percentage:0},"known"],[{ready:true,isPresent:true,isLaptopBattery:true,percentage:1},"known"]])check(SystemInfo.batteryStatus(device)===state,"Battery validity "+state);
 console.log("DOCK BATTERY VALIDITY PASS");Qt.quit();
}catch(e){console.error(e);Qt.exit(1);}}}}
''','DOCK BATTERY VALIDITY PASS')

SOURCE='''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
ShellRoot {
 id:root
 property int activations:0
 property QtObject first:QtObject {property string name:"one";property var activeWorkspace:null}
 property QtObject second:QtObject {property string name:"two";property var activeWorkspace:null}
 property var named
 Component {id:workspace;QtObject {property int id:0;property string name:"";property var monitor;property bool urgent:false;function activate(){root.activations++;}}}
 FloatingWindow {visible:true;implicitWidth:400;implicitHeight:150
  Island.WorkspaceMarks {id:marks;monitor:root.first;width:42;height:35;workspaces:[]}
  Island.DockSignals {id:signals;y:50;width:68;height:26}
 }
 TestCase {id:input;when:false}
 function check(ok,label){if(!ok)throw new Error(label);}
 Timer {interval:80;running:true;onTriggered:{try{
  root.named=workspace.createObject(root,{id:-1337,name:"design",monitor:first});
  const list=[root.named,workspace.createObject(root,{id:-99,name:"special",monitor:first}),workspace.createObject(root,{id:-98,name:"special:music",monitor:first}),workspace.createObject(root,{id:2,name:"2",monitor:second})];
  for(let i=1;i<=8;i++)list.push(workspace.createObject(root,{id:i,name:String(i),monitor:first}));
  marks.workspaces=list;root.first.activeWorkspace=list[list.length-1];marks.monitor=null;marks.monitor=first;for(let i=0;i<50&&marks.contentX===0;i++)input.wait(10);
  check(marks.members.length===9&&marks.members.includes(named),"Named workspace filtered or special leaked");
  check(marks.activeIndex===8&&marks.contentX>0,"Active mark remains clipped");
  const buttons=marks.contentItem.children.filter(c=>c instanceof AbstractButton);
  const button=buttons.find(b=>b.modelData===named);check(!!button,"Named workspace action missing");button.forceActiveFocus();input.keyClick(Qt.Key_Space);check(activations===1,"Keyboard workspace action missing");
  marks.workspaces=[];marks.activate(named);check(activations===1,"Removed workspace activated");
  marks.monitor=null;marks.workspaces=list;check(marks.members.length===0,"Missing monitor leaked workspaces");
  marks.monitor=second;check(marks.members.length===1,"Monitor move kept old membership");
  for(const [available,enabled,network,state,arcs] of [[false,true,null,"unavailable",0],[true,false,null,"off",0],[true,true,null,"disconnected",0],[true,true,{connected:true,signalStrength:NaN},"unknown",0],[true,true,{connected:true,signalStrength:0},"known",0],[true,true,{connected:true,signalStrength:.2},"known",1],[true,true,{connected:true,signalStrength:.6},"known",2],[true,true,{connected:true,signalStrength:1},"known",3]]){
   Wireless.available=available;Wireless.enabled=enabled;Wireless.networks=network?[network]:[];
   check(signals.wifiState===state&&signals.arcs===arcs,"Wi-Fi semantics "+state+" "+arcs);
  }
  Wireless.hardwareEnabled=false;check(signals.wifiState==="off","Hardware-disabled Wi-Fi presented as connected");Wireless.hardwareEnabled=true;
  check(signals.batteryText.includes("unknown"),"Unknown battery fabricated percentage");SystemInfo.batteryState="absent";check(signals.batteryText.includes("absent"),"Absent battery not distinct");SystemInfo.hasBattery=true;SystemInfo.batteryState="known";SystemInfo.batteryPercent=0;check(signals.batteryText.includes("0%"),"Known zero battery hidden");
  console.log("DOCK DATA PASS");Qt.quit();
 }catch(e){console.error(e);Qt.exit(1);}}}
}
'''
with tempfile.TemporaryDirectory(prefix='modesty-dock-data-') as d:
    w=Path(d)
    for name in ('components','modules','assets','theme','scripts'):(w/name).symlink_to(qml.ROOT/name)
    (w/'services').mkdir()
    for f in (qml.ROOT/'services').iterdir():
        if f.name not in ('Wireless.qml','SystemInfo.qml'):(w/'services'/f.name).symlink_to(f)
    stubs={'Wireless':'property bool available:true;property bool hardwareEnabled:true;property bool enabled:true;property var networks:[];property string connectedName:"Fixture";', 'SystemInfo':'property string wallpaper:"";property string lockWallpaper:"";property var wallpapers:[];property bool hasBattery:false;property string batteryState:"unknown";property real batteryPercent:NaN;property bool charging:false;'}
    for name,body in stubs.items():(w/'services'/f'{name}.qml').write_text('pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {'+body+'}')
    with patch.object(qml,'ROOT',w):qml.run(SOURCE,'DOCK DATA PASS')
