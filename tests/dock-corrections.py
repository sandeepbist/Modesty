#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MEDIA = '''pragma Singleton
import QtQuick
import Quickshell
Singleton {
 property bool hasSession:false;property bool playing:false;property var active:null;property var players:[]
 property string title:"Fixture";property string artist:"Artist";property string artUrl:""
 property real length:100;property real position:10;property real progress:.1
 property bool canSeek:false;property bool canRepeat:false;property bool canGoNext:false;property bool canGoPrevious:false
 property string repeatLabel:"Repeat unavailable";property string repeatIcon:"repeat";property int toggles:0
 function togglePlaying(){toggles++;}function next(){}function previous(){}function seekTo(value){}function cycleRepeat(){}
}'''
HEADER = '''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.components
ShellRoot {
 id:root
 FloatingWindow {id:window;visible:true;implicitWidth:1000;implicitHeight:700
  Island.IslandSurface {id:surface;availableWidth:1000;availableHeight:700}
 }
 TestCase {id:input;when:false}
 function check(ok,label){if(!ok)throw new Error(label);}
 function walk(item){let all=[item];for(const c of item.children||[])all=all.concat(walk(c));return all;}
 function child(name){const c=input.findChild(surface,name);check(!!c,"Missing "+name);return c;}
 function pane(stage,name){return walk(stage).find(c=>c.modelData===name&&c.selected&&c.item);}
 function waitPane(stage,name){const end=Date.now()+2500;while(Date.now()<end&&!(pane(stage,name)?.enabled))input.wait(10);const p=pane(stage,name);check(p?.enabled,"Pane disabled "+name);return p;}
 function geometry(){return [surface.mediaStage,surface.clockStage,surface.controlStage].map(s=>[s.x,s.y,s.width,s.height]);}
 function toggle(){const g=JSON.stringify(geometry()),v=surface.dockVelocity;IslandState.toggleDock();check(JSON.stringify(geometry())===g&&surface.dockVelocity===v,"Mode retarget reset frame or velocity");}
 function inside(item,stage,label){const p=item.mapToItem(stage,0,0),q=item.mapToItem(stage,item.width,item.height);check(item.height>0&&p.y>=stage.headerInset-.1&&q.y<=stage.height+.1,label+" viewport outside capsule "+JSON.stringify({p,q,height:stage.height}));}
 Component.onCompleted:{Quickshell.watchFiles=false;Preferences.motion="instant";Preferences.barHeight=35;Preferences.uiScale=.9;Preferences.collapsedWidth=105;Preferences.clusterGap=8;}
 Timer {interval:100;running:true;onTriggered:{try{
'''
FOOTER = '''
 console.log("DOCK CORRECTION PASS CASE");Qt.quit();
 }catch(e){console.error(e);Qt.exit(1);}}}
}'''
CASES = {
'finite-media': '''
 Preferences.innerPadding=15;Preferences.contextEvents=false;surface.scale=Qt.binding(()=>Preferences.uiScale);surface.transformOrigin=Item.TopLeft;
 Media.hasSession=true;Media.active=Qt.createQmlObject('import QtQuick;QtObject {property string identity:"Fixture player";property string trackAlbum:"Fixture album"}',root);
 FocusTimer.loaded=false;FocusTimer.phase="paused";FocusTimer.remaining=2315;FocusTimer.duration=3600;FocusTimer.deadline=0;
 function controls(card){return walk(card).find(c=>c instanceof IconButton&&c.label==="Play");}
 function fitted(card,play,label){
  const viewport=child("mediaViewport"),stage=surface.mediaStage,p=viewport.mapToItem(stage,0,0),q=viewport.mapToItem(stage,viewport.width,viewport.height),a=play.mapToItem(viewport,0,0);
  check(q.y<=stage.height+.01&&p.y>=stage.headerInset-.01,"Media viewport exceeds actual body aperture "+label+" "+JSON.stringify({p,q,height:stage.height,header:stage.headerInset}));
  check(play.activeFocus&&a.x>=-.01&&a.y>=-.01&&a.x+play.width<=viewport.width+.01&&a.y+play.height<=viewport.height+.01,"Focused Play is outside visible media viewport "+label+" "+JSON.stringify({focus:play.activeFocus,a,button:[play.width,play.height],viewport:[viewport.width,viewport.height],scroll:[viewport.contentX,viewport.contentY]}));
 }
 for(const height of [180,200]){
  Preferences.motion="instant";IslandState.closeMenu();IslandState.restingMode=IslandState.Pills;surface.availableWidth=1920;window.implicitWidth=1920;surface.availableHeight=height;input.wait(60);
  IslandState.openMenu("media");const loader=waitPane(surface.mediaStage,"media"),card=loader.item,play=controls(card);check(!!play,"Play fixture missing");input.wait(120);play.forceActiveFocus();input.wait(50);fitted(card,play,"wide-before");
  Preferences.motion="fluid";Preferences.motionSpeed=.5;surface.availableWidth=330;window.implicitWidth=330;input.wait(1100);
  check(IslandState.restingMode===IslandState.Pills&&surface.dockProgress===1,"Resize did not select temporary shared header");
  check(loader.item===card&&play.activeFocus,"Finite resize recreates media or loses focus");fitted(card,play,"retained-narrow-"+height);
  const count=Media.toggles;input.mouseClick(play,play.width/2,play.height/2);check(Media.toggles===count+1,"Visible finite Play cannot activate exactly once");
  card.forceActiveFocus();const viewport=child("mediaViewport");viewport.contentY=10;input.wait(30);surface.availableWidth=1920;window.implicitWidth=1920;input.wait(1100);
  const expectedScroll=Math.min(10,Math.max(0,viewport.contentHeight-viewport.height));
  check(loader.item===card&&Math.abs(viewport.contentY-expectedScroll)<.01,"Finite viewport loses feasible reading scroll "+JSON.stringify({same:loader.item===card,scroll:viewport.contentY,expectedScroll,viewportHeight:viewport.height,contentHeight:viewport.contentHeight,cardFocus:card.activeFocus,playFocus:play.activeFocus,mode:surface.dockProgress}));
  Preferences.motion="instant";IslandState.closeMenu();input.wait(60);IslandState.restingMode=IslandState.Dock;surface.availableWidth=330;window.implicitWidth=330;IslandState.openMenu("media");
  const fresh=waitPane(surface.mediaStage,"media");input.wait(80);check(fresh.opacity>.99&&fresh.visibleScale>.995,"Fresh finite Media never completes reveal");
  const freshPlay=controls(fresh.item);freshPlay.forceActiveFocus();input.wait(40);fitted(fresh.item,freshPlay,"fresh-dock-"+height);
 }
