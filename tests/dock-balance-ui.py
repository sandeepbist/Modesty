#!/usr/bin/env python3
from pathlib import Path
from unittest.mock import patch
import tempfile
import qml

STUBS={
'Time':'property string timeStr:"02:49";property date date:new Date(2026,9,25,2,49)',
'Media':'''property bool hasSession:true;property bool playing:false;property var active:null;property var players:[]
 property string title:"Long title العربية हिन्दी 日本語";property string artist:"Fixture";property string artUrl:""
 property real length:100;property real position:10;property real progress:.1
 property bool canSeek:false;property bool canRepeat:false;property bool canGoNext:false;property bool canGoPrevious:false
 property string repeatLabel:"Repeat unavailable";property string repeatIcon:"repeat"
 function togglePlaying(){}function next(){}function previous(){}function seekTo(value){}function cycleRepeat(){}''',
'FocusTimer':'''property string phase:"running";property bool loaded:false;property string kind:"focus"
 property int duration:7200;property int remaining:7200;property double deadline:0;property string error:""
 property int pauses:0;property int cancels:0;readonly property bool active:phase!=="idle"
 readonly property string label:"Focus";readonly property real progress:0
 readonly property string timeText:String(Math.floor(remaining/60)).padStart(duration>=6000?3:2,"0")+":"+String(remaining%60).padStart(2,"0")
 function pause(){pauses++;}function cancel(){cancels++;}function start(minutes,isBreak){}''',
'Recorder':'''property var status:({phase:"idle",elapsed:127});readonly property string phase:status.phase
 readonly property bool active:phase!=="idle";readonly property bool selecting:false;readonly property bool recording:["recording","paused"].includes(phase)
 readonly property string timeText:Math.floor(status.elapsed/60)+":"+String(status.elapsed%60).padStart(2,"0")
 readonly property string label:phase==="recording"?timeText:phase==="paused"?"Paused · "+timeText:phase==="saving"?"Saving…":"Preparing…"
 property int stops:0;function stop(){stops++;}function start(region,sound){}function pause(){}function openFolder(){}'''
}
SOURCE=r'''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.components
import qs.theme
ShellRoot {
 id:root
 property int activations:0
 property QtObject monitor:QtObject {property string name:"fixture";property var activeWorkspace:null}
 Component {id:workspace;QtObject {property int id:0;property string name:"";property var monitor;property bool urgent:false;function activate(){root.activations++;root.monitor.activeWorkspace=this;}}}
 FloatingWindow {id:window;visible:true;implicitWidth:1920;implicitHeight:750
  Island.IslandSurface {id:surface;availableWidth:1920;availableHeight:750;scale:Preferences.uiScale;transformOrigin:Item.TopLeft;monitor:root.monitor}
 }
 TestCase {id:input;when:false}
 function check(ok,label){if(!ok)throw new Error(label);}
 function walk(item){let a=[item];for(const c of item.children||[])a=a.concat(walk(c));return a;}
 function child(name){const c=input.findChild(surface,name);check(!!c,"Missing "+name);return c;}
 function bounds(item){const a=item.mapToItem(surface,0,0),b=item.mapToItem(surface,item.width,item.height);return {x:a.x,y:a.y,w:b.x-a.x,h:b.y-a.y};}
 function edgeClick(item,right){const a=item.mapToItem(window.contentItem,0,0),b=item.mapToItem(window.contentItem,item.width,item.height);input.mouseClick(window.contentItem,right?Math.floor(b.x)-1:Math.ceil(a.x),Math.round((a.y+b.y)/2));}
 function members(count){const a=[];for(let i=0;i<count;i++)a.push(workspace.createObject(root,{id:i+1,name:String(i+1),monitor}));marks.workspaces=a;monitor.activeWorkspace=a[0]??null;input.wait(50);return a;}
 property var marks:null
 property var label:null
 function record(name){console.log("BALANCE_CASE "+JSON.stringify({name,width:surface.availableWidth,compact:surface.compactDisclosure,workspace:bounds(marks),contentX:marks.contentX,clock:bounds(label),mediaFits:surface.dockMediaFits,privacyGap:Preferences.privacyIndicatorGap,privacyPadding:Preferences.privacyIndicatorRightPadding}));}
 Component.onCompleted:{Quickshell.watchFiles=false;Preferences.motion="instant";Preferences.barHeight=35;Preferences.uiScale=.9;Preferences.collapsedWidth=105;Preferences.clusterGap=8;Preferences.contextEvents=false;IslandState.restingMode=IslandState.Dock;marks=walk(surface).find(c=>c instanceof Island.WorkspaceMarks);label=walk(surface).find(c=>c instanceof RollingText&&c.text===Time.timeStr);}
 Timer {interval:120;running:true;onTriggered:{try{
  for(const width of [1920,600,330])for(const count of [0,1,3,6,9]){surface.availableWidth=width;window.implicitWidth=width;const a=members(count);check(Math.abs(marks.width/20-Math.round(marks.width/20))<.001,"Partial workspace target viewport");check(marks.width<=100,"More than five targets reserved");check(marks.contentWidth===20*count,"Workspace pitch differs from target");const buttons=marks.contentItem.children.filter(c=>c instanceof AbstractButton);for(const b of buttons)check(b.width===20&&b.height>=20&&b.x===b.index*20,"Workspace target smaller than 20 logical px");if(count){monitor.activeWorkspace=a[count-1];input.wait(40);check(marks.contentX+marks.width>=count*20-.1,"Active target clipped");const end=buttons.find(b=>b.modelData===a[count-1]);end.forceActiveFocus();input.keyClick(Qt.Key_Space);check(activations>0,"Narrow keyboard workspace lost");const before=activations;marks.workspaces=a.slice(0,-1);marks.activate(a[count-1]);check(activations===before,"Removed workspace activated");}record("workspace-"+count);}
  for(const width of [600,500,330,1920]){surface.availableWidth=width;window.implicitWidth=width;members(3);IslandState.restingMode=IslandState.Pills;Media.playing=true;IslandState.hover("media",true);input.wait(250);const media=surface.mediaStage.presentation,controls=surface.controlStage.presentation;check(media.restSceneX+media.restWidth<=surface.width/2-.1,"Playing title crosses clock "+width);check(media.restSceneX>=16/Preferences.uiScale-.1,"Playing title exceeds screen "+width);record("playing-"+width);Media.playing=false;IslandState.hover("media",false);IslandState.restingMode=IslandState.Dock;}
  surface.availableWidth=600;window.implicitWidth=600;members(3);check(!surface.compactDisclosure,"Full header discarded controls despite actual fit");check(child("focusAction").visible&&child("controlsDockHit").enabled,"Fitting header actions hidden");
  surface.availableWidth=330;window.implicitWidth=330;members(9);check(surface.compactDisclosure&&child("dockOverflow").enabled,"Narrow disclosure missing");input.mouseClick(child("dockOverflow"),14,17);check(IslandState.menu==="quicksettings","Disclosure route missing");IslandState.closeMenu();
  surface.availableWidth=1920;window.implicitWidth=1920;members(3);
  for(const gap of [0,25,40])for(const padding of [0,19,40]){Preferences.privacyIndicatorGap=gap;Preferences.privacyIndicatorRightPadding=padding;Audio.directCameras=[{directCamera:true,label:"Fixture camera"}];input.wait(40);const privacy=walk(surface).find(c=>c instanceof PrivacyIndicator);const p=bounds(privacy),clock=bounds(child("clockDockHit")),status=bounds(child("controlsDockHit"));check(clock.x+clock.w<=p.x+.01&&p.x+p.w<=status.x+.01,"Privacy target overlaps enabled adjacent target");const lamp=privacy.children.find(c=>c.width===6&&c.height===6);check(Math.abs(lamp.mapToItem(surface,0,0).x-(surface.width/2+label.width/2-1+gap))<1.1,"Privacy gap preference ignored");check(Math.abs(label.mapToItem(surface,label.width/2,0).x-surface.width/2)<.01,"Privacy moves clock");input.mouseClick(privacy,privacy.width/2,privacy.height/2);check(IslandState.menu==="privacy","Privacy pointer route missing");IslandState.closeMenu();record("privacy");}
  Audio.directCameras=[];input.wait(40);
  const action=child("focusAction"),detail=child("focusDetail");check(bounds(detail).x+bounds(detail).w<=bounds(action).x+.01,"Timer targets overlap");edgeClick(detail,true);check(IslandState.menu==="focus"&&FocusTimer.pauses===0,"Detail edge invokes action");IslandState.closeMenu();input.wait(40);edgeClick(action,false);check(FocusTimer.pauses===1&&IslandState.menu==="none","Pause edge invokes duplicate route");FocusTimer.phase="finished";input.wait(30);input.mouseClick(action,action.width/2,action.height/2);check(FocusTimer.cancels===1&&FocusTimer.pauses===1,"Finished close action not exactly once");
  FocusTimer.phase="idle";Recorder.status={phase:"recording",elapsed:127};input.wait(50);const rec=child("recorderAction"),recDetail=child("recorderDetail");input.tryVerify(()=>Math.abs(rec.parent.y)<.01,1000,"Recording selector has not presented target");check(bounds(recDetail).x+bounds(recDetail).w<=bounds(rec).x+.01,"Recording targets overlap");check(walk(rec.parent).some(c=>c instanceof Icon&&c.icon==="video_camera_front"),"Recording camera identity missing");check(walk(rec.parent).some(c=>c instanceof PanelText&&c.text==="2:07"),"Recording elapsed identity missing");edgeClick(rec,false);check(Recorder.stops===1&&IslandState.menu==="none","Recording action not exactly once "+JSON.stringify({stops:Recorder.stops,menu:IslandState.menu,target:bounds(rec)}));Recorder.status={phase:"saving",elapsed:127};input.wait(40);check(!rec.enabled,"Saving offers stop");input.mouseClick(rec,rec.width/2,rec.height/2);check(Recorder.stops===1,"Disabled saving stop invoked");
  Recorder.status={phase:"idle",elapsed:0};FocusTimer.phase="running";surface.availableWidth=330;window.implicitWidth=330;members(9);Preferences.motion="fluid";Preferences.motionSpeed=.65;IslandState.restingMode=IslandState.Pills;input.wait(70);monitor.activeWorkspace=marks.members[8];input.wait(50);monitor.activeWorkspace=marks.members[2];input.wait(35);IslandState.restingMode=IslandState.Dock;input.wait(900);check(marks.contentX<=40+.1&&marks.contentX+marks.width>=60-.1,"Active change during motion loses target");
  IslandState.restingMode=IslandState.Pills;input.wait(80);Preferences.motion="instant";check(surface.dockProgress===0,"Mid-transition Reduce Motion fails pills");IslandState.restingMode=IslandState.Dock;check(surface.dockProgress===1,"Reduced Motion fails dock");
  IslandState.restingMode=IslandState.Pills;IslandState.openMenu("notes");input.tryVerify(()=>surface.clockStage.diagnostics().entries.some(e=>e.name==="notes"&&e.enabled),2500,"Narrow Notes ready");const pane=walk(surface.clockStage).find(c=>c.modelData==="notes"&&c.selected&&c.item),menu=pane.item;const body=child("notesBody"),scroll=child("notesScroll");body.text=Array.from({length:100},(_,i)=>"Retained draft "+i).join("\n");body.cursorPosition=0;input.wait(80);scroll.contentY=60;body.forceActiveFocus();const reading=scroll.contentY;check(reading>0&&body.activeFocus,"Narrow Notes fixture has no reading/focus");check(surface.dockProgress===1&&IslandState.restingMode===IslandState.Pills,"Narrow panel overwrites saved resting mode");Preferences.motion="fluid";IslandState.closeMenu();input.wait(35);IslandState.openMenu("notes");input.wait(900);check(pane.item===menu&&scroll.contentY===reading&&body.activeFocus,"Narrow reversal loses draft/scroll/focus "+JSON.stringify({same:pane.item===menu,scroll:scroll.contentY,reading,focus:body.activeFocus}));IslandState.closeMenu();input.wait(1000);check(surface.dockProgress===0&&IslandState.restingMode===IslandState.Pills,"Narrow close fails saved resting mode");
  console.log("DOCK BALANCE PASS");Qt.quit();
 }catch(e){console.error(e);Qt.exit(1);}}}
}
'''
with tempfile.TemporaryDirectory(prefix='modesty-dock-balance-') as d:
    work=Path(d)
    for name in ('components','modules','assets','theme','scripts'):(work/name).symlink_to(qml.ROOT/name)
    (work/'services').mkdir()
    for f in (qml.ROOT/'services').iterdir():
        if f.name not in {name+'.qml' for name in STUBS}:(work/'services'/f.name).symlink_to(f)
    for name,body in STUBS.items():(work/'services'/(name+'.qml')).write_text('pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {'+body+'}')
    with patch.object(qml,'ROOT',work):qml.run(SOURCE,'DOCK BALANCE PASS',timeout=40)
