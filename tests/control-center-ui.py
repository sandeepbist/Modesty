#!/usr/bin/env python3
"""Exercise the production control center and performance rows offscreen."""
from qml import run

FOOTER = '''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    id:test
    property int phase:0
    property real withoutFooter:0
    property var custom:[{id:"wifi",x:0,y:0,w:3,h:1}]
    FloatingWindow {
        visible:true;implicitWidth:700;implicitHeight:800
        Island.ControlCenter {id:center;width:Preferences.controlsWidth-Preferences.innerPadding*2;height:ControlLayout.panelHeight-Preferences.innerPadding*2}
    }
    TestCase {id:input;when:false}
    function check(value,message) {if(!value)throw new Error(message);}
    function child(name) {const item=input.findChild(center,name);check(!!item,"Missing "+name);return item;}
    Component.onCompleted: {
        Preferences.set("motion","instant");Theme.setMode("TEST_MODE");
        Preferences.footerTray=false;Preferences.footerSettings=true;Preferences.footerPerformance=true;
        IslandState.openMenu("quicksettings");
    }
    Timer {id:steps;interval:160;running:true;repeat:false;onTriggered:{try {
        const footer=child("controlFooter"),settings=child("footerSettings"),performance=child("footerPerformance");
        if(phase===0) {
            check(Theme.mode==="TEST_MODE","Requested footer color mode not active");
            check(footer.visible&&footer.enabled&&ControlLayout.footerShown,"Default footer unavailable");
            check(settings.text==="Settings"&&performance.text==="Performance"&&settings.x<performance.x,"Footer labels/order wrong");
            check(settings.height===38&&performance.height===38,"Footer action height changed");
            check(settings.width>100&&performance.width>100&&performance.x+performance.width<=center.width+.1,"Actions do not share footer width");
            settings.forceActiveFocus();check(settings.activeFocus&&settings.background.border.width===1,"Settings has no visible native focus");
            input.keyClick(Qt.Key_Tab);check(performance.activeFocus,"Tab does not reach Performance");
            input.keyClick(Qt.Key_Space);
            check(IslandState.menu==="performance","Keyboard Performance route failed");
        } else if(phase===1) {
            check(!footer.enabled,"Detail leaves footer interactive");
            IslandState.openMenu("quicksettings");
        } else if(phase===2) {
            input.mouseClick(settings,settings.width/2,settings.height/2);
        } else if(phase===3) {
            check(IslandState.settingsOpen&&IslandState.menu==="none","Click Settings route failed");
            IslandState.settingsOpen=false;IslandState.openMenu("quicksettings");
            settings.forceActiveFocus();input.keyClick(Qt.Key_Return);
        } else if(phase===4) {
            check(IslandState.settingsOpen,"Keyboard Settings route failed");
            IslandState.settingsOpen=false;IslandState.openMenu("quicksettings");
        } else if(phase===5) {
            input.mouseClick(performance,performance.width/2,performance.height/2);
            check(IslandState.menu==="performance","Click Performance route failed");
            IslandState.openMenu("quicksettings");Preferences.footerSettings=false;
        } else if(phase===6) {
            check(!settings.visible&&performance.visible&&Math.abs(performance.width-center.width)<1,"Hidden Settings reserves space");
            Preferences.footerSettings=true;Preferences.footerPerformance=false;
        } else if(phase===7) {
            check(settings.visible&&!performance.visible&&Math.abs(settings.width-center.width)<1,"Hidden Performance reserves space");
            Preferences.footerSettings=false;
        } else if(phase===8) {
            check(!ControlLayout.footerShown&&!footer.visible&&!footer.enabled,"Empty footer remains visible");
            withoutFooter=ControlLayout.panelHeight;
            Preferences.footerTray=true;
            check(ControlLayout.footerShown===(Tray.items.length>0),"Tray visibility does not follow actual items");
            Preferences.footerTray=false;Preferences.footerSettings=true;
            check(ControlLayout.panelHeight===withoutFooter+48,"Footer allocation differs from 48px");
            Preferences.footerVisible=false;
        } else if(phase===9) {
            check(!footer.visible&&!ControlLayout.footerShown&&ControlLayout.panelHeight===withoutFooter,"Global footer toggle leaves ghost space");
            ControlLayout.items=custom;Preferences.footerVisible=true;
        } else if(phase===10) {
            check(ControlLayout.footerShown&&footer.visible,"Custom layout lost enabled footer");
            check(JSON.stringify(ControlLayout.items)===JSON.stringify(custom),"Footer mutated custom layout");
            center.width=256;
        } else if(phase===11) {
            const label=child("footerSettingsLabel");
            check(label.mapToItem(settings,0,0).x>=0&&label.mapToItem(settings,label.width,0).x<=settings.width,"Narrow footer label escapes action");
            Preferences.footerVisible=false;
        } else if(phase===12) {
            check(!ControlLayout.footerShown&&!footer.visible,"Custom layout creates Notes fallback");
            const height=ControlLayout.panelHeight;
            ControlLayout.items=custom.concat([{id:"notes",x:3,y:0,w:1,h:1}]);
            check(ControlLayout.panelHeight===height&&!ControlLayout.footerShown,"Notes tile changes footer allocation");
            console.log("CONTROL FOOTER TEST_MODE PASS");Qt.quit();return;
        }
        phase++;steps.restart();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

PERFORMANCE = '''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    id:test
    property int phase:0
    property string longName:"nvme-device-with-a-very-long-readable-name"
    property string longPath:"/home/example/a/very/long/filesystem/mount/path"
    property var savedHistory
    property var savedSample
    FloatingWindow {
        visible:true;implicitWidth:700;implicitHeight:750
        Island.PerformanceMenu {id:panel;width:TEST_WIDTH;height:510}
    }
    TestCase {id:input;when:false}
    function check(value,message) {if(!value)throw new Error(message);}
    function child(name) {const item=input.findChild(panel,name);check(!!item,"Missing "+name);return item;}
    function near(actual,expected,message) {check(Math.abs(actual-expected)<.01,message+" actual="+actual);}
    function known() {return {cpu:.17,memoryUsed:1073741824,memoryTotal:4294967296,download:2097152,upload:1024,
        diskIo:[{name:longName,busy:.08,read:1048576,write:2048},{name:"sda",busy:.02,read:24576,write:0}],
        disks:[{path:"/",used:1073741824,total:4294967296},{path:longPath,used:2147483648,total:4294967296}]};}
    function walk(item) {let items=[item];for(const child of item.children||[])items=items.concat(walk(child));return items;}
    function geometry() {
        for(const item of walk(child("performanceScroll"))) {
            if(!item.visible||item.width<=0||item.height<=0)continue;
            check(Number.isFinite(item.x)&&Number.isFinite(item.y)&&Number.isFinite(item.width),"Invalid metric geometry "+item.objectName);
            if(item.text!==undefined)check(item.width<=panel.width+.1,"Metric exceeds narrow panel "+item.objectName);
        }
        check(child("driveName-"+longName).truncated&&child("driveName-"+longName).text===longName,"Long device label did not elide while retaining full text");
        check(child("storagePath-"+longPath).text===longPath,"Actual filesystem path missing");
    }
    Component.onCompleted: {Preferences.set("motion","instant");Theme.setMode("TEST_MODE");IslandState.openMenu("performance");}
    Timer {id:steps;interval:180;running:true;repeat:false;onTriggered:{try {
        const scroll=child("performanceScroll");
        if(phase===0) {
            check(Preferences.preview&&!child("performanceCollector").running,"Preview started live collector");
            check(Theme.mode==="TEST_MODE","Requested color mode not active");
            check(child("CPUPercent").text==="—"&&child("MemoryPercent").text==="—","Unknown percentages show data");
            check(child("downloadRate").text==="—/s"&&child("performanceStatus").visible&&!child("performanceLive").visible,"Loading state missing");
            panel.ingest(known());
        } else if(phase===1) {
            check(panel.deviceNames.length===2&&panel.diskPaths.length===2,"Multiple drives/filesystems lost");
            check(child("CPUPercent").text==="17"&&child("MemoryPercent").text==="25","Known percentages wrong");
            check(child("CPUDetail").text==="All cores"&&child("MemoryDetail").text==="1.0 GiB / 4.0 GiB","Summary detail missing");
            check(child("driveBusy-"+longName).text==="8% active"&&child(longName+"-read").text==="1.0 MiB/s"&&child(longName+"-write").text==="2.0 KiB/s","Disk readings missing");
            check(child("sda-read").text==="24.0 KiB/s"&&child("sda-write").text==="0 B/s","Second disk readings missing");
            check(child("downloadRate").text==="2.0 MiB/s"&&child("uploadRate").text==="1.0 KiB/s","Network readings missing");
            check(child("storageUsage-/").text==="1.0 GiB / 4.0 GiB"&&child("storageUsage-"+longPath).text==="2.0 GiB / 4.0 GiB","Filesystem readings missing");
            near(child("storageFill-/").width/child("storageFill-/").parent.width,.25,"Capacity bar wrong");
            check(child("performanceLive").visible&&!child("performanceStatus").visible,"Live state missing");
            check(child("CPUHistory").values[0]===.17&&child("MemoryHistory").values[0]===.25&&child("driveHistory-sda").values[0]===.02,"CPU/RAM/disk traces lost");
            check(child("downloadHistory").values[0]===2097152&&child("uploadHistory").values[0]===1024,"Separate network histories lost");
            check(child("downloadHistory").ceiling===child("uploadHistory").ceiling&&child("uploadHistory").ceiling===2097152,"Network traces use different scales");
            geometry();
            check(panel.implicitHeight<=510,"Two-drive metrics exceed normal 610px detail allocation "+panel.implicitHeight);
            const zero=known();zero.cpu=0;zero.memoryUsed=0;zero.download=0;zero.upload=0;
            zero.diskIo.forEach(d=>{d.busy=0;d.read=0;d.write=0;});panel.ingest(zero);
        } else if(phase===2) {
            check(child("CPUPercent").text==="0"&&child("MemoryPercent").text==="0"&&child("downloadRate").text==="0 B/s","Zero metrics shown as unknown");
            check(child("driveBusy-sda").text==="0% active","Zero busy lost");
            const unknown=known();unknown.cpu=null;unknown.memoryUsed=null;unknown.memoryTotal=null;unknown.download=null;unknown.upload=null;
            unknown.diskIo.forEach(d=>{d.busy=null;d.read=null;d.write=null;});unknown.disks.forEach(d=>{d.used=null;d.total=null;});panel.ingest(unknown);
        } else if(phase===3) {
            check(child("CPUPercent").text==="—"&&child("MemoryPercent").text==="—"&&child("MemoryDetail").text==="— / —","Null summary not unknown");
            check(child("driveBusy-sda").text==="—"&&child("sda-read").text==="—/s"&&child("downloadRate").text==="—/s","Null rates not unknown");
            check(child("storageUsage-/").text==="— / —"&&child("storageFill-/").width===0,"Unknown storage has invalid bar");
            check(panel.history.cpu.length===2&&panel.history.sda.length===2&&panel.history.download.length===2,"Null readings erased existing histories");
            panel.ingest(known());savedHistory=JSON.stringify(panel.history);savedSample=JSON.stringify(panel.sample);
            panel.ingest({error:"Metrics unavailable"});
        } else if(phase===4) {
            check(child("performanceStatus").visible&&child("performanceStatus").text==="Metrics unavailable"&&!child("performanceLive").visible,"Error state missing");
            check(JSON.stringify(panel.history)===savedHistory&&JSON.stringify(panel.sample)===savedSample,"Error erased last sample/history");
            check(child("CPUPercent").text==="17"&&child("storageUsage-/").text==="1.0 GiB / 4.0 GiB","Error hid last readings");
            for(let i=0;i<35;i++){const data=known();data.cpu=i/100;panel.ingest(data);}
        } else if(phase===5) {
            check(!panel.error&&!child("performanceStatus").visible,"Recovery retained error");
            for(const key of ["cpu","memory",longName,"sda","download","upload"])check(panel.history[key].length===30,"History retention changed "+key);
            near(panel.history.cpu[0],.05,"History oldest sample wrong");near(panel.history.cpu[29],.34,"History newest sample wrong");
            panel.height=220;
            const many=known();for(let i=0;i<6;i++){many.diskIo.push({name:"extra"+i,busy:.1,read:1024,write:0});many.disks.push({path:"/mount/"+i,used:1024,total:2048});}panel.ingest(many);
        } else if(phase===6) {
            geometry();check(scroll.contentHeight>scroll.height,"Short panel does not scroll");
            scroll.forceActiveFocus();input.keyClick(Qt.Key_End);
            near(scroll.contentY,scroll.contentHeight-scroll.height,"End does not reach storage");
            const last=child("storage-/mount/5");const bottom=last.mapToItem(scroll,0,last.height).y;
            check(bottom<=scroll.height+1&&bottom>0,"Last filesystem unreachable");
            input.keyClick(Qt.Key_Home);near(scroll.contentY,0,"Home does not reach CPU");
            input.keyClick(Qt.Key_PageDown);check(scroll.contentY>0,"Keyboard PageDown does not scroll");
            input.keyClick(Qt.Key_Up);input.keyClick(Qt.Key_PageUp);near(scroll.contentY,0,"Keyboard Up/PageUp does not scroll");
            input.mouseWheel(scroll,scroll.width/2,scroll.height/2,0,-120);
            input.tryVerify(()=>scroll.contentY>0,1000,"Mouse wheel does not scroll");check(scroll.contentY>0,"Mouse wheel did not reach metrics");
            savedHistory=JSON.stringify(panel.history);
            const back=walk(panel).find(item=>item.label==="Control center");check(!!back,"Back action missing");
            input.mouseClick(back,back.width/2,back.height/2);check(IslandState.menu==="quicksettings","Back action route failed");
        } else if(phase===7) {
            check(JSON.stringify(panel.history)===savedHistory,"Back navigation changed history");
            console.log("PERFORMANCE TEST_MODE TEST_WIDTH PASS");Qt.quit();return;
        }
        phase++;steps.restart();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

for mode in ('dark', 'light'):
    run(FOOTER.replace('TEST_MODE', mode), f'CONTROL FOOTER {mode} PASS')
    for width in (326, 256):
        run(PERFORMANCE.replace('TEST_MODE', mode).replace('TEST_WIDTH', str(width)),
            f'PERFORMANCE {mode} {width} PASS')