''',
'activity-routes': '''
 surface.availableWidth=330;window.implicitWidth=330;surface.scale=Qt.binding(()=>Preferences.uiScale);surface.transformOrigin=Item.TopLeft;
 Preferences.uiScale=1.25;Preferences.showSeconds=true;Preferences.use24Hour=true;Preferences.contextEvents=false;
 Audio.directCameras=[{directCamera:true,label:"Fixture camera"}];IslandState.restingMode=IslandState.Dock;
 const configured=ControlLayout.items;ControlLayout.remove("focus");ControlLayout.remove("recorder");const savedLayout=JSON.stringify(ControlLayout.items);
 for(const kind of ["focus","recorder","dual"]){
  IslandState.closeMenu();FocusTimer.loaded=false;FocusTimer.duration=7200;FocusTimer.remaining=7200;FocusTimer.deadline=0;FocusTimer.phase=kind==="recorder"?"idle":"paused";
  Recorder.status={phase:kind==="focus"?"idle":"recording",elapsed:127};input.wait(100);
  const more=child("dockOverflow"),activity=child("compactActivity");check(more.visible&&more.enabled&&activity.width===0,"Displaced activity fixture did not fit expected branch");
  for(const route of kind==="dual"?["focus","recorder"]:[kind]){
   input.mouseClick(more,more.width/2,more.height/2);const center=waitPane(surface.controlStage,"quicksettings").item;input.wait(100);
   const action=walk(center).find(c=>c instanceof ActionButton&&c.visible&&c.enabled&&c.Accessible.name.startsWith(route==="focus"?"Focus timer":"Recording"));
   check(!!action,"More loses displaced "+route+" route when its tile is removed");
   const stage=surface.controlStage,top=action.mapToItem(stage,0,0),bottom=action.mapToItem(stage,action.width,action.height);
   check(top.x>=-.01&&bottom.x<=stage.width+.01&&top.y>=stage.headerInset-.01&&bottom.y<=stage.height+.01,"Disclosed activity action outside painted capsule "+JSON.stringify({route,top,bottom,width:stage.width,height:stage.height,header:stage.headerInset}));
   check(more.Accessible.name.includes(route==="focus"?"Focus timer":"Recording"),"More accessible label omits displaced activity");
   action.forceActiveFocus();input.wait(50);input.keyClick(Qt.Key_Return);input.wait(30);
   check(IslandState.menu===route&&center.detail===route,"Ongoing action did not open existing "+route+" detail");
   input.tryVerify(()=>center.diagnostics().panes.some(p=>p.name===route&&p.enabled),2500,"Ongoing detail never became usable");
   check(JSON.stringify(ControlLayout.items)===savedLayout,"Activity disclosure restores a removed tile or changes layout");IslandState.closeMenu();input.wait(80);
  }
 }
 ControlLayout.items=configured;
