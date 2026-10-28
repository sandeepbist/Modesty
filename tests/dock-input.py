#!/usr/bin/env python3
import re,tempfile
from pathlib import Path
from unittest.mock import patch
import qml
ROOT=qml.ROOT
source=(ROOT/'modules/island/IslandDropTarget.qml').read_text().replace('PanelWindow {','FloatingWindow {',1)
source='\n'.join(line for line in source.splitlines() if not line.strip().startswith(('exclusionMode:','anchors {','margins {','WlrLayershell.')))
mask=re.search(r'    mask: Region \{.*?\n    \}',(ROOT/'modules/island/Island.qml').read_text(),re.S).group()
SOURCE='''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import "NATIVE" as Native
import qs.services
ShellRoot {
 property int phase:0
 FloatingWindow {
  id:root;visible:true;implicitWidth:1000;implicitHeight:700
  property alias surface:surface
  property bool captureActive:false
  property bool hiddenByFullscreen:false
  Island.IslandSurface {id:surface;availableWidth:1000;availableHeight:700;visible:!root.hiddenByFullscreen&&!root.captureActive&&!Session.locked&&!Session.secure}
  MASK
 }
 Native.DropTarget {id:drop;sourceIsland:root;visible:!Session.locked&&!Session.secure&&!root.hiddenByFullscreen&&surface.visible}
 TestCase {id:input;when:false}
 function check(ok,label){if(!ok)throw new Error(label);}
 function regionContains(region,item){if(!region.item)return false;const p=item.mapToItem(region.item,item.width/2,item.height/2);return p.x>=0&&p.y>=0&&p.x<region.item.width&&p.y<region.item.height;}
 function walk(item){let a=[item];for(const c of item.children||[])a=a.concat(walk(c));return a;}
 Component.onCompleted:{Preferences.motion="instant";Preferences.barHeight=35;Preferences.uiScale=.9;IslandState.restingMode=IslandState.Dock;}
 Timer {interval:100;running:true;repeat:true;onTriggered:{try{
  if(phase===0){
   check(drop.interactive,"Dock clock overlay unavailable");
   check(drop.liveBox.width<=Math.ceil((surface.clockHitRegion.width+12)*Preferences.uiScale),"Drop overlay steals dock controls");
   check(surface.clockOrigin.width===surface.clockHitRegion.width&&surface.clockOrigin.height===35,"CommandCanvas origin is not clock-sized");
   const controls=walk(surface).find(c=>c.Accessible?.name==="Control center"&&c.activeFocusOnTab);
   check(!!controls,"Dock controls missing accessible action");input.mouseClick(controls,controls.width/2,controls.height/2);check(IslandState.menu==="quicksettings","Whole-Stage input steals control action");
   drop.hold();const box=JSON.stringify(drop.heldBox);Preferences.motion="fluid";IslandState.toggleDock();drop.hold();check(JSON.stringify(drop.heldBox)===box,"Repeated drag entry recaptures heldBox");
  }else if(phase===1){
   const embedded=walk(surface).find(c=>c.offer!==undefined&&c.heldBox!==undefined);check(!!embedded,"Embedded drop path missing");embedded.heldBox=embedded.liveBox;embedded.holding=true;const embeddedBox=JSON.stringify(embedded.box);
   const box=JSON.stringify(drop.heldBox);IslandState.toggleDock();check(JSON.stringify(embedded.box)===embeddedBox,"Embedded drag follows projection");embedded.completing=true;embedded.holding=false;check(JSON.stringify(embedded.box)===embeddedBox,"Embedded completion loses held geometry");embedded.completing=false;check(JSON.stringify(drop.box)===box,"Projection moves held drag geometry");drop.completing=true;drop.holding=false;check(JSON.stringify(drop.box)===box,"Completion loses heldBox");
   root.hiddenByFullscreen=true;
  }else if(phase===2){check(!drop.interactive&&!root.mask.item,"Fullscreen leaves clock input active");root.hiddenByFullscreen=false;root.captureActive=true;}
  else if(phase===3){check(!drop.interactive&&!root.mask.item,"Capture leaves clock input active");root.captureActive=false;Session.locked=true;}
  else if(phase===4){const mode=IslandState.restingMode;IslandState.toggleDock();check(IslandState.restingMode===mode,"Locked toggle accepted");check(!drop.interactive&&!root.mask.item&&!drop.holding&&!drop.completing,"Lock retains drag or input");Session.locked=false;Session.secure=true;}
  else if(phase===5){const mode=IslandState.restingMode;IslandState.toggleDock();check(IslandState.restingMode===mode&&!drop.interactive,"Secure toggle or input accepted");Session.secure=false;IslandState.closeMenu();Preferences.motion="instant";IslandState.restingMode=IslandState.Dock;}
  else if(phase===6){
   const oldPosition=surface.naturalCenterX-Preferences.barHeight-Preferences.clusterGap;
   check(surface.clockStage.inputRegion.width===surface.clockStage.width+12,"Mask does not follow projected geometry");
   const mode=IslandState.restingMode;Bindings.trigger("dock");check(IslandState.restingMode===mode,"Preview binding action escaped guard");
   console.log("DOCK INPUT PASS");Qt.quit();
  }
  phase++;
 }catch(e){console.error(e);Qt.exit(1);}}}
}
'''
with tempfile.TemporaryDirectory(prefix='modesty-dock-input-') as d:
    w=Path(d);native=w/'native';native.mkdir();(native/'DropTarget.qml').write_text(source)
    for n in ('components','modules','assets','theme','scripts'):(w/n).symlink_to(ROOT/n)
    (w/'services').mkdir()
    for f in (ROOT/'services').iterdir():
        if f.name!='Session.qml':(w/'services'/f.name).symlink_to(f)
    (w/'services/Session.qml').write_text('pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {property bool locked:false;property bool secure:false;function isLocked(){return locked;}}')
    with patch.object(qml,'ROOT',w):qml.run(SOURCE.replace('NATIVE',native.as_uri()).replace('MASK',mask),'DOCK INPUT PASS')
