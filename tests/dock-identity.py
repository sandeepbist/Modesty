#!/usr/bin/env python3
from qml import run
run('''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.components
ShellRoot {
 FloatingWindow {id:window;visible:true;implicitWidth:1100;implicitHeight:750
  Island.IslandSurface {id:surface;availableWidth:1100;availableHeight:750}
 }
 TestCase {id:input;when:false}
 function check(ok,label){if(!ok)throw new Error(label);}
 function walk(item){let all=[item];for(const c of item.children||[])all=all.concat(walk(c));return all;}
 function child(name){const c=input.findChild(surface,name);check(!!c,"Missing "+name);return c;}
 function pane(stage,name){return walk(stage).find(c=>c.modelData===name&&c.selected&&c.item);}
 function geometry(){return [surface.mediaStage,surface.clockStage,surface.controlStage].map(s=>[s.x,s.y,s.width,s.height]);}
 function toggle(){const g=JSON.stringify(geometry()),v=surface.dockVelocity;IslandState.toggleDock();check(Preferences.motion==="instant"||(JSON.stringify(geometry())===g&&surface.dockVelocity===v),"Retarget resets current frame or velocity before="+g+" after="+JSON.stringify(geometry())+" v="+v+" afterV="+surface.dockVelocity+" motion="+Preferences.motion);}
 function waitPane(stage,name){input.tryVerify(()=>!!pane(stage,name)&&pane(stage,name).enabled,2500,"Pane never reveals "+name);return pane(stage,name);}
 function morph(){
  Preferences.motion="fluid";Preferences.motionSpeed=.5;
  for(const progress of [.25,.6,.95]){
   IslandState.restingMode=IslandState.Pills;input.wait(900);IslandState.restingMode=IslandState.Dock;
   input.tryVerify(()=>surface.dockProgress>=progress,2000,"Progress not reached");toggle();input.wait(30);toggle();input.wait(40);
  }
  Preferences.motion="instant";IslandState.restingMode=IslandState.Dock;input.wait(50);
 }
 Component.onCompleted:{Preferences.motion="instant";Preferences.barHeight=35;Preferences.uiScale=.9;Preferences.collapsedWidth=105;Preferences.clusterGap=8;}
 Timer {interval:80;running:true;onTriggered:{try{
  Notifications.previewNotify(0);const record=Notifications.list[0];record.summary="Retained title";record.body="Retained body";record.localActions=[{identifier:"done",text:"Done",invoke:()=>{}}];
  const toast=waitPane(surface.clockStage,"toast"),stack=toast.item,card=child("popupCard"),scroll=child("notificationScroll");
  input.tryVerify(()=>stack.shown===record,1500);const app=record.appName;
  scroll.contentY=0;const focus=window.activeFocusItem;
  input.mouseMove(card,card.width/2,Math.max(45,card.height/2));input.wait(30);check(record.popupHovered,"Synthetic reading hover missing");
  morph();check(record.popupHovered,"Mode loses stationary reading hover inside retained card");
  check(toast.item===stack&&child("popupCard")===card&&stack.shown===record&&card.notification===record,"Notification object identity changed");
  check(record.summary==="Retained title"&&record.body==="Retained body"&&record.appName===app&&record.actions[0].identifier==="done","Notification content changed");
  check(window.activeFocusItem===focus,"Mode acquired keyboard focus");
  check(!record.expired&&!record.popupClosing,"Mode dismissed sticky notification");
  input.mouseMove(window.contentItem,1,1);
  Notifications.dismiss(record);input.wait(300);check(!record.popup,"Dismissal failed");
  IslandState.openMenu("wifi");const controls=waitPane(surface.controlStage,"quicksettings"),center=controls.item;input.wait(200);
  const sheet=child("controlDetailSheet"),viewport=child("controlDetailViewport"),width=controls.heldWidth,height=controls.heldHeight;
  const focusButton=walk(viewport).find(c=>c.label==="Control center");check(!!focusButton,"Detail action missing");focusButton.forceActiveFocus();
  morph();check(controls.item===center&&controls.heldWidth===width&&controls.heldHeight===height,"Mode resized or replaced held ControlCenter");check(focusButton.activeFocus,"Mode lost detail focus");
  check(center.apertureHeight===surface.controlStage.height-35,"Detail aperture includes dock header");
  check(sheet.mapToItem(surface,0,0).y>=35,"Detail overlaps dock header");
  IslandState.openMenu("notes");const notes=waitPane(surface.clockStage,"notes"),body=child("notesBody");body.forceActiveFocus();
  const popup=input.findChild(notes.item,"notesOverflow");check(!!popup,"Notes popup object missing");popup.open();input.tryVerify(()=>popup.visible,1000);const exposed=surface.popupInputRegion;check(!!exposed,"Notes popup missing native region");
  const text=body.text;Preferences.motion="fluid";toggle();input.wait(60);toggle();input.wait(800);
  check(pane(surface.clockStage,"notes")===notes&&body.text===text&&popup.visible&&surface.popupInputRegion===exposed,"Mode recreates Notes, loses draft or closes popup");
  popup.close();IslandState.closeMenu();input.wait(200);
  Preferences.motion="instant";Context.clear();Notifications.previewNotify(1100);const expiry=Notifications.list[0];input.wait(450);toggle();input.wait(150);toggle();input.wait(650);
  check(expiry.popupClosing||!expiry.popup,"Mode restarted notification expiry");
  console.log("DOCK IDENTITY PASS");Qt.quit();
 }catch(e){console.error(e);Qt.exit(1);}}}
}
''','DOCK IDENTITY PASS',timeout=35)