''',
'normal-privacy': '''
 Preferences.contextEvents=false;Preferences.showSeconds=false;Preferences.use24Hour=true;Preferences.privacyIndicatorGap=25;
 FocusTimer.loaded=false;FocusTimer.phase="idle";AgentWork.pulse=false;Audio.directCameras=[{directCamera:true,label:"Fixture camera"}];IslandState.restingMode=IslandState.Pills;
 Preferences.privacyIndicatorRightPadding=19;input.wait(80);const reference=geometry();
 for(const padding of [0,4,8,19,40]){
  Preferences.privacyIndicatorRightPadding=padding;input.wait(40);const current=geometry(),delta=padding-19;
  check(Math.abs(current[1][2]-reference[1][2]-delta)<.01&&Math.abs(current[2][0]-reference[2][0]-delta)<.01,"Dock minimum changes normal privacy padding "+JSON.stringify({padding,reference,current}));
  check(Math.abs(current[0][0]-reference[0][0])<.01&&Math.abs(current[1][0]-reference[1][0])<.01,"Normal privacy padding shifts original media or clock");
  console.log("NORMAL PRIVACY",JSON.stringify({padding,stages:current}));
 }
''',
'provider-motion': '''
 Preferences.contextEvents=false;Preferences.privacyIndicatorRightPadding=19;Audio.directCameras=[{directCamera:true,label:"Fixture camera"}];
 const viewport=walk(surface).find(c=>c instanceof Island.ClockViewport),privacy=walk(viewport).find(c=>c instanceof PrivacyIndicator),lamp=privacy.children.find(c=>c.width===privacy.dotSize&&c.height===privacy.dotSize),clock=walk(viewport).find(c=>c instanceof RollingText&&c.text===Time.timeStr);
 function bounds(item){const p=item.mapToItem(surface,0,0),q=item.mapToItem(surface,item.width,item.height);return {x:p.x,y:p.y,right:q.x,bottom:q.y};}
 function paintedBounds(item){const box=bounds(item);for(let c=item.parent;c;c=c.parent)if(c.clip){const clip=bounds(c);box.x=Math.max(box.x,clip.x);box.y=Math.max(box.y,clip.y);box.right=Math.min(box.right,clip.right);box.bottom=Math.min(box.bottom,clip.bottom);}return box;}
 let observations=0;
 for(const crisp of [false,true])for(const name of ["OpenCode ×12","Provider with a considerably longer name ×123"])for(const gap of [0,25,40]){
  Preferences.crispText=crisp;
  Preferences.motion="instant";IslandState.restingMode=IslandState.Pills;Preferences.privacyIndicatorGap=gap;AgentWork.providerLabel=name;AgentWork.pulse=true;input.wait(80);
  const label=walk(surface.clockStage).find(c=>c instanceof RollingText&&c.text===name);check(!!label,"Provider label missing");
  Preferences.motion="fluid";Preferences.motionSpeed=.65;
  for(const mode of [IslandState.Dock,IslandState.Pills]){
   IslandState.restingMode=mode;
   for(let i=0;i<90;i++){
    input.wait(5);const p=surface.dockProgress;if(p<=0||p>=1)continue;
    const text=paintedBounds(label),dot=paintedBounds(lamp),area=Math.max(0,Math.min(text.right,dot.right)-Math.max(text.x,dot.x))*Math.max(0,Math.min(text.bottom,dot.bottom)-Math.max(text.y,dot.y));
    check(area<.001,"Privacy lamp enters painted provider text during mode motion "+JSON.stringify({name,gap,mode,p,velocity:surface.dockVelocity,text,dot,area}));
    const time=paintedBounds(clock),timeArea=Math.max(0,Math.min(text.right,time.right)-Math.max(text.x,time.x))*Math.max(0,Math.min(text.bottom,time.bottom)-Math.max(text.y,time.y));
    check(timeArea<.001,"Provider retirement overlaps returning clock "+JSON.stringify({p,text,time,timeArea}));observations++;
   }
  }
 }
 check(observations>20,"Provider motion fixture missed transition frames");console.log("PROVIDER MOTION OBSERVATIONS",observations);
''',
'provider-privacy': '''
 Preferences.privacyIndicatorGap=25;Preferences.privacyIndicatorRightPadding=19;Preferences.contextEvents=false;IslandState.restingMode=IslandState.Pills;
 Audio.directCameras=[{directCamera:true,label:"Fixture camera"}];AgentWork.providerLabel="OpenCode ×12";AgentWork.pulse=true;input.wait(80);
 const viewport=walk(surface).find(c=>c instanceof Island.ClockViewport),privacy=walk(viewport).find(c=>c instanceof PrivacyIndicator);
 const label=walk(surface.clockStage).find(c=>c instanceof RollingText&&c.text===AgentWork.providerLabel);
 check(label?.visible&&surface.agentReveal===1&&privacy.visible,"Provider privacy fixture did not appear");
 const labelRight=label.mapToItem(surface,label.width,0).x,dotLeft=privacy.mapToItem(surface,(privacy.width-privacy.dotSize)/2,0).x;
 check(dotLeft-labelRight>=Preferences.privacyIndicatorGap-.01,"Privacy lamp overlaps provider label "+JSON.stringify({labelRight,dotLeft,gap:Preferences.privacyIndicatorGap}));
