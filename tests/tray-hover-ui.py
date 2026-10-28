#!/usr/bin/env python3
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(os.environ.get('MODESTY_TEST_SOURCE', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / 'tests'))
import qml

SOURCE = '''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    id:test
    property var profile:TEST_PROFILE
    property var changes:[]
    property point pointer:Qt.point(5,5)
    FloatingWindow {
        id:window;visible:true;implicitWidth:700;implicitHeight:800
        Item {
            id:host;x:20;y:20;width:600;height:740
            property real maximumBodyHeight:profile.limit?profile.limit+Preferences.innerPadding*2:Infinity
            Island.ControlCenter {id:center;width:profile.width;height:profile.height||overviewHeight}
        }
    }
    QtObject {id:first;property string id:"first";property string title:"First fixture";property string tooltipTitle:title;property string icon:"";property bool hasMenu:true;property var menu:null}
    QtObject {id:second;property string id:"second";property string title:"Second fixture";property string tooltipTitle:title;property string icon:"";property bool hasMenu:true;property var menu:null}
    Connections {target:Tray;function onSelectedChanged(){test.changes=test.changes.concat([Tray.selected?.id||"closed"]);}}
    TestCase {id:input;when:false}
    function check(ok,message) {if(!ok)throw new Error(message+" profile="+profile.name+" motion=TEST_MOTION");}
    function walk(item) {let result=[item];for(const child of item.children||[])result=result.concat(walk(child));return result;}
    function find(predicate) {const item=walk(center).find(predicate);check(!!item,"Missing control");return item;}
    function child(name) {return find(item=>item.objectName===name);}
    function rect(item) {
        const p=item.mapToItem(window.contentItem,0,0);
        let r={left:p.x,top:p.y,right:p.x+item.width,bottom:p.y+item.height};
        for(let parent=item.parent;parent;parent=parent.parent) {
            if(!parent.clip)continue;
            const p=parent.mapToItem(window.contentItem,0,0);
            r={left:Math.max(r.left,p.x),top:Math.max(r.top,p.y),right:Math.min(r.right,p.x+parent.width),bottom:Math.min(r.bottom,p.y+parent.height)};
        }
        return r;
    }
    function point(item) {
        const r=rect(item);
        check(item.visible&&item.enabled&&r.right-r.left>2&&r.bottom-r.top>2,"Control is clipped or disabled "+item);
        return Qt.point((r.left+r.right)/2,(r.top+r.bottom)/2);
    }
    function move(p) {
        const start=pointer;
        for(let i=1;i<=8;i++)input.mouseMove(window.contentItem,start.x+(p.x-start.x)*i/8,start.y+(p.y-start.y)*i/8,5);
        pointer=p;
    }
    function click(item) {move(point(item));input.mouseClick(window.contentItem,pointer.x,pointer.y);}
    function selected(app) {
        for(let i=0;i<100&&Tray.selected!==app;i++)input.wait(10);
        check(Tray.selected===app&&Tray.open,"Hover did not select "+app.id);
        input.wait(Tokens.animFast+30);
        check(Tray.selected===app,"Selection changed during menu reveal");
    }
    function stay(app,duration) {
        const count=changes.length;
        input.wait(duration);
        check(Tray.selected===app&&changes.length===count,"Hover ownership changed "+JSON.stringify(changes));
    }
    function positionFooter(overview) {
        overview.contentY=Math.max(0,overview.contentHeight-overview.height)-(profile.partial?20:0);
        overview.contentX=Math.max(0,overview.contentWidth-overview.width);
        input.wait(40);
    }
    function restore(overview) {
        IslandState.settingsOpen=false;IslandState.openMenu("quicksettings");input.wait(450);positionFooter(overview);
    }
    function outsideTile(menu) {
        const m=rect(menu);
        for(const tile of walk(center).filter(c=>["wifi","bluetooth","notes","notifications","appearance"].includes(c.kind)&&"activate" in c&&c.visible&&c.enabled)) {
            const r=rect(tile);
            if(r.right-r.left<8||r.bottom-r.top<8)continue;
            for(const x of [.2,.8])for(const y of [.2,.8]) {
                const p=Qt.point(r.left+(r.right-r.left)*x,r.top+(r.bottom-r.top)*y);
                if(p.x<m.left||p.x>m.right||p.y<m.top||p.y>m.bottom)return {tile,p};
            }
        }
        check(false,"No exposed tile for dismissal");
    }
    Component.onCompleted: {
        Preferences.motion="TEST_MOTION";Preferences.footerVisible=true;
        Preferences.footerTray=true;Preferences.footerSettings=true;Preferences.footerPerformance=true;
        if(profile.ongoing){ControlLayout.items=ControlLayout.items.filter(item=>item.id!=="focus");FocusTimer.phase="paused";}
        Tray.items=[first,second];IslandState.openMenu("quicksettings");
    }
    Timer {interval:500;running:true;onTriggered:{try {
        const overview=child("controlOverview"),footer=child("controlFooter");
        const firstIcon=find(item=>item.modelData===first&&"activate" in item);
        const secondIcon=find(item=>item.modelData===second&&"activate" in item);
        const menu=find(item=>"activeHeight" in item&&"maximumHeight" in item);
        if(profile.height||profile.limit)check(overview.contentHeight>overview.height,"Profile does not scroll");
        if(profile.width<300)check(overview.contentWidth>overview.width,"Profile is not horizontally narrow");
        if(profile.ongoing)check(overview.y===44,"Ongoing activity offset not exercised");
        positionFooter(overview);
        input.mouseClick(window.contentItem,5,5);move(Qt.point(5,5));input.wait(50);changes=[];
        move(point(firstIcon));input.wait(2500);
        console.log("STATIONARY "+JSON.stringify({profile:profile.name,motion:"TEST_MOTION",changes,selected:Tray.selected?.id,inside:Tray.pointerInside}));
        check(Tray.selected===first&&changes.length===1&&changes[0]==="first", "Stationary icon hover must stay selected; changes="+JSON.stringify(changes));
        check(firstIcon.selected&&Tray.pointerInside,"Selected icon lost hover ownership");
        move(point(menu));stay(first,550);
        let close=find(item=>item.label==="Close menu"&&item.visible);
        move(point(close));stay(first,550);
        move(point(secondIcon));selected(second);stay(second,550);
        check(!firstIcon.selected&&secondIcon.selected,"Second icon selection highlight wrong");
        close=find(item=>item.label==="Close menu"&&item.visible);
        move(point(close));stay(second,450);click(close);
        check(!Tray.open&&IslandState.menu==="quicksettings","Close control did not dismiss only tray menu");
        input.wait(250);check(Tray.path.length===0,"Closed menu model did not clean up");
        move(point(firstIcon));selected(first);move(Qt.point(5,5));
        input.wait(100);check(Tray.open,"Leave dismisses before grace period");
        input.wait(500);check(!Tray.open&&!Tray.pointerInside,"Leaving icon and menu does not dismiss");
        move(point(firstIcon));selected(first);input.wait(200);
        const target=outsideTile(menu),mode=Theme.mode,scrollY=overview.contentY;
        move(target.p);input.mouseWheel(window.contentItem,pointer.x,pointer.y,0,-120);
        check(overview.contentY===scrollY,"Open tray menu scrolls underlying tiles");
        input.mouseClick(window.contentItem,pointer.x,pointer.y);
        check(!Tray.open&&IslandState.menu==="quicksettings"&&Theme.mode===mode,"Outside click activates underlying tile");
        input.wait(250);input.mouseClick(window.contentItem,pointer.x,pointer.y);input.wait(50);
        check(target.tile.kind==="appearance"?Theme.mode!==mode:IslandState.menu!=="quicksettings","Dismissal target was not an active tile");
        restore(overview);
        for(const name of ["footerPerformance","footerSettings"]) {
            move(point(firstIcon));selected(first);move(point(menu));overview.contentX=0;input.wait(30);
            const action=child(name);action.forceActiveFocus();input.wait(50);
            click(action);input.wait(100);
            check(!Tray.open,"Footer action leaves tray menu open "+name+" "+JSON.stringify({pointer,action:rect(child(name)),contentX:overview.contentX,contentY:overview.contentY,selected:Tray.selected?.id}));
            check(name==="footerPerformance"?IslandState.menu==="performance":IslandState.settingsOpen,"Footer action unreachable "+name);
            restore(overview);
        }
        if(profile.height||profile.limit) {
            move(point(firstIcon));selected(first);move(point(menu));overview.contentY=0;input.wait(30);
            check(footer.mapToItem(overview,0,0).y>=overview.height,"Footer is not clipped below viewport");
            input.mouseClick(center,center.width-2,Math.min(center.height-2,overview.y+overview.height-2));
            check(!Tray.open&&IslandState.menu==="quicksettings","Clipped footer leaves dismissal hole");
        }
        console.log("TRAY HOVER TEST_MOTION "+profile.name+" PASS");Qt.quit();
    }catch(error){console.error(error,error.stack);Qt.exit(1);}}}
}
'''

