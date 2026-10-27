#!/usr/bin/env python3
from pathlib import Path
from unittest.mock import patch
import tempfile
import qml
SOURCE='''import QtQuick
import Quickshell
import QtTest
import "modules/island" as Island
import qs.services
import qs.components
ShellRoot {
 FloatingWindow {visible:true;implicitWidth:1000;implicitHeight:650;Island.IslandSurface {id:surface;availableWidth:1000;availableHeight:650}}
 TestCase {id:input;when:false}
 function check(ok,label){if(!ok)throw new Error(label);}
 function walk(item){let a=[item];for(const c of item.children||[])a=a.concat(walk(c));return a;}
 Component.onCompleted:{Preferences.motion="instant";Preferences.uiScale=.9;Preferences.barHeight=35;Preferences.collapsedWidth=105;Preferences.clusterGap=8;Preferences.mediaAutoHide=false;IslandState.restingMode=IslandState.Dock;}
 Timer {interval:80;running:true;onTriggered:{try{
  const media=surface.mediaStage,clock=surface.clockStage;
  check(media.opacity===0&&!media.dockMediaAvailable&&!LiveMedia.visibleOnScreen,"Dock fabricates empty media when auto-hide is disabled");
  Media.hasSession=true;input.wait(30);check(media.dockMediaAvailable&&media.opacity===1&&!Media.playing,"Paused session disappeared");check(LiveMedia.visibleOnScreen,"Shared media observation owner misses paused artwork");
  const art=walk(media).find(c=>c instanceof Art);check(!!art&&art.visible,"Actual artwork owner missing");const point=art.mapToItem(surface,art.width/2,0);check(point.x<surface.width/2,"Artwork leaves physical left lane");
  IslandState.restingMode=IslandState.Pills;input.wait(30);check(art.mapToItem(surface,art.width/2,0).x<surface.width/2,"Normal artwork leaves physical left lane");IslandState.restingMode=IslandState.Dock;
  Media.hasSession=false;input.wait(200);check(media.dockMediaAvailable,"Real-session grace removed");input.wait(700);check(!media.dockMediaAvailable&&media.opacity===0,"Media grace fabricates permanent session");
  Preferences.showStatus=false;Audio.directCameras=[{directCamera:true,label:"Dock fixture camera"}];input.wait(30);
  const privacy=walk(surface).find(c=>c instanceof PrivacyIndicator);check(!!privacy&&privacy.kind!=="","Privacy hidden by optional status");privacy.clicked();check(IslandState.menu==="privacy","Shared privacy action lost route");IslandState.closeMenu();
  IslandState.hover("controls",true);input.wait(10);check(surface.mediaStage.hoverLift===clock.hoverLift&&surface.controlStage.hoverLift===clock.hoverLift,"Per-stage hover splits shared contour");
  Preferences.showStatus=true;Context.show("workspace","Brave","",0);input.wait(20);check(clock.height===35,"Workspace feedback expands dock");
  check(walk(surface).some(c=>c instanceof RollingText&&c.text===Time.timeStr&&c.opacity===1),"Context hides dock time");
  console.log("DOCK MEDIA PASS");Qt.quit();
 }catch(e){console.error(e);Qt.exit(1);}}}
}
'''
with tempfile.TemporaryDirectory(prefix='modesty-dock-media-') as d:
    w=Path(d)
    for name in ('components','modules','assets','theme','scripts'):(w/name).symlink_to(qml.ROOT/name)
    (w/'services').mkdir()
    for f in (qml.ROOT/'services').iterdir():
        if f.name!='Media.qml':(w/'services'/f.name).symlink_to(f)
    (w/'services/Media.qml').write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton {
 property bool hasSession:false;property bool playing:false;property var active:null;property var players:[]
 property string title:"Paused fixture";property string artist:"Artist";property string artUrl:""
 property real length:100;property real position:10;property real progress:.1
 property bool canSeek:false;property bool canRepeat:false;property bool canGoNext:false;property bool canGoPrevious:false;property string repeatLabel:"Repeat unavailable";property string repeatIcon:"repeat"
 function togglePlaying(){}function next(){}function previous(){}function seekTo(value){}function cycleRepeat(){}
}
''')
    with patch.object(qml,'ROOT',w):qml.run(SOURCE,'DOCK MEDIA PASS')