''',
'level-motion': '''
 Preferences.contextEvents=true;Preferences.contextVolume=true;Preferences.contextBrightness=true;Preferences.contextDuration=5000;
 const viewport=walk(surface).find(c=>c instanceof Island.ClockViewport),feedback=walk(viewport).find(c=>c instanceof Island.ContextPanel),label=walk(viewport).find(c=>c instanceof RollingText&&c.text===Time.timeStr);
 let observations=0;
 for(const mode of [IslandState.Pills,IslandState.Dock])for(const kind of ["volume","brightness"]){
  Preferences.motion="instant";Context.clear();IslandState.restingMode=mode;input.wait(40);Preferences.motion="fluid";Preferences.motionSpeed=.5;
  Context.show(kind,kind,kind==="volume"?"volume_up":"light_mode",.6);
  for(const arriving of [true,false]){
   if(!arriving)Context.clear();
   for(let i=0;i<24;i++){
    input.wait(20);
    if(viewport.levelAmount>0&&viewport.levelAmount<1&&feedback.visible&&label.visible){
     const top=feedback.mapToItem(viewport,0,0).y,bottom=label.mapToItem(viewport,0,label.height).y;
     check(top>=bottom-.01,"Level entrance overlaps clock "+JSON.stringify({mode,kind,arriving,amount:viewport.levelAmount,top,bottom}));observations++;
    }
   }
  }
 }
 check(observations>2,"Level motion fixture missed transition frames");console.log("LEVEL MOTION OBSERVATIONS",observations);
''',
'recording-label': '''
 surface.availableWidth=330;IslandState.restingMode=IslandState.Dock;FocusTimer.loaded=false;FocusTimer.phase="idle";
 for(const phase of ["preparing","countdown"]){
  Recorder.status={phase,remaining:3,elapsed:0};input.wait(60);
  const activity=child("compactActivity"),view=walk(activity).find(c=>c instanceof Island.RecordingStatus),detail=child("recorderDetail");
  check(view?.condensed&&activity.visible,"Recording label fixture is not condensed");
  const label=walk(view).find(c=>c instanceof PanelText&&c.text);
  const expected=phase==="countdown"?"In 3":"Preparing";
  check(label?.text===expected,"Compact recorder misreports startup "+JSON.stringify({phase,expected,actual:label?.text}));
  check(detail.Accessible.name.includes(Recorder.label),"Recorder accessibility loses phase label "+detail.Accessible.name);
 }
''',
'privacy-fit': '''
 surface.availableWidth=330;window.implicitWidth=330;surface.scale=Qt.binding(()=>Preferences.uiScale);surface.transformOrigin=Item.TopLeft;
 Preferences.contextEvents=false;Preferences.use24Hour=true;IslandState.restingMode=IslandState.Dock;
 FocusTimer.loaded=false;FocusTimer.duration=7200;FocusTimer.remaining=7200;FocusTimer.deadline=0;FocusTimer.phase="paused";
 Audio.directCameras=[{directCamera:true,label:"Fixture camera"}];
 const viewport=walk(surface).find(c=>c instanceof Island.ClockViewport),privacy=walk(viewport).find(c=>c instanceof PrivacyIndicator),more=child("dockOverflow"),activity=child("compactActivity");
 const label=walk(viewport).find(c=>c instanceof RollingText&&c.text===Time.timeStr);
 function bounds(item){const p=item.mapToItem(window.contentItem,0,0),q=item.mapToItem(window.contentItem,item.width,item.height);return {x:p.x,right:q.x};}
 let observations=0;
 for(const scale of [.85,.9,.95,1,1.05,1.1,1.15,1.2,1.25])for(const seconds of [false,true])for(const gap of [0,25,40])for(const padding of [0,19,40]){
  Preferences.uiScale=scale;Preferences.showSeconds=seconds;Preferences.privacyIndicatorGap=gap;Preferences.privacyIndicatorRightPadding=padding;input.wait(10);
  const enclosure=bounds(surface.clockStage),disclosure=bounds(more),indicator=bounds(privacy),clock=bounds(label);
  const evidence=JSON.stringify({scale,seconds,gap,padding,enclosure,disclosure,indicator,activityWidth:activity.width,rightNeed:surface.dockRightNeed,rightCapacity:surface.rightCapacity});
  check(surface.compactDisclosure&&more.visible&&more.enabled&&more.width>=20,"Narrow controls route missing "+evidence);
  check(enclosure.x>=15.99&&enclosure.right<=314.01,"Narrow enclosure exceeds screen margin "+evidence);
  check(disclosure.x>=enclosure.x&&disclosure.right<=enclosure.right+.01,"More outside painted enclosure "+evidence);
  check(indicator.right<=disclosure.x+.01&&indicator.x>=enclosure.x&&indicator.right<=enclosure.right+.01,"Privacy target outside enclosure or overlaps disclosure "+evidence);
  check(surface.dockHeaderSupported&&surface.dockRightNeed<=surface.rightCapacity+.01,"Right allocation exceeds measured capacity "+evidence);
  check(Math.abs((clock.x+clock.right)/2-165)<.02,"Narrow clock leaves screen center "+evidence);
  observations++;
 }
 input.mouseClick(more,more.width/2,more.height/2);input.wait(50);check(IslandState.menu==="quicksettings","Visible More route cannot open controls");
 console.log("PRIVACY FIT OBSERVATIONS",observations);
