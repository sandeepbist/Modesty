#!/usr/bin/env python3
"""Exercise the retained compact activity against native production QML."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = dict(uiScale=.9, barHeight=35, collapsedWidth=105, clusterGap=8,
                expandedRadius=30, innerPadding=15, fontFamily='Inter Variable',
                clockFontFamily='Inter Variable', showSeconds=False, topMargin=8,
                privacyIndicatorGap=25, privacyIndicatorRightPadding=19,
                motion='gentle', motionSpeed=1.15)
MEDIA = '''pragma Singleton
import QtQuick
import Quickshell
Singleton {
 property bool hasSession:true;property bool playing:false
 property QtObject active:QtObject {property string trackAlbum:"Native fixture";property string identity:"Native fixture"};property var players:[]
 property string title:"NEON BLADE";property string artist:"MoonDeity";property string artUrl:""
 property real length:265;property real position:229;property real progress:229/265
 property bool canSeek:true;property bool canRepeat:false;property bool canGoNext:true;property bool canGoPrevious:true
 property string repeatLabel:"Repeat unavailable";property string repeatIcon:"repeat"
 function togglePlaying(){}function next(){}function previous(){}function seekTo(value){}function cycleRepeat(){}
}'''
SOURCE = r'''import QtQuick
import QtTest
import Quickshell
import Quickshell.Widgets
import "modules/island" as Island
import qs.services
import qs.components
import qs.theme
ShellRoot {
 id:root
 property var retained:null
 property var rows:[]
 property bool captured:false
 property bool observing:false
 property string collisionFailure:""
 property int maskIndex:0
 property int masksPending:0
 property real sampledProgress:-1
 onObservingChanged:sampledProgress=-1
 FloatingWindow {id:window;visible:true;implicitWidth:1920;implicitHeight:750
  Rectangle {id:canvas;anchors.fill:parent;color:"#273540"
   Island.IslandSurface {id:surface;y:Preferences.topMargin;availableWidth:1920;availableHeight:1080;scale:Preferences.uiScale;transformOrigin:Item.TopLeft}
   Item {id:measureScene;x:20;y:550;width:250;height:100;visible:false
    ClippingRectangle {id:controlClip;width:80;height:25;radius:12;color:"transparent";contentInsideBorder:false
     Item {width:60;height:18;clip:true
      Rectangle {id:controlBody;x:10;y:10;width:50;height:20;color:"white"}
     }
    }
    Rectangle {id:controlReference;x:10;y:19;width:50;height:6;color:"white"}
    Rectangle {id:timingReference;x:10;y:60;width:20;height:20;color:"white"}
    Rectangle {id:timingBody;x:10;y:60;width:20;height:20;color:"white"}
   }
  }
 }
 TestCase {id:input;when:false}
 function check(ok,label){if(!ok)throw new Error(label);}
 function walk(item){let a=[item];for(const c of item.children||[])a=a.concat(walk(c));return a;}
 function child(name){const c=input.findChild(surface,name);check(!!c,"Missing "+name);return c;}
 function pane(stage,name){return walk(stage).find(c=>c.modelData===name&&c.selected&&c.item);}
 function waitPane(stage,name){input.tryVerify(()=>!!pane(stage,name)?.enabled,3000,"Pane not exposed "+name);return pane(stage,name);}
 function box(item){const p=item.mapToItem(surface,0,0),q=item.mapToItem(surface,item.width,item.height);return {x:p.x,y:p.y,w:q.x-p.x,h:q.y-p.y};}
 function overlap(a,b){return Math.max(0,Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x))*Math.max(0,Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y));}
 function geometry(){return [surface.mediaStage,surface.clockStage,surface.controlStage].map(s=>[s.x,s.width,s.height]);}
 function validate(name){
  const a=child("compactActivity"),v=child("activityViewport");
  check(a===retained,"Activity object recreated "+name);
  check(walk(surface).filter(c=>c instanceof Island.ActivityStatus).length===1,"Duplicate activity "+name);
  check(!walk(surface).some(c=>c.modelData==="activities"),"Activity still a body "+name);
  const clock=walk(surface).find(c=>c instanceof RollingText&&c.text===Time.timeStr);
  check(clock&&Math.abs(clock.mapToItem(surface,clock.width/2,0).x-surface.width/2)<.03,"Clock moved "+name);
  separation(name);
  if(surface.dockProgress===1)for(const orb of walk(surface).filter(c=>c instanceof Island.StatusOrb)){
   check(orb.deviceOnly||Math.abs(orb.width-orb.dockImplicitWidth)<.02,"Dock uses compact status fallback");
   for(const c of orb.children)if((typeof c.modelData==="number")||("preferredRendererType" in c))check(c.opacity===0,"Dock ring/dots survive "+name);
  }
  const row={name,mode:IslandState.restingMode,progress:surface.dockProgress,velocity:surface.dockVelocity,activity:box(a),viewport:{width:v.width,contentWidth:v.contentWidth,x:v.contentX},dock:surface.diagnostics().dock,panel:surface.controlStage.panel,body:surface.dockPanels.map(s=>s.panel),primary:Activities.primary,recording:Recorder.phase,focus:FocusTimer.phase,privacy:Audio.indicatorKind};
  rows.push(row);console.log("ACTIVITY "+JSON.stringify(row));
 }
 function objectWalk(item,seen){
  if(!item||seen.has(item))return [];seen.add(item);let rows=[item];
  for(const c of [...(item.data||[]),...(item.children||[])])rows=rows.concat(objectWalk(c,seen));
  return rows;
 }
 function freezeFrames(){
  const rows=objectWalk(surface,new Set()).filter(c=>c instanceof FrameSpring&&c.running).map(c=>({spring:c,value:c.value,velocity:c.velocity,target:c.targetValue}));
  for(const row of rows)row.spring.frames.stop();return rows;
 }
 function restoreFrames(rows){for(const row of rows){check(row.spring.value===row.value&&row.spring.velocity===row.velocity,"Measurement changed spring state");row.spring.start();}}
 Component {id:holdOpacity;Binding {property:"opacity";restoreMode:Binding.RestoreBindingOrValue}}
 Component {id:hideForMask;Binding {property:"visible";value:false;restoreMode:Binding.RestoreBindingOrValue}}
 function isolate(item,ancestor){
  const bindings=[];
  for(let c=item;c!==(ancestor.contentItem||ancestor);c=c.parent){check(!!c.parent,"Mask ancestor missing");for(const sibling of c.parent.children)if(sibling!==c)bindings.push(hideForMask.createObject(root,{target:sibling}));}
  return bindings;
 }
 function chain(item){const rows=[];for(let c=item;c&&c!==surface;c=c.parent)rows.push({type:String(c),box:box(c),clip:c.clip,opacity:c.opacity,visible:c.visible,radius:c.radius});return rows;}
 function sameBox(a,b){return ["x","y","w","h"].every(k=>Math.abs(a[k]-b[k])<.001);}
 function separation(name){
  if(masksPending)return;
  const a=child("compactActivity"),jobs=[];
  for(const stage of [surface.mediaStage,surface.clockStage,surface.controlStage])for(const p of walk(stage).filter(c=>c.modelData&&c.selected&&c.item&&c.opacity>.01)){
   if(a.visible&&a.enabled&&a.parent.enabled&&a.parent.opacity>.01&&overlap(box(a),box(p))>0)jobs.push({stage,p});
  }
  if(!jobs.length)return;
  const frozen=freezeFrames();masksPending=1;
  const activityRoot=surface.controlStage.capsule;
  function next(){
   if(!jobs.length){try{restoreFrames(frozen);}catch(e){collisionFailure=e.toString();}masksPending=0;return;}
   const job=jobs.shift(),bodyRoot=job.stage.capsule;
   for(const target of [activityRoot,bodyRoot])for(let c=target.parent;c&&c!==surface;c=c.parent)check(!c.clip,"Unhandled clip above mask ancestor");
   const held=[],seen=new Set();for(const item of [a,job.p.item])for(let c=item;c&&c!==surface;c=c.parent)if(!seen.has(c)){seen.add(c);held.push(holdOpacity.createObject(root,{target:c,value:c.opacity}));}
   const id=maskIndex++,row={id,name,activity:box(activityRoot),body:box(bodyRoot),activityItem:box(a),bodyItem:box(job.p.item),progress:surface.dockProgress,activityChain:chain(a),bodyChain:chain(job.p.item),callbacks:[],synchronized:true,ancestorClipping:true,frozenSprings:frozen.length,frozenAncestorOpacities:held.length,requestTime:Date.now()};
   const parts=[[a,activityRoot,"activity"],[job.p.item,bodyRoot,"body"]];
   function part(){
    if(!parts.length){console.log("PAINT "+JSON.stringify(row));for(const binding of held)binding.destroy();Qt.callLater(next);return;}
    const [item,ancestor,label]=parts.shift(),bindings=isolate(item,ancestor);
    ancestor.grabToImage(result=>{
     try{
      const callback={label,time:Date.now(),progress:surface.dockProgress,item:box(item),mask:box(ancestor),chain:chain(item)};row.callbacks.push(callback);
      check(sameBox(callback.item,label==="activity"?row.activityItem:row.bodyItem)&&sameBox(callback.mask,row[label])&&callback.progress===row.progress,"Mask frame drift "+name+" "+label);
      const before=label==="activity"?row.activityChain:row.bodyChain;check(callback.chain.length===before.length&&callback.chain.every((c,i)=>sameBox(c.box,before[i].box)&&Math.abs(c.opacity-before[i].opacity)<.000001&&c.visible===before[i].visible),"Mask ancestor frame drift "+name+" "+label);
      check(result.saveToFile("OUTPUT/mask-"+id+"-"+label+".png"),"Paint capture failed");
     }catch(e){collisionFailure=e.toString();row.synchronized=false;}
     for(const binding of bindings)binding.destroy();Qt.callLater(part);
    });
   }
   part();
  }
  next();
 }
 FrameAnimation {running:root.observing;onTriggered:{
  if(masksPending===0&&Math.abs(surface.dockProgress-sampledProgress)>.07){sampledProgress=surface.dockProgress;Qt.callLater(()=>{try{if(root.observing)separation("frame");}catch(e){root.collisionFailure=e.toString();}});}
 }}
 function capture(name){input.tryVerify(()=>masksPending===0,5000,"Drain preceding mask");validate(name);input.tryVerify(()=>masksPending===0,5000,"Drain captured mask");check(!collisionFailure,collisionFailure);captured=false;canvas.grabToImage(result=>{check(result.saveToFile("OUTPUT/"+name+".png"),"Capture failed");captured=true;});input.tryVerify(()=>captured,3000,"Capture timed out");}
 function measurementControls(){
  measureScene.visible=true;input.wait(30);let pending=0;
  for(const [item,label] of [[controlBody,"raw"],[controlClip,"clipped"],[controlReference,"activity"]]){
   pending++;item.grabToImage(result=>{check(result.saveToFile("OUTPUT/control-clipping-"+label+".png"),"Clipping control capture");pending--;});
  }
  const clipRow={kind:"clipping",activity:box(controlReference),raw:box(controlBody),clipped:box(controlClip)};
  input.tryVerify(()=>pending===0,3000,"Clipping control pending");console.log("MEASURE_CONTROL "+JSON.stringify(clipRow));
  const request=box(timingBody);pending=2;
  timingReference.grabToImage(result=>{check(result.saveToFile("OUTPUT/control-timing-activity.png"),"Timing reference capture");pending--;});
  timingBody.grabToImage(result=>{
   check(result.saveToFile("OUTPUT/control-timing-body.png"),"Timing body capture");
   const callback=box(timingBody);check(!sameBox(request,callback),"Timing control did not introduce drift");
   console.log("MEASURE_CONTROL "+JSON.stringify({kind:"timing",activity:box(timingReference),request,callback,driftDetected:!sameBox(request,callback)}));pending--;
  });
  timingBody.x+=100;input.tryVerify(()=>pending===0,3000,"Timing control pending");measureScene.visible=false;
 }
 function focus(phase){input.tryVerify(()=>masksPending===0,5000,"Drain mask before activity change");FocusTimer.loaded=false;FocusTimer.duration=3600;FocusTimer.remaining=2315;FocusTimer.deadline=Date.now()+2315000;FocusTimer.phase=phase;}
 function reset(){Context.clear();IslandState.closeMenu();Recorder.status={phase:"idle"};Radio.devices=[];Audio.directCameras=[];focus("idle");Preferences.motion="instant";surface.availableWidth=1920;Preferences.showStatus=true;}
 function passive(name){input.wait(70);check(surface.dockHeight===35&&!surface.dockBody,"Activity expanded body "+name);capture(name);}
 function toggle(){input.tryVerify(()=>masksPending===0,5000,"Drain mask before retarget");const g=JSON.stringify(geometry()),v=surface.dockVelocity,m=IslandState.menu;IslandState.toggleDock();check(JSON.stringify(geometry())===g&&surface.dockVelocity===v&&IslandState.menu===m,"Mode retarget resets state");}
 function reachable(item){item.forceActiveFocus();input.wait(30);const v=child("activityViewport"),p=item.mapToItem(v,0,0);check(item.activeFocus&&p.x>=-.05&&p.x+item.width<=v.width+.05,"Focused action clipped "+item.objectName+" "+JSON.stringify({x:p.x,w:item.width,viewport:v.width}));}
 Component.onCompleted:{Quickshell.watchFiles=false;for(const [key,value] of Object.entries(SETTINGS))Preferences[key]=value;Preferences.motion="instant";Preferences.contextEvents=false;Preferences.footerTray=false;Preferences.contextDevices=false;Preferences.contextBattery=false;}
 Timer {interval:150;running:true;onTriggered:{try{
  measurementControls();reset();IslandState.restingMode=IslandState.Dock;focus("paused");input.wait(90);check(surface.dockHeight===35&&!surface.dockBody,"Ongoing activity expanded dock to "+surface.dockHeight);
  retained=child("compactActivity");reset();IslandState.restingMode=IslandState.Dock;passive("dock-idle");
  for(const phase of ["running","paused","finished"]){focus(phase);passive("dock-focus-"+phase);}
  FocusTimer.kind="break";focus("paused");passive("dock-break");FocusTimer.kind="focus";
  for(const mode of [IslandState.Pills,IslandState.Dock]){
   IslandState.restingMode=mode;input.wait(100);capture(mode===0?"pills-focus":"dock-focus");
   const detail=child("focusDetail"),action=child("focusAction");
   input.mouseClick(detail,detail.width/2,detail.height/2);check(IslandState.menu==="focus","Detail hit swallowed");waitPane(surface.controlStage,"quicksettings");input.wait(150);
   check(mode===1||!retained.parent.enabled,"Hidden pill rest remains enabled");
   if(mode===0)for(let i=0;i<8;i++){input.keyClick(Qt.Key_Tab);input.wait(5);check(!walk(retained).some(c=>c.activeFocus),"Hidden pill activity remains in Tab chain");}
   if(mode===0){const state=FocusTimer.phase;input.mouseClick(action,action.width/2,action.height/2);check(FocusTimer.phase===state,"Hidden pill action received input");}
   capture(mode===0?"pills-focus-detail":"dock-focus-detail");IslandState.closeMenu();input.wait(100);
   FocusTimer.loaded=true;input.mouseClick(action,action.width/2,action.height/2);check(FocusTimer.phase==="running","Resume hit swallowed");
   input.mouseClick(action,action.width/2,action.height/2);check(FocusTimer.phase==="paused","Pause hit swallowed");
   action.forceActiveFocus();input.keyClick(Qt.Key_Space);check(FocusTimer.phase==="running","Keyboard resume failed");focus("finished");FocusTimer.loaded=true;input.wait(30);
   input.mouseClick(action,action.width/2,action.height/2);check(FocusTimer.phase==="idle","Dismiss hit swallowed");focus("paused");
  }
  for(const phase of ["preparing","countdown","recording","paused","saving"]){focus("idle");Recorder.status={phase,remaining:3,elapsed:127};passive("dock-recording-"+phase);const stop=child("recorderAction");check(stop.enabled===(phase!=="saving"),"Saving action availability changed");if(stop.enabled){const n=Recorder.testStops;input.mouseClick(stop,stop.width/2,stop.height/2);check(Recorder.testStops===n+1,"Stop hit swallowed");}}
  Recorder.status={phase:"selecting"};input.wait(50);check(!Activities.active&&!retained.visible,"Region selection has activity");passive("dock-selecting");
  focus("paused");Recorder.status={phase:"recording",elapsed:127};input.wait(180);check(Activities.primary==="recording"&&Activities.dual,"New recorder preference lost");
  const selector=child("activitySelector");input.mouseClick(selector,selector.width/2,selector.height/2);input.wait(180);check(Activities.primary==="focus","Dual selector swallowed");capture("dock-dual-focus");
  selector.forceActiveFocus();input.keyClick(Qt.Key_Return);input.wait(180);check(Activities.primary==="recording","Keyboard cycle failed");
  input.mouseWheel(retained,20,17,0,-120);input.wait(250);check(Activities.primary==="focus","Wheel cycle failed");
  Recorder.status={phase:"idle"};Radio.devices=[{name:"Probe headphones",deviceName:"Probe headphones",icon:"audio-headphones",connected:true,batteryAvailable:true,battery:.5,address:"probe"}];input.wait(180);capture("dock-device-focus");
  const device=child("activityDevice");input.mouseClick(device,device.width/2,device.height/2);check(IslandState.menu==="bluetooth","Device hit swallowed");IslandState.closeMenu();input.wait(100);
  const orb=child("systemStatus"),control=walk(surface).find(c=>c.Accessible?.name==="Control center"&&c.activeFocusOnTab&&c.enabled);check(control&&control.width===orb.width,"Control center hit covers activity");input.mouseClick(control,control.width/2,control.height/2);check(IslandState.menu==="quicksettings","Control center hit failed");IslandState.closeMenu();
  Audio.directCameras=[{directCamera:true,label:"Native fixture camera"}];Preferences.showStatus=false;input.wait(100);capture("dock-privacy-device");const privacy=walk(surface).find(c=>c instanceof PrivacyIndicator);input.mouseClick(privacy,privacy.width/2,privacy.height/2);check(IslandState.menu==="privacy","Privacy hit swallowed");IslandState.closeMenu();check(Audio.indicatorKind!==""&&surface.controlStage.visible,"Optional status hides active task/privacy");
  reset();focus("paused");IslandState.openMenu("media");const media=waitPane(surface.mediaStage,"media"),card=media.item;input.wait(200);capture("dock-media-focus");
  Preferences.motion="gentle";Preferences.motionSpeed=.5;observing=true;IslandState.restingMode=IslandState.Pills;input.wait(800);capture("pills-media-focus");
  for(let round=0;round<2;round++){
   toggle();for(let i=0;i<5;i++){input.wait(35);capture("morph-"+round+"-"+i);}
   toggle();input.wait(35);capture("reversal-"+round);toggle();input.wait(800);
   check(media.item===card&&media.enabled&&media.opacity>.99,"Media identity/exposure lost");check(!collisionFailure,collisionFailure);
  }
  observing=false;input.tryVerify(()=>masksPending===0,5000,"Drain moving paint captures");
  const spring=surface.data.find(c=>c instanceof FrameSpring&&c.maximumValue===1);check(!!spring,"Projection spring missing");
  for(const target of [card,child("focusDetail"),child("focusAction")]){
   target.forceActiveFocus();const name=target===card?"plain":target.objectName;
   for(const p of [.25,.46,.48,.497,.5,.527,.55,.57,.75]){spring.reset(p);input.wait(25);capture("projection-"+name+"-"+p);}
  }
  Preferences.motion="instant";IslandState.closeMenu();IslandState.restingMode=IslandState.Pills;input.wait(100);
  Preferences.motion="gentle";Preferences.motionSpeed=.5;IslandState.restingMode=IslandState.Dock;input.wait(80);
  check(surface.dockProgress>0&&surface.dockProgress<1,"Media arrival fixture missed dock motion");IslandState.openMenu("media");
  for(let i=0;i<6;i++){input.wait(25);capture("media-arrival-"+i);}
  IslandState.restingMode=IslandState.Pills;IslandState.closeMenu();
  for(let i=0;i<3;i++){input.wait(25);capture("media-retirement-"+i);}
  IslandState.openMenu("media");
  for(let i=0;i<6;i++){input.wait(25);capture("media-reactivation-"+i);}
  input.wait(900);check(media.item&&media.enabled,"Mid-motion media reactivation did not reveal a card");
  spring.reset(1);observing=true;
  IslandState.openMenu("notes");const notes=waitPane(surface.clockStage,"notes"),menu=notes.item,body=child("notesBody"),scroll=child("notesScroll");body.text=Array.from({length:80},(_,i)=>"Line "+i).join("\n");body.cursorPosition=0;input.wait(120);scroll.contentY=60;body.forceActiveFocus();const y=scroll.contentY;
  focus("idle");input.wait(100);const oldFocus=window.activeFocusItem;focus("paused");input.wait(20);capture("arrival-notes");check(window.activeFocusItem===oldFocus&&body.activeFocus,"Activity arrival stole body focus");
  toggle();input.wait(80);capture("arrival-morph");Recorder.status={phase:"recording",elapsed:127};input.wait(40);capture("arrival-dual-morph");toggle();input.wait(800);
  check(!collisionFailure,collisionFailure);observing=false;check(notes.item===menu&&body.activeFocus&&scroll.contentY===y&&notes.opacity>.99,"Activity/morph loses body identity focus scroll");capture("dock-notes-dual");
  for(const p of [.15,.25,.28,.3,.3038436860605998,.31,.35,.46,.5,.57,.75]){spring.reset(p);input.wait(25);capture("projection-notes-"+p);}spring.reset(1);
  Preferences.motion="instant";IslandState.restingMode=IslandState.Dock;
  for(const name of ["clock","privacy","wifi","focus","recorder","calendar","launcher"]){IslandState.openMenu(name);input.wait(300);validate("body-"+name);check(surface.dockBody,"Explicit body missing "+name);}
  IslandState.closeMenu();Recorder.status={phase:"idle"};focus("finished");Preferences.contextEvents=true;Preferences.contextDuration=800;Context.show("notice","Focus complete","timer",0);input.wait(100);capture("completion-context");check(surface.controlStage.panel==="context"&&surface.dockBody,"Completion Context behavior changed");input.wait(850);check(!Context.active&&surface.dockHeight===35&&!surface.dockBody,"Notice expiry reopens body");capture("completion-expired");
  IslandState.restingMode=IslandState.Pills;Preferences.contextEvents=true;Context.show("audiooutput","Headphones","headphones",0);input.wait(100);input.mouseClick(surface.controlStage,surface.controlStage.width/2,17);check(IslandState.menu==="sound","Controls Context action lost");IslandState.closeMenu();Context.clear();IslandState.restingMode=IslandState.Dock;
  Preferences.contextEvents=false;focus("paused");Recorder.status={phase:"preparing",remaining:3};input.wait(150);Audio.directCameras=[{directCamera:true,label:"Native camera"}];
  let critical=1000;
  for(let width=1000;width>=250;width-=10){surface.availableWidth=width;if(surface.compactDisclosure){critical=width+10;break;}}
  surface.availableWidth=critical;input.wait(150);check(!surface.compactDisclosure&&surface.dockHeaderSupported,"Fitting full header rejected");
  for(const item of [child("recorderDetail"),child("recorderAction"),child("activitySelector")]){reachable(item);capture("narrow-"+item.objectName);}
  for(const name of ["recorderAction","activitySelector"]){
   Recorder.status={phase:"recording",elapsed:127};input.wait(80);const item=child(name);reachable(item);
   Recorder.status={phase:"paused",elapsed:127};input.wait(100);const viewport=child("activityViewport"),point=item.mapToItem(viewport,0,0);
   check(item.activeFocus&&point.x>=-.05&&point.x+item.width<=viewport.width+.05,"Recorder phase hides focused "+name+" "+JSON.stringify({x:point.x,width:item.width,viewport:viewport.width}));capture("narrow-paused-"+name);
  }
  Recorder.status={phase:"preparing",remaining:3};input.wait(100);
  capture("narrow-supported");console.log("FLOOR "+JSON.stringify({physical:surface.availableWidth,logical:surface.dockMinimumWidth,aperture:child("activityViewport").width,clock:surface.dockClockNeed,status:orb.dockImplicitWidth}));
  IslandState.restingMode=IslandState.Pills;input.wait(100);for(const item of [child("recorderDetail"),child("recorderAction"),child("activitySelector")])reachable(item);capture("narrow-pills");IslandState.restingMode=IslandState.Dock;input.wait(100);
  surface.availableWidth=330;input.wait(100);check(surface.compactDisclosure&&child("dockOverflow").enabled,"Narrow disclosure unavailable");
  check(!child("recorderAction").visible&&!child("activitySelector").parent.visible,"Displaced actions remain exposed");
  reachable(child("recorderDetail"));input.mouseClick(child("dockOverflow"),14,17);check(IslandState.menu==="quicksettings","Narrow displaced action route missing");IslandState.closeMenu();capture("narrow-disclosed");
  input.tryVerify(()=>masksPending===0,5000,"Paint capture pending");check(!collisionFailure,collisionFailure);
  console.log("ACTIVITY HEADER PASS");Qt.quit();
 }catch(e){console.error(e);Qt.exit(1);}}}
}'''


def painted_overlap(activity_path, body_path, activity, body):
    x, y = max(activity['x'], body['x']), max(activity['y'], body['y'])
    width = min(activity['x'] + activity['w'], body['x'] + body['w']) - x
    height = min(activity['y'] + activity['h'], body['y'] + body['h']) - y
    if width <= 0 or height <= 0:
        return dict(painted_overlap=0, alpha_contacts=0, maximum_alpha_product=0)
    masks = []
    for path, box in ((activity_path, activity), (body_path, body)):
        alpha = Image.open(path).convert('RGBA').getchannel('A')
        sx, sy = alpha.width / box['w'], alpha.height / box['h']
        projected = alpha.transform((math.ceil(width * 4), math.ceil(height * 4)),
                                   Image.Transform.AFFINE,
                                   (sx / 4, 0, (x - box['x']) * sx,
                                    0, sy / 4, (y - box['y']) * sy),
                                   Image.Resampling.BILINEAR)
        masks.append(projected.tobytes())
    products = [a * b for a, b in zip(*masks)]
    return dict(painted_overlap=sum(product >= 255 for product in products),
                alpha_contacts=sum(product > 0 for product in products),
                maximum_alpha_product=max(products, default=0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--settings', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='modesty-activity-') as directory:
        work = Path(directory)
        out = args.output.resolve() if args.output else work / 'evidence'
        out.mkdir(parents=True, exist_ok=True)
        hashes = {}
        for folder in ('components', 'modules', 'assets', 'theme', 'services', 'scripts'):
            shutil.copytree(ROOT / folder, work / folder, symlinks=True)
            for p in (work / folder).rglob('*'):
                if p.is_file():
                    hashes[str(p.relative_to(work))] = hashlib.sha256(p.read_bytes()).hexdigest()
        (out / 'source-sha256.json').write_text(json.dumps(hashes, indent=2))
        (out / 'test-sha256.json').write_text(json.dumps({str(Path(__file__).resolve()): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2))
        (work / 'services/Media.qml').write_text(MEDIA)
        p = work / 'services/Radio.qml'
        radio = p.read_text()
        line = next(line for line in radio.splitlines() if 'readonly property var devices:' in line)
        p.write_text(radio.replace(line, '    property var devices: []'))
        p = work / 'services/FocusTimer.qml'
        timer = p.read_text().replace('if(!loaded||Preferences.preview||Session.isLocked())return;', 'if(!loaded||Session.isLocked())return;')
        p.write_text(timer)
        p = work / 'services/Recorder.qml'
        recorder = p.read_text()
        line = next(line for line in recorder.splitlines() if 'function stop()' in line)
        p.write_text(recorder.replace(line, '    property int testStops:0\n    function stop():void {testStops++;}'))
        settings = json.loads(args.settings.read_text()) if args.settings else SETTINGS
        source = SOURCE.replace('SETTINGS', json.dumps(settings)).replace('OUTPUT', str(out))
        (work / 'shell.qml').write_text(source)
        (out / 'fixture-sha256.json').write_text(json.dumps({name: hashlib.sha256((work / name).read_bytes()).hexdigest() for name in ('services/Media.qml', 'services/Radio.qml', 'services/FocusTimer.qml', 'services/Recorder.qml', 'shell.qml')}, indent=2))
        env = dict(os.environ, MODESTY_PREVIEW='1', QT_QPA_PLATFORM='offscreen',
                   QT_QUICK_BACKEND='rhi', QSG_RHI_BACKEND='opengl', QSG_INFO='1',
                   QS_NO_RELOAD_POPUP='1', QT_NO_XDG_DESKTOP_PORTAL='1', QT_QPA_PLATFORMTHEME='generic',
                   XDG_STATE_HOME=str(work / 'state'), XDG_CACHE_HOME=str(work / 'cache'),
                   XDG_CONFIG_HOME=str(work / 'config'))
        env.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
        result = subprocess.run(['dbus-run-session', '--', 'qs', '--no-color', '-p', str(work)],
                                env=env, capture_output=True, text=True, timeout=65)
        log = result.stdout + result.stderr
        (out / 'native.log').write_text(log)
        (out / 'exit-code.json').write_text(json.dumps({'exit_code': result.returncode}))
        rows = [json.loads(line.split('ACTIVITY ', 1)[1]) for line in log.splitlines() if 'ACTIVITY {' in line]
        (out / 'geometry.json').write_text(json.dumps(rows, indent=2))
        assert result.returncode == 0 and 'ACTIVITY HEADER PASS' in log, log
        assert not any(e in log for e in ('ReferenceError', 'TypeError', 'Unable to assign', 'Binding loop')), log
        assert 'OpenGL' in log, log
        paints = [json.loads(line.split('PAINT ', 1)[1]) for line in log.splitlines() if 'PAINT {' in line]
        for row in paints:
            row.update(painted_overlap(out / f"mask-{row['id']}-activity.png",
                                                     out / f"mask-{row['id']}-body.png",
                                                     row['activity'], row['body']))
        for row in paints:
            for label in ('activity','body'):
                row[label+'_ink']=Image.open(out/f"mask-{row['id']}-{label}.png").getchannel('A').getbbox()
        (out / 'painted-overlap.json').write_text(json.dumps(paints, indent=2))
        controls=[json.loads(line.split('MEASURE_CONTROL ',1)[1]) for line in log.splitlines() if 'MEASURE_CONTROL {' in line]
        for row in controls:
            if row['kind']=='clipping':
                row['raw_result']=painted_overlap(out/'control-clipping-activity.png',out/'control-clipping-raw.png',row['activity'],row['raw'])
                row['clipped_result']=painted_overlap(out/'control-clipping-activity.png',out/'control-clipping-clipped.png',row['activity'],row['clipped'])
                assert row['raw_result']['painted_overlap']>0 and row['clipped_result']['painted_overlap']==0, row
            else:
                row['stale_result']=painted_overlap(out/'control-timing-activity.png',out/'control-timing-body.png',row['activity'],row['request'])
                row['matched_result']=painted_overlap(out/'control-timing-activity.png',out/'control-timing-body.png',row['activity'],row['callback'])
                assert row['driftDetected'] and row['stale_result']['painted_overlap']>0 and row['matched_result']['painted_overlap']==0, row
        (out/'measurement-controls.json').write_text(json.dumps(controls,indent=2))
        assert len(controls)==2, controls
        assert paints and all(row['activity_ink'] for row in paints) and any(row['body_ink'] for row in paints), 'Paint masks must contain actual ink'
        assert all(row['synchronized'] and row['ancestorClipping'] for row in paints), paints
        assert not any(row['painted_overlap'] for row in paints), ('Activity/body ink overlap', paints)
        print('ACTIVITY HEADER PASS', len(rows), 'native observations')
        print('PAINTED OVERLAP PASS', len(paints), 'synchronized clipped candidate intersections')
        print('MEASUREMENT CONTROLS PASS', len(controls))
        for line in log.splitlines():
            if 'FLOOR ' in line:
                print(line)


if __name__ == '__main__':
    main()