PROFILES = (
    {'name': 'full', 'width': 400},
    {'name': 'scrolled', 'width': 400, 'height': 230},
    {'name': 'narrow-partial', 'width': 180, 'height': 230, 'partial': True},
    {'name': 'offset-limited', 'width': 400, 'limit': 280, 'ongoing': True},
)

if __name__ == '__main__':
    import json

    with tempfile.TemporaryDirectory(prefix='modesty-tray-hover-') as directory:
        workspace = Path(directory)
        for name in ('components', 'modules', 'assets', 'theme', 'scripts'):
            (workspace / name).symlink_to(ROOT / name, target_is_directory=True)
        services = workspace / 'services'
        services.mkdir()
        for source in (ROOT / 'services').iterdir():
            if source.name == 'Tray.qml':
                text = source.read_text()
                injection = 'readonly property var items:SystemTray.items.values'
                assert text.count(injection) == 1, 'Tray fixture injection no longer matches production'
                (services / source.name).write_text(text.replace(injection, 'property var items:[]'))
            else:
                (services / source.name).symlink_to(source, target_is_directory=source.is_dir())
        with patch.object(qml, 'ROOT', workspace):
            for motion in ('instant', 'gentle'):
                for profile in PROFILES:
                    marker = f'TRAY HOVER {motion} {profile["name"]} PASS'
                    source = SOURCE.replace('TEST_PROFILE', json.dumps(profile)).replace('TEST_MOTION', motion)
                    qml.run(source, marker, timeout=30)