''',
'media-clearance': '''
 Media.hasSession=true;Preferences.contextEvents=false;
 function pose(){const s=surface.mediaStage;return {p:surface.dockProgress,velocity:surface.dockVelocity,height:s.height,naturalHeight:s.naturalHeight,dockHeight:surface.dockHeight,header:s.headerInset};}
 function continuous(action,label){const before=pose();action();const after=pose();check(before.p===after.p&&before.velocity===after.velocity,"Media action resets dock spring "+label);check(Math.abs(before.height-after.height)<.000001&&Math.abs(before.header-after.header)<.000001,"Media action steps enclosure geometry "+label+" "+JSON.stringify({before,after}));console.log("MEDIA CONTINUITY",label,JSON.stringify({before,after}));}
 for(const width of [1920,330]){
  Preferences.motion="instant";IslandState.closeMenu();IslandState.restingMode=IslandState.Pills;surface.availableWidth=width;window.implicitWidth=width;input.wait(80);
  Preferences.motion="fluid";Preferences.motionSpeed=.65;IslandState.restingMode=IslandState.Dock;input.wait(80);
  check(surface.dockProgress>.05&&surface.dockProgress<.95,"Opening fixture is not mid-transition");
  continuous(()=>IslandState.openMenu("media"),"open-"+width);input.wait(45);
  continuous(()=>IslandState.closeMenu(),"close-"+width);input.wait(30);
  continuous(()=>IslandState.openMenu("media"),"reactivate-"+width);input.wait(900);
  check(surface.mediaStage.headerInset===35&&surface.mediaStage.height<=surface.maximumHeight,"Settled media clearance remains nonzero");
  IslandState.restingMode=IslandState.Pills;input.wait(80);
  check(surface.dockProgress>.05&&surface.dockProgress<.95,"Closing fixture is not mid-transition");
  continuous(()=>IslandState.closeMenu(),"reverse-close-"+width);input.wait(30);
  continuous(()=>IslandState.openMenu("media"),"reverse-reactivate-"+width);input.wait(900);
  IslandState.closeMenu();input.wait(900);
 }
''',
'media': '''
 Preferences.mediaAutoHide=true;IslandState.restingMode=IslandState.Dock;IslandState.openMenu("media");
 const p=waitPane(surface.mediaStage,"media"),card=p.item;
 check(surface.mediaStage.opacity>.99,"Selected no-session MediaCard hidden");
 Media.hasSession=true;input.wait(100);Preferences.showAlbum=false;input.wait(250);
 check(p.item===card&&surface.mediaStage.opacity>.99,"showAlbum hides selected MediaCard");
 Preferences.showAlbum=true;surface.availableWidth=300;
 const marks=walk(surface).find(c=>c instanceof Island.WorkspaceMarks);
 const monitor=Qt.createQmlObject('import QtQuick;QtObject {property var activeWorkspace:null}',root);surface.monitor=monitor;
 marks.workspaces=Array.from({length:6},(_,i)=>({id:i+1,name:String(i+1),monitor,activate:()=>{}}));input.wait(250);
 check(surface.dockMediaFits&&surface.mediaStage.opacity>.99,"Header discards media that fits");
 surface.availableWidth=120;input.wait(250);
 check(!surface.dockMediaFits&&surface.mediaStage.opacity>.99,"Forced header suppression hides selected MediaCard");
 surface.availableWidth=1000;Media.hasSession=false;input.wait(1000);
 check(p.item===card&&p.enabled&&surface.mediaStage.opacity>.99,"Session loss hides active MediaCard");
 card.forceActiveFocus();Preferences.motion="fluid";IslandState.closeMenu();
 input.wait(20);check(p.opacity>.01&&surface.mediaStage.opacity>.9,"Retiring MediaCard hidden by accessory suppression");
 input.wait(1100);check(surface.mediaStage.opacity<.01,"Absent optional resting media remains visible");
 Preferences.motion="instant";IslandState.restingMode=IslandState.Pills;Preferences.mediaAutoHide=false;input.wait(50);
 check(surface.mediaStage.opacity>.99,"Ordinary empty media pill behavior changed");
