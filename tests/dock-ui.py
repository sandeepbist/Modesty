#!/usr/bin/env python3
from qml import run
from pathlib import Path
import runpy

REGISTRY = '''import QtQuick
import Quickshell
import qs.services
ShellRoot {Timer {interval:50;running:true;onTriggered:{try{if(!Bindings.actions.some(a=>a.id==="dock"))throw new Error("Dock action is absent from native action registry");console.log("DOCK REGISTRY PASS");Qt.quit();}catch(e){console.error(e);Qt.exit(1);}}}}
'''
TRANSFORM = '''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.components
ShellRoot {
 property int phase:0
 property var retained
 property var pane
 FloatingWindow {visible:true;implicitWidth:1000;implicitHeight:700
  Island.IslandSurface {id:surface;availableWidth:1000;availableHeight:700}
 }
 TestCase {id:test;when:false}
 function check(ok,label){if(!ok)throw new Error(label+" phase="+phase);}
 function walk(item){let all=[item];for(const c of item.children||[])all=all.concat(walk(c));return all;}
 function snapshot(){return [surface.mediaStage,surface.clockStage,surface.controlStage].map(s=>[s.x,s.y,s.width,s.height]);}
 function toggle(){const before=JSON.stringify(snapshot());const velocity=surface.dockVelocity;const menu=IslandState.menu;IslandState.toggleDock();check(JSON.stringify(snapshot())===before,"Mode retarget synchronously changes geometry");check(surface.dockVelocity===velocity,"Mode retarget resets velocity");check(menu===IslandState.menu,"Mode changes lifecycle");}
 function centered(){const label=walk(surface).find(c=>c instanceof RollingText&&c.text===Time.timeStr);check(!!label,"Time missing");check(Math.abs(label.mapToItem(surface,label.width/2,0).x-surface.width/2)<.02,"Time leaves screen center");}
 Component.onCompleted:{Preferences.motion="instant";Preferences.uiScale=.9;Preferences.barHeight=35;Preferences.collapsedWidth=105;Preferences.clusterGap=8;}
 Timer {interval:140;repeat:true;running:true;onTriggered:{try{
  check(surface.dockProgress!==undefined,"Native dock projection is absent");centered();
  if(phase===0){const marks=walk(surface).find(c=>c instanceof Island.WorkspaceMarks);check(marks.parent===surface.clockStage.capsule.contentItem,"Workspace details escape moving clip");check(surface.clockStage.height===35,"Resting height changed");check(surface.mediaStage.mode!=="media","Dock fixture has fabricated media");Preferences.motion="fluid";toggle();}
  else if(phase<4){if(phase===1)check(surface.dockProgress>0,"Projection did not move");toggle();}
  else if(phase===4){IslandState.restingMode=IslandState.Dock;}
  else if(phase===9){check(surface.dockProgress===1,"Dock did not settle");check(surface.clockStage.height===35,"Dock resting height changed");check(surface.clockHitRegion.width<surface.clockStage.width,"Clock input covers dock controls");IslandState.openMenu("wifi");}
  else if(phase===15){pane=walk(surface.controlStage).find(c=>c.modelData==="quicksettings"&&c.selected&&c.item);check(!!pane,"ControlCenter missing");retained=pane.item;Preferences.motion="fluid";toggle();}
  else if(phase===16){check(pane.item===retained,"Panel recreated during mode toggle");toggle();}
  else if(phase===22){check(pane.item===retained,"Retained panel identity lost");check(pane.heldWidth===surface.controlStage.targetWidth,"Mode resized held panel");IslandState.closeMenu();Preferences.motion="instant";IslandState.restingMode=IslandState.Dock;}
  else if(phase===24){check(surface.clockStage.height===35,"Dock fails to return to rest");Context.show("workspace","Brave","",0);}
  else if(phase===25){check(surface.clockStage.height===35,"Workspace Context expands dock header");centered();check(walk(surface).some(c=>c.text===Time.timeStr&&c.opacity>0),"Context replaces dock time");console.log("DOCK TRANSFORM PASS");Qt.quit();}
  phase++;
 }catch(e){console.error(e);Qt.exit(1);}}}
}
'''
if __name__ == '__main__':
    run(REGISTRY, 'DOCK REGISTRY PASS')
    run(TRANSFORM, 'DOCK TRANSFORM PASS')
    scroll=runpy.run_path(str(Path(__file__).with_name('island-geometry-ui.py')))['SCROLL']
    scroll=scroll.replace('Preferences.motion="instant";Preferences.footerTray=false;', 'Preferences.motion="instant";Preferences.footerTray=false;IslandState.restingMode=IslandState.Dock;').replace('ISLAND SCROLL PASS','DOCK SHORT SCROLL PASS')
    scroll=scroll.replace('check(!!overview,"Narrow overview has no scroll viewport");','check(!!overview,"Narrow overview has no scroll viewport");check(Math.abs(overview.parent.parent.visibleScale-1)<.001,"Short dock controls remain scaled down");')
    run(scroll,'DOCK SHORT SCROLL PASS')
