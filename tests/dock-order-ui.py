#!/usr/bin/env python3
"""Reject side crossings, changed normal pills, and incorrect dock group order."""
import argparse
from pathlib import Path
from unittest.mock import patch
import tempfile
import qml

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dock-only',action='store_true');args=parser.parse_args()

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
 property var marks:null
 property var art:null
 property var label:null
 property string failure:""
 property bool observing:false
 property int frames:0
 property QtObject monitor:QtObject {property string name:"fixture";property var activeWorkspace:null}
 Component {id:workspace;QtObject {property int id:0;property string name:"";property var monitor;property bool urgent:false;function activate(){root.monitor.activeWorkspace=this;}}}
 FloatingWindow {id:window;visible:true;implicitWidth:1920;implicitHeight:700
  Island.IslandSurface {id:surface;availableWidth:1920;availableHeight:700;scale:Preferences.uiScale;transformOrigin:Item.TopLeft;monitor:root.monitor}
 }
 TestCase {id:input;when:false}
 function check(ok,label){if(!ok)throw new Error(label);}
 function walk(item){let a=[item];for(const c of item.children||[])a=a.concat(walk(c));return a;}
 function child(name){return input.findChild(surface,name);}
 function box(item){const p=item.mapToItem(surface,0,0),q=item.mapToItem(surface,item.width,item.height);return {x:p.x,y:p.y,w:q.x-p.x,h:q.y-p.y};}
 function members(count){const list=[];for(let i=0;i<count;i++)list.push(workspace.createObject(root,{id:i+1,name:String(i+1),monitor}));marks.workspaces=list;monitor.activeWorkspace=list[0]??null;}
 function observe(name){
  const clock=box(label),media=box(art),workspace=box(marks),activity=box(child("compactActivity")),status=box(child(surface.compactDisclosure?"dockOverflow":"systemStatus"));
  check(Math.abs(clock.x+clock.w/2-surface.width/2)<.02,"Clock leaves original center "+name);
  if(Media.hasSession&&surface.mediaStage.opacity>.05){check(media.x+media.w<=clock.x+.01,"Media crosses clock "+name);check(media.x+media.w/2<surface.width/2,"Media center leaves left side "+name);}
  if(Media.hasSession&&marks.enabled&&marks.opacity>.7){const hit=box(child("mediaDockHit"));check(workspace.x+workspace.w<=hit.x+.01,"Enabled workspace and media targets overlap "+name);}
  if(surface.dockProgress===1){
   if(Media.hasSession&&surface.dockMediaFits){check(workspace.x+workspace.w<=media.x+.01,"Workspaces are not outer left "+name);check(media.x+media.w<=clock.x+.01,"Dock media is not between workspaces and clock "+name);}
   if(Activities.active){check(clock.x+clock.w<=activity.x+.01,"Activity crosses clock "+name);check(activity.x+activity.w<=status.x+.01,"Status is not right of activities "+name);}
   if(!Media.hasSession){check(surface.dockMediaWidth===0,"Absent media reserves width "+name);check(surface.dockLeftNeed===surface.dockWorkspaceWidth,"Absent media reserves gap "+name);}
  }
  const row={name,width:surface.availableWidth,p:surface.dockProgress,velocity:surface.dockVelocity,mediaPresent:Media.hasSession,workspace,media,clock,activity,status,mediaHit:box(child("mediaDockHit"))};
  console.log("ORDER_FRAME "+JSON.stringify(row));frames++;
 }
 function normal(name){const width=surface.width,clockX=(width-105)/2;check(surface.dockProgress===0,"Normal fixture is not resting");check(Math.abs(surface.clockStage.x-clockX)<.01&&Math.abs(surface.clockStage.width-105)<.01,"Original normal clock rectangle changed "+name);check(Math.abs(surface.mediaStage.x-(clockX-8-35))<.01&&Math.abs(surface.mediaStage.width-35)<.01,"Original normal media rectangle changed "+name);check(Math.abs(surface.controlStage.x-(clockX+105+8))<.01&&Math.abs(surface.controlStage.width-35)<.01,"Original normal status rectangle changed "+name);observe(name);}
 function retarget(target){const p=surface.dockProgress,v=surface.dockVelocity;IslandState.restingMode=target;check(surface.dockProgress===p&&surface.dockVelocity===v,"Retarget resets position or velocity");}
 FrameAnimation {running:root.observing;onTriggered:{try{observe("moving");}catch(e){root.failure=e.toString();root.observing=false;}}}
 Component.onCompleted:{Quickshell.watchFiles=false;Preferences.motion="instant";Preferences.uiScale=.9;Preferences.barHeight=35;Preferences.collapsedWidth=105;Preferences.clusterGap=8;Preferences.showAlbum=true;Preferences.showStatus=true;Preferences.mediaAutoHide=true;Preferences.liveMedia=true;Preferences.mediaLyrics=true;Preferences.mediaVisualizer=true;Preferences.contextEvents=false;Preferences.showSeconds=false;FocusTimer.loaded=false;FocusTimer.phase="idle";Time.timeStr="02:49";marks=walk(surface).find(c=>c instanceof Island.WorkspaceMarks);art=walk(surface.mediaStage).find(c=>c instanceof Art);label=walk(surface).find(c=>c instanceof RollingText&&c.text===Time.timeStr);}
 Timer {interval:120;running:true;onTriggered:{try{
  if(!DOCK_ONLY)for(const width of [1920,330]){surface.availableWidth=width;window.implicitWidth=width;IslandState.restingMode=IslandState.Pills;Media.hasSession=true;Media.playing=false;FocusTimer.phase="idle";input.wait(60);normal("normal-"+width);}
  for(const width of [1920,330])for(const present of [true,false]){
   Preferences.motion="instant";surface.availableWidth=width;window.implicitWidth=width;Media.hasSession=present;Media.playing=present;FocusTimer.phase="paused";FocusTimer.duration=7200;FocusTimer.remaining=7200;FocusTimer.deadline=0;input.wait(present?60:950);
   for(const count of [0,1,3,6,9]){members(count);IslandState.restingMode=IslandState.Dock;input.wait(50);observe("dock-"+present+"-w"+count+"-"+width);}
   members(3);IslandState.restingMode=IslandState.Pills;Preferences.motion="fluid";Preferences.motionSpeed=.7;observing=true;IslandState.hover("media",true);retarget(IslandState.Dock);input.wait(35);retarget(IslandState.Pills);input.wait(30);retarget(IslandState.Dock);input.wait(90);retarget(IslandState.Pills);input.wait(60);retarget(IslandState.Dock);input.wait(950);observe("forward-end");retarget(IslandState.Pills);input.wait(950);observe("reverse-end");IslandState.hover("media",false);observing=false;
   if(present){retarget(IslandState.Dock);input.wait(70);const hit=child("mediaDockHit");check(hit.enabled,"Moving media target unavailable");input.mouseClick(hit,hit.width/2,hit.height/2);check(IslandState.menu==="media","Moving left media input missed");IslandState.closeMenu();input.wait(500);}
  }
  check(!failure,failure);check(frames>30,"Order gate observed no native trajectory");console.log("DOCK ORDER PASS");Qt.quit();
 }catch(e){console.error(e);Qt.exit(1);}}}
}
'''
MEDIA='''pragma Singleton
import QtQuick
import Quickshell
Singleton {
 property bool hasSession:true;property bool playing:false;property var active:null;property var players:[]
 property string title:"Fixture";property string artist:"Fixture";property string artUrl:""
 property real length:100;property real position:10;property real progress:.1
 property bool canSeek:false;property bool canRepeat:false;property bool canGoNext:false;property bool canGoPrevious:false
 property string repeatLabel:"Unavailable";property string repeatIcon:"repeat"
 function togglePlaying(){}function next(){}function previous(){}function seekTo(value){}function cycleRepeat(){}
}'''
with tempfile.TemporaryDirectory(prefix='modesty-dock-order-') as directory:
    work=Path(directory)
    for folder in ('components','modules','assets','theme','scripts'):(work/folder).symlink_to(qml.ROOT/folder)
    (work/'services').mkdir()
    for f in (qml.ROOT/'services').iterdir():
        if f.name not in ('Media.qml','Time.qml'):(work/'services'/f.name).symlink_to(f)
    (work/'services/Media.qml').write_text(MEDIA)
    (work/'services/Time.qml').write_text('pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {property string timeStr:"02:49";property date date:new Date(2026,9,25,2,49)}')
    with patch.object(qml,'ROOT',work):qml.run(SOURCE.replace('DOCK_ONLY','true' if args.dock_only else 'false'),'DOCK ORDER PASS',timeout=35)