''',
'levels': '''
 Preferences.contextEvents=true;Preferences.contextVolume=true;Preferences.contextBrightness=true;Preferences.contextDuration=1100;
 IslandState.restingMode=IslandState.Dock;Context.show("volume","Volume","volume_up",.4);input.wait(150);
 const viewport=walk(surface).find(c=>c instanceof Island.ClockViewport),feedback=walk(viewport).find(c=>c instanceof Island.ContextPanel);
 function level(kind,value){check(feedback.visible&&feedback.opacity>.99,"Dock "+kind+" feedback invisible");check(feedback.kind===kind&&Math.abs(feedback.value-value)<.001,"Feedback stale");inside(feedback,surface.clockStage,kind);check(viewport.clockOpacity>.99,"Level hides centered time");}
 level("volume",.4);const event=Context.event;
 const label=walk(viewport).find(c=>c instanceof RollingText&&c.text===Time.timeStr);
 check(!!label&&Math.abs(label.mapToItem(surface,label.width/2,0).x-surface.width/2)<.01,"Level displaces centered time");
 Preferences.motion="fluid";toggle();input.wait(60);toggle();input.wait(700);
 check(Context.event===event&&Context.active,"Mode changes Context identity or deadline");
 Context.show("volume","Volume","volume_up",.8);input.wait(80);level("volume",.8);
 Context.show("brightness","Brightness","light_mode",.6);input.wait(80);level("brightness",.6);
 Preferences.contextBrightness=false;const current=Context.event;Context.show("brightness","Brightness","light_mode",.1);
 check(Context.event===current,"Feedback bypasses preference");Preferences.contextBrightness=true;
 input.wait(1100);check(!Context.active,"Mode rewrites Context expiry");
 Preferences.motion="instant";IslandState.restingMode=IslandState.Pills;Context.show("volume","Volume","volume_up",.3);input.wait(50);
 check(feedback.visible&&feedback.y===0&&surface.clockStage.height===35,"Pill level endpoint changed");
 Preferences.motion="fluid";Preferences.motionSpeed=.5;toggle();input.wait(90);toggle();input.wait(20);
 const g=JSON.stringify(geometry()),v=surface.dockVelocity;Context.show("brightness","Brightness","light_mode",.7);
 check(JSON.stringify(geometry())===g&&surface.dockVelocity===v,"Level arrival resets moving reversal");
 toggle();input.wait(1000);level("brightness",.7);
''',
'body': '''
 surface.availableHeight=200;IslandState.restingMode=IslandState.Dock;IslandState.openMenu("notes");
 const notes=waitPane(surface.clockStage,"notes"),menu=notes.item;input.wait(100);
 check(notes.opacity>.99&&notes.visibleScale>=.995,"Short Notes never completes reveal");
 const held=[notes.heldWidth,notes.heldHeight],body=child("notesBody"),scroll=child("notesScroll"),actions=child("notesActions");
 body.text=Array.from({length:100},(_,i)=>"Reading line "+i).join("\\n");body.cursorPosition=0;input.wait(100);scroll.contentY=60;
 check(scroll.contentY>0,"Notes reading scroll fixture empty");const reading=scroll.contentY;
 body.forceActiveFocus();inside(scroll,surface.clockStage,"Notes");inside(actions,surface.clockStage,"Notes actions");
 const popup=input.findChild(menu,"notesOverflow");popup.open();input.wait(50);check(popup.visible&&surface.popupInputRegion,"Notes popup inaccessible");
 Preferences.motion="fluid";toggle();input.wait(800);toggle();input.wait(800);
 check(notes.item===menu&&notes.heldWidth===held[0]&&notes.heldHeight===held[1],"Mode recreates Notes or changes held layout");
 check(popup.visible&&surface.popupInputRegion&&scroll.contentY===reading,"Mode loses Notes popup or nonzero scroll");
 popup.close();body.forceActiveFocus();check(body.activeFocus,"Notes editor cannot focus");
 actions.forceActiveFocus();input.keyClick(Qt.Key_Space);input.wait(40);check(popup.visible,"Short Notes popup cannot open by keyboard");
 check(popup.contentItem.contentHeight>popup.contentItem.height,"Short Notes popup needs a scroll viewport");
 let insertion=null;for(let i=0;i<popup.count;i++)if(popup.itemAt(i).text==="Insert task"){insertion=popup.itemAt(i);popup.contentItem.positionViewAtIndex(i,ListView.Contain);}
 input.wait(40);check(insertion?.enabled,"Scrolled Notes action unreachable");const draft=body.text;insertion.triggered();input.wait(40);
 check(body.text.includes("- [ ] ")&&body.text.length>draft.length,"Scrolled Notes action failed");popup.close();
 IslandState.closeMenu();Preferences.motion="instant";input.wait(100);
 function notification(){Notifications.previewNotify(0);const n=Notifications.list[0];n.summary="Long actionable notification";n.body="Reading body ".repeat(80);n.localActions=Array.from({length:8},(_,i)=>({identifier:"action"+i,text:"Action button "+i,invoke:()=>root.objectName="invoked"+i}));return n;}
 const record=notification(),toast=waitPane(surface.clockStage,"toast"),stack=toast.item;input.wait(100);
 const card=child("popupCard"),viewport=child("notificationScroll"),toastHeld=[toast.heldWidth,toast.heldHeight];
 check(toast.opacity>.99&&toast.visibleScale>=.995,"Short toast never completes reveal");inside(viewport,surface.clockStage,"Toast");
 viewport.contentY=50;check(viewport.contentY>0,"Toast reading scroll fixture empty");const y=viewport.contentY;
 input.mouseMove(viewport,viewport.width/2,50);input.wait(30);check(record.popupHovered,"Nonzero-scroll reading hover missing");const shown=stack.shown;
 Preferences.motion="fluid";toggle();input.wait(800);toggle();input.wait(800);
 check(toast.item===stack&&stack.shown===shown&&card.notification===record,"Mode changes toast identity");
 check(toast.heldWidth===toastHeld[0]&&toast.heldHeight===toastHeld[1]&&viewport.contentY===y,"Mode loses nonzero toast scroll or held layout");check(record.popupHovered,"Mode loses stationary nonzero-scroll reading hover");
 inside(viewport,surface.clockStage,"Retained toast");
 const action=walk(card).find(c=>c.text==="Action button 7");check(!!action,"Last action missing");action.forceActiveFocus();input.wait(50);inside(action,surface.clockStage,"Focused last action");
 action.clicked();check(root.objectName==="invoked7","Retained notification action failed");
''',
'bounds': '''
 surface.availableWidth=330;surface.availableHeight=200;IslandState.restingMode=IslandState.Dock;Media.hasSession=true;input.wait(30);
 const marks=walk(surface).find(c=>c instanceof Island.WorkspaceMarks);
 const monitor=Qt.createQmlObject('import QtQuick;QtObject {property var activeWorkspace:null}',root);surface.monitor=monitor;
 Preferences.motion="fluid";Preferences.motionSpeed=.5;
 marks.workspaces=Array.from({length:6},(_,i)=>({id:i+1,name:String(i+1),monitor,activate:()=>{}}));IslandState.openMenu("notes");
 let maximumHeight=0,minimumMargin=Infinity;
 function sample(){maximumHeight=Math.max(maximumHeight,surface.dockHeight);minimumMargin=Math.min(minimumMargin,surface.dockX*.9);check(surface.dockHeight<=surface.maximumHeight+.001,"Dock height exceeds finite bound "+surface.dockHeight+" > "+surface.maximumHeight);check(surface.dockX*.9>=15.999,"Dock width violates 16px margin "+surface.dockX*.9);}
 for(let i=0;i<160;i++){input.wait(5);sample();}
 Media.hasSession=false;for(let i=0;i<210;i++){input.wait(5);sample();}
 Media.hasSession=true;for(let i=0;i<160;i++){input.wait(5);sample();}
 surface.availableWidth=260;surface.availableHeight=180;sample();for(let i=0;i<100;i++){input.wait(5);sample();}
 toggle();input.wait(80);toggle();for(let i=0;i<160;i++){input.wait(5);sample();}
 console.log("BOUNDS",JSON.stringify({maximumHeight,minimumMargin}));
''',
'focused-action': '''
 surface.availableHeight=200;IslandState.restingMode=IslandState.Pills;
 Notifications.previewNotify(0);const record=Notifications.list[0];record.body="Reading body ".repeat(80);
 record.localActions=Array.from({length:8},(_,i)=>({identifier:"action"+i,text:"Action button "+i,invoke:()=>root.objectName="invoked"+i}));
 const loader=waitPane(surface.clockStage,"toast"),stack=loader.item,card=child("popupCard"),scroll=child("notificationScroll");input.wait(120);
 const action=walk(card).find(c=>c.text==="Action button 7");check(!!action,"Last action absent");action.forceActiveFocus();input.wait(100);
 function visibleAction(){const p=action.mapToItem(scroll,0,0);check(p.y>=-.1&&p.y+action.height<=scroll.height+.1,"Retained focused action is clipped by viewport");check(action.activeFocus&&loader.item===stack&&stack.shown===record,"Mode loses focused action identity");}
 visibleAction();Preferences.motion="fluid";toggle();input.wait(900);visibleAction();
 toggle();input.wait(900);visibleAction();toggle();input.wait(55);toggle();input.wait(900);visibleAction();
 card.forceActiveFocus();input.wait(40);scroll.contentY=40;input.wait(40);const reading=scroll.contentY;
 check(reading>0,"Card reading fixture needs nonzero scroll");toggle();input.wait(900);toggle();input.wait(900);
 check(scroll.contentY===reading&&card.activeFocus,"Viewport change resets whole-card reading scroll");
 action.forceActiveFocus();input.wait(50);visibleAction();input.keyClick(Qt.Key_Space);check(root.objectName==="invoked7","Retained keyboard action failed");
''',
'moving-toast': '''
 surface.availableHeight=200;Preferences.motion="fluid";Preferences.motionSpeed=.5;IslandState.restingMode=IslandState.Dock;input.wait(100);toggle();input.wait(25);
 check(surface.dockProgress>0&&surface.dockProgress<1&&surface.dockVelocity!==0,"Arrival fixture is not moving");
 const g=JSON.stringify(geometry()),v=surface.dockVelocity;Notifications.previewNotify(0);
 check(JSON.stringify(geometry())===g&&surface.dockVelocity===v,"Notification arrival resets moving reversal");
 const record=Notifications.list[0];record.body="Reading ".repeat(100);record.localActions=Array.from({length:8},(_,i)=>({identifier:"action"+i,text:"Action button "+i,invoke:()=>{}}));
 toggle();const toast=waitPane(surface.clockStage,"toast"),stack=toast.item;input.wait(1000);
 const scroll=child("notificationScroll"),card=child("popupCard");card.forceActiveFocus();check(scroll.contentHeight>scroll.height+40,"Moving toast must overflow viewport");scroll.contentY=40;input.wait(50);check(scroll.contentY>0,"Moving toast nonzero scroll missing");const y=scroll.contentY;
 const focus=window.activeFocusItem;toggle();input.wait(50);toggle();input.wait(900);
 check(stack===toast.item&&stack.shown===record&&card.notification===record&&scroll.contentY===y,"Moving notification loses identity or reading scroll "+JSON.stringify({sameStack:stack===toast.item,sameShown:stack.shown===record,sameRecord:card.notification===record,y,before:y,after:scroll.contentY,contentHeight:scroll.contentHeight,height:scroll.height}));
 check(window.activeFocusItem===focus,"Moving notification loses focus");
 Notifications.dismiss(record);input.wait(900);check(!record.popup,"Moving notification dismissal failed");
'''
}


notes, toast = CASES.pop('body').split(' IslandState.closeMenu();Preferences.motion="instant";input.wait(100);', 1)
CASES['notes'] = notes
CASES['toast'] = 'surface.availableHeight=200;IslandState.restingMode=IslandState.Dock;\n' + toast


def run_case(name):
    marker = 'DOCK CORRECTION PASS ' + name
    with tempfile.TemporaryDirectory(prefix='modesty-correction-') as directory:
        work = Path(directory)
        for folder in ('components', 'modules', 'assets', 'theme', 'scripts'):
            (work / folder).symlink_to(ROOT / folder)
        (work / 'services').mkdir()
        for path in (ROOT / 'services').iterdir():
            if path.name != 'Media.qml':
                (work / 'services' / path.name).symlink_to(path)
        (work / 'services/Media.qml').write_text(MEDIA)
        (work / 'shell.qml').write_text(HEADER + CASES[name] + FOOTER.replace('DOCK CORRECTION PASS CASE', marker))
        env = dict(os.environ, MODESTY_PREVIEW='1', QT_QPA_PLATFORM='offscreen',
                   QSG_RHI_BACKEND='software', QS_NO_RELOAD_POPUP='1',
                   QT_NO_XDG_DESKTOP_PORTAL='1', QT_QPA_PLATFORMTHEME='generic',
                   XDG_STATE_HOME=str(work / 'state'), XDG_CACHE_HOME=str(work / 'cache'))
        result = subprocess.run(['dbus-run-session', '--', 'qs', '--no-color', '-p', str(work)],
                                env=env, capture_output=True, text=True, timeout=40)
        log = result.stdout + result.stderr
        if result.returncode or marker not in log or any(e in log for e in ('ReferenceError', 'TypeError', 'Unable to assign')):
            print(log)
            return False
        print(marker)
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=CASES)
    args = parser.parse_args()
    results = [run_case(name) for name in ([args.case] if args.case else CASES)]
    raise SystemExit(not all(results))
