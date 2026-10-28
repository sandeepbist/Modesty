#!/usr/bin/env python3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import sleep

from qml import run

SIDE = '''import QtQuick
import QtTest
import Quickshell
import qs.services
import "modules/island" as Island
ShellRoot {
    FloatingWindow {visible:true;implicitWidth:1000;implicitHeight:650
        Island.IslandSurface {id:surface;availableWidth:800;availableHeight:600}
    }
    TestCase {id:input;when:false}
    function check(ok,label) {if(!ok)throw new Error(label);}
    function near(a,b,label) {check(Math.abs(a-b)<.00001,label+" before="+a+" after="+b);}
    function walk(item) {let all=[item];for(const child of item.children||[])all=all.concat(walk(child));return all;}
    function bounds() {
        for(const stage of [surface.mediaStage,surface.controlStage]) {
            check(stage.x*Preferences.uiScale>=16-.001,"Side crosses left physical margin");
            check((surface.width-stage.x-stage.width)*Preferences.uiScale>=16-.001,"Side crosses right physical margin");
        }
    }
    function exercise() {
        Preferences.motion="gentle";Preferences.motionSpeed=1.15;Preferences.uiScale=.9;
        Preferences.barHeight=35;Preferences.collapsedWidth=105;Preferences.clusterGap=8;
        Preferences.innerPadding=15;Preferences.expandedRadius=30;Preferences.mediaAutoHide=false;
        for(const output of [800,640])for(const name of ["quicksettings","media"]) {
            surface.availableWidth=output;IslandState.openMenu(name);input.wait(850);
            const stage=name==="media"?surface.mediaStage:surface.controlStage;
            const loader=walk(stage).find(c=>c.selected&&c.heldWidth!==undefined),item=loader.item;
            const w=stage.width,x=stage.x,lw=loader.width,lh=loader.height;
            IslandState.openMenu("clock");
            near(w,stage.width,"Synchronous side cap jump");near(x,stage.x,"Synchronous side position jump");
            for(let i=0;i<3;i++){input.wait(16);bounds();near(lw,loader.width,"Outgoing layout follows moving cap");near(lh,loader.height,"Outgoing height changed");}
            IslandState.openMenu(name);
            check(loader.item===item,"Side reversal recreated loaded content");
            for(let i=0;i<50;i++){input.wait(16);bounds();}
            near(stage.targetWidth,stage.width,"Side misses settled destination");
        }
        Audio.directCameras=[{directCamera:true,label:"Fixture camera"}];IslandState.closeMenu();input.wait(850);bounds();
        near(surface.controlStage.maximumWidth,surface.width-16/Preferences.uiScale-surface.clockStage.x-surface.clockStage.width-surface.gap,"Privacy cap ignores rendered edge");
    }
    Timer {interval:100;running:true;onTriggered:{try{exercise();console.log("POLISH SIDE PASS");Qt.quit();}catch(e){console.error(e);Qt.exit(1);}}}
}
'''

REVERSE = '''import QtQuick
import QtTest
import Quickshell
import qs.services
import "modules/island" as Island
ShellRoot {
    id:test
    property real apertureWidth:216
    property real apertureHeight:96
    property int profile:0
    property string phase:"prepare"
    property double since:Date.now()
    property var opening
    property var previous
    readonly property real fit:profile===0?1:.72
    FloatingWindow {visible:true;implicitWidth:700;implicitHeight:500
        Island.Stage {id:stage;stage:"clock";width:test.apertureWidth;height:test.apertureHeight;targetWidth:216;targetHeight:96}
    }
    TestCase {id:input;when:false}
    function check(ok,label) {if(!ok)throw new Error(label+" phase="+phase+" fit="+fit);}
    function near(a,b,label) {check(Math.abs(a-b)<.00001,label+" before="+a+" after="+b);}
    function walk(item) {let all=[item];for(const child of item.children||[])all=all.concat(walk(child));return all;}
    function pane() {return walk(stage).find(c=>c.modelData==="clock"&&c.outgoingScale!==undefined);}
    function geometry(amount) {apertureWidth=Preferences.innerPadding*2+pane().width*amount;apertureHeight=Preferences.innerPadding*2+pane().height*amount;}
    function sample() {const p=pane();return {scale:p.transform[0].xScale,reveal:p.revealAmount,opacity:p.opacity,item:p.item,width:stage.width,height:stage.height};}
    function next(name) {phase=name;since=Date.now();}
    function reselect(label) {
        const before=sample();check(before.opacity>0,"Reversal fixture already invisible");stage.panel="clock";
        const after=sample();near(before.scale,after.scale,label+" scale");near(before.reveal,after.reveal,label+" reveal");near(before.opacity,after.opacity,label+" opacity");
        near(before.width,after.width,label+" aperture width");near(before.height,after.height,label+" aperture height");check(before.item===after.item,label+" item identity");
    }
    Component.onCompleted:{Preferences.motion="gentle";Preferences.motionSpeed=.65;Preferences.innerPadding=15;}
    Timer {interval:20;running:true;repeat:true;onTriggered:{try{
        const elapsed=Date.now()-since,p=pane();check(elapsed<2500,"Reversal timed out");
        if(phase==="prepare"&&p.item&&elapsed>180&&p.exposure===0) {
            geometry(fit);stage.panel="clock";next("opening");
        } else if(phase==="opening"&&elapsed>300) {
            near(p.visibleScale,fit,"Fresh entrance scale");
            if(fit<1)check(p.opacity>0&&p.opacity<.7&&!p.enabled,"Partial fixture must be visible below input threshold");
            opening=sample();stage.panel="idle";check(!p.enabled,"Outgoing pane accepts input");geometry(.4);next("closing");
        } else if(phase==="closing"&&elapsed>=20) {
            near(opening.scale,p.transform[0].xScale,"Outgoing transform not frozen");reselect("Retained");next("resuming");
        } else if(phase==="resuming"&&elapsed>=20) {
            if(fit<1) {
                input.tryVerify(()=>p.transform[0].xScale>opening.scale&&p.transform[0].xScale<1,300,"Partial resumption has no intermediate frame");
                check(p.transform[0].xScale!==1,"Partial resumption finishes before an intermediate frame");
                check(p.transform[0].xScale>opening.scale,"No resumption frame within 300ms");
            }
            previous=sample();stage.panel="idle";geometry(.9);next("repeated close");
        } else if(phase==="repeated close"&&elapsed>=20) {
            reselect("Repeated");check(p.transform[0].xScale>=previous.scale,"Repeated reversal regresses scale");next("repeated resume");
        } else if(phase==="repeated resume"&&elapsed>=20) {
            stage.panel="calendar";geometry(1.6);next("enlarged");
        } else if(phase==="enlarged"&&elapsed>=20) {
            reselect("Enlarged aperture");geometry(1);previous=sample();next("settling");
        } else if(phase==="settling") {
            const current=sample();
            check(current.scale>=previous.scale-.00001&&current.scale<=1,"Gentle resumption scale leaves continuous range");
            check(current.reveal>=previous.reveal-.00001&&current.reveal<=1,"Gentle resumption reveal leaves continuous range");previous=current;
            if(elapsed>1200) {
                near(1,p.transform[0].xScale,"Resume misses full scale");near(1,p.opacity,"Resume misses full opacity");
                if(profile++===1){console.log("POLISH REVERSE PASS");Qt.quit();return;}
                stage.panel="idle";geometry(.4);next("prepare");
            }
        }
    }catch(e){console.error(e);Qt.exit(1);}}}
}
'''

LEVEL = '''import QtQuick
import QtTest
import Quickshell
import qs.services
import "modules/island" as Island
ShellRoot {
    FloatingWindow {visible:true;implicitWidth:1000;implicitHeight:300;Island.IslandSurface {id:surface;availableWidth:1000}}
    TestCase {id:input;when:false}
    function check(ok,label) {if(!ok)throw new Error(label+" level="+surface.levelProgress);}
    function exercise() {
        Preferences.motion="gentle";Context.show("volume","Volume","volume_up",.5);input.wait(65);
        check(surface.levelProgress>0&&surface.levelProgress<1,"Entry fixture did not animate");
        Preferences.motion="instant";check(surface.levelProgress===1,"Active level entry not settled immediately");input.wait(100);check(surface.levelProgress===1,"Settled entry kept moving");
        Preferences.motion="gentle";Context.clear();input.wait(65);check(surface.levelProgress>0&&surface.levelProgress<1,"Later fluid exit lost binding");
        Preferences.motion="instant";check(surface.levelProgress===0,"Active level exit not settled immediately");
        Preferences.motion="gentle";Context.show("brightness","Brightness","light_mode",.4);input.wait(65);check(surface.levelProgress>0&&surface.levelProgress<1,"Later fluid entry lost binding");
    }
    Timer {interval:120;running:true;onTriggered:{try{exercise();console.log("POLISH LEVEL PASS");Qt.quit();}catch(e){console.error(e);Qt.exit(1);}}}
}
'''

TOAST = '''import QtQuick
import QtTest
import Quickshell
import qs.services
import "modules/island" as Island
ShellRoot {
    property var stack
    property var first
    property int phase:0
    FloatingWindow {visible:true;implicitWidth:600;implicitHeight:400;Item {id:host;width:350;height:240}}
    Component {id:component;Island.ToastStack {width:350;height:240}}
    TestCase {id:input;when:false}
    function check(ok,label) {if(!ok)throw new Error(label+" presence="+stack.presence);}
    function record() {Notifications.previewNotify(0);return Notifications.list[0];}
    function exercise() {
        check(stack.presence>0&&stack.presence<1,"Toast entry fixture not moving");Preferences.motion="instant";
        check(stack.presence===1&&stack.shown===first,"Active toast entry not settled immediately");
        input.mouseMove(input.findChild(stack,"popupCard"),80,35);input.wait(20);check(first.popupHovered,"Hover fixture missing");
        Preferences.motion="gentle";const second=record();input.wait(65);check(stack.shown===first&&stack.presence>0&&stack.presence<1,"Swap fixture missed outgoing half");
        Preferences.motion="instant";check(stack.shown===second&&stack.presence===1&&!first.popupHovered&&second.popupHovered,"Instant swap loses identity/hover");
        input.wait(100);check(stack.shown===second&&stack.presence===1,"Stopped swap still runs ScriptAction");
        Preferences.motion="gentle";Notifications.dismiss(second);input.wait(65);check(stack.presence>0&&stack.presence<1,"Exit fixture not moving");
        Preferences.motion="instant";check(stack.shown===second&&stack.presence===0&&second.popupClosing&&second.popup,"Instant exit changes lifecycle or leaves motion");
        Preferences.motion="gentle";const third=record();input.wait(65);check(stack.shown===third&&stack.presence>0&&stack.presence<1,"Later fluid toast does not animate");
    }
    Component.onCompleted:Preferences.motion="gentle"
    Timer {id:steps;interval:120;running:true;onTriggered:{try{
        if(phase++===0){first=record();stack=component.createObject(host);interval=65;restart();return;}
        exercise();console.log("POLISH TOAST PASS");Qt.quit();
    }catch(e){console.error(e);Qt.exit(1);}}}
}
'''

ART = '''import QtQuick
import QtTest
import Quickshell
import qs.components
import qs.services
ShellRoot {
    property int phase:0
    property int presentations:0
    FloatingWindow {visible:true;implicitWidth:300;implicitHeight:200
        CrossfadeImage {id:art;width:80;height:80;source:"ART_URL/first.svg";onPresented:presentations++}
    }
    TestCase {id:input;when:false}
    function check(ok,label) {if(!ok)throw new Error(label+" presentations="+presentations);}
    function slots() {return art.children.filter(c=>c.status!==undefined&&c.source!==undefined);}
    function current() {return slots().find(c=>String(c.source)===art.source);}
    function waitReady() {for(let i=0;i<150&&current()?.status!==Image.Ready;i++)input.wait(10);check(current()?.status===Image.Ready,"Current decode never ready");}
    Component.onCompleted:Preferences.motion="gentle"
    Timer {id:steps;interval:350;running:true;onTriggered:{try{
        if(phase===0){check(art.ready&&presentations===1,"Initial art not presented once");art.source="ART_URL/second.svg";phase=1;interval=20;restart();return;}
        if(phase===1){if(current()?.status===Image.Ready){phase=2;interval=65;}restart();return;}
        check(current()?.opacity>0&&current().opacity<1,"Artwork fade fixture not moving");Preferences.motion="instant";
        check(current().opacity===1&&presentations===2&&!art.transitioning,"Active artwork fade not settled immediately");
        input.wait(400);check(presentations===2,"Stopped fade emits presented twice");
        Preferences.motion="gentle";art.source="ART_URL/slow.svg";Preferences.motion="instant";
        check(slots().some(c=>String(c.source).endsWith("second.svg")&&c.opacity===1),"Pending decode loses valid old artwork");
        waitReady();check(current().opacity===1&&presentations===3,"Instant pending decode never presented once");input.wait(100);check(presentations===3,"Pending decode emits presented twice");
        Preferences.motion="gentle";art.source="ART_URL/last.svg";waitReady();input.wait(60);
        check(current().opacity>0&&current().opacity<1,"Later fluid artwork does not fade");input.wait(400);check(presentations===4,"Later fluid completion not once-only");
        console.log("POLISH ART PASS");Qt.quit();
    }catch(e){console.error(e);Qt.exit(1);}}}
}
'''


def artwork_source():
    class ImageHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/slow.svg':
                sleep(.3)
            color = 'red' if self.path == '/first.svg' else 'blue'
            data = f'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><rect width="80" height="80" fill="{color}"/></svg>'.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'image/svg+xml')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), ImageHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server, ART.replace('ART_URL', f'http://127.0.0.1:{server.server_port}')


GEOMETRY = '''import QtQuick
import QtTest
import Quickshell
import qs.components
import qs.services
import "modules/island" as Island
ShellRoot {
    FloatingWindow {visible:true;implicitWidth:1200;implicitHeight:700
        Island.IslandSurface {id:surface;availableWidth:1200;availableHeight:680}
    }
    TestCase {id:input;when:false}
    function check(ok,label) {if(!ok)throw new Error(label+" padding="+Preferences.innerPadding);}
    function near(a,b,label) {check(Math.abs(a-b)<.01,label+" actual="+a+" expected="+b);}
    function walk(item) {let all=item?[item]:[];for(const child of item?.children||[])all=all.concat(walk(child));return all;}
    function find(item,predicate) {const found=walk(item).find(predicate);check(!!found,"Missing fixture child");return found;}
    function pane(stage,name) {return find(stage,c=>c.modelData===name&&c.heldWidth!==undefined);}
    function ready(stage,name) {for(let i=0;i<150&&(!pane(stage,name).item||!pane(stage,name).enabled);i++)input.wait(10);check(pane(stage,name).enabled,"Pane never ready "+name);input.wait(30);return pane(stage,name).item;}
    function exercise() {
        Preferences.motion="instant";Preferences.uiScale=.9;Preferences.barHeight=35;Preferences.collapsedWidth=105;Preferences.clusterGap=8;
        Preferences.controlsWidth=400;Preferences.mediaWidth=360;Preferences.calendarWidth=280;
        Preferences.controlRadius=17;Preferences.controlIconSize=18;Preferences.controlGap=8;Preferences.crispText=false;
        for(const profile of [{padding:15,radius:30},{padding:10,radius:28},{padding:6,radius:30},{padding:16,radius:30}]) {
            Preferences.innerPadding=profile.padding;Preferences.expandedRadius=profile.radius;
            IslandState.openMenu("notifhistory");const center=ready(surface.controlStage,"quicksettings");
            const sheet=input.findChild(center,"controlDetailSheet"),viewport=input.findChild(center,"controlDetailViewport");
            near(IslandState.detailChromeHeight,78,"Detail chrome drift");
            near(sheet.mapToItem(surface.controlStage,0,0).x,profile.padding+6,"Sheet side gap");
            near(surface.controlStage.height-sheet.mapToItem(surface.controlStage,0,sheet.height).y,profile.padding+6,"Sheet bottom gap");
            near(sheet.radius,profile.radius-profile.padding-6,"Sheet radius");
            near(viewport.height,surface.controlStage.targetHeight-2*profile.padding-IslandState.detailChromeHeight,"Final viewport height");
            near(IslandState.sizes.notifhistory[1],250,"Empty history is too tall");
            const feed=find(center,c=>c.feedInset!==undefined&&!c.showHeader);
            check(feed.feedInset===0&&!feed.compact&&feed.height>=95,"Full empty history keeps redundant inset or compact fallback");
            IslandState.openMenu("media");const media=ready(surface.mediaStage,"media"),mediaViewport=input.findChild(media,"mediaViewport");
            near(IslandState.sizes.media[1],Math.max(186,166+2*profile.padding),"Content-driven media height");
            check(mediaViewport.height>=166&&mediaViewport.contentHeight===mediaViewport.height,"Ordinary media still scrolls vertically");
            IslandState.openMenu("calendar");const calendar=ready(surface.clockStage,"calendar");
            const cells=walk(calendar).filter(c=>c.day!==undefined&&c.today!==undefined&&c.key!==undefined);
            check(cells.length===42,"Calendar lost six weeks");
            for(const cell of cells) {
                const text=find(cell,c=>c instanceof PanelText&&c.text===String(cell.day.getDate()));
                check(text.font.pixelSize===13&&text.font.weight===Font.Medium,"Calendar date typography");
                check(cell.width>=26&&cell.height>=26&&cell.background.width===26&&cell.background.radius===13,"Calendar marker exceeds hitbox");
            }
            const chooser=find(calendar,c=>c.Accessible?.name==="Choose month"),heading=chooser.contentItem;
            chooser.text="A very long localized September heading 2026";input.wait(30);
            check(heading.font.pixelSize===14&&heading.width<=chooser.width&&heading.text===chooser.text&&chooser.Accessible.description===chooser.text,"Long calendar heading loses bounds or accessible text");
        }
        Preferences.innerPadding=15;Preferences.expandedRadius=30;
        IslandState.openMenu("notifhistory");const center=ready(surface.controlStage,"quicksettings");
        for(let i=0;i<8;i++){Notifications.previewNotify(0);const n=Notifications.list[0];n.summary="Long notification title ".repeat(8);n.body="Long retained history body ".repeat(15);n.localActions=[{identifier:"reply",text:"Reply to this notification",invoke:()=>{}}];}
        input.wait(100);near(IslandState.sizes.notifhistory[1],400,"Populated history did not grow");
        const feed=find(center,c=>c.feedInset!==undefined&&!c.showHeader),cards=walk(feed).filter(c=>c.notification!==undefined&&c.departure!==undefined);
        check(cards.length>0&&cards.every(c=>c.width===feed.width-4),"Full-history cards lose width or scrollbar clearance");
        const first=cards[0];feed.expandedId=first.notification.serial;input.wait(35);
        check(first.expanded&&walk(first).some(c=>c.objectName==="notificationAction-reply"&&c.visible),"Populated history action missing");
        Preferences.motion="gentle";for(const record of Notifications.list)Notifications.close(record);
        check(Notifications.list.length===8&&IslandState.sizes.notifhistory[1]===400,"Closing records shrink history early");
        input.wait(80);check(IslandState.sizes.notifhistory[1]===400,"Departing history shrinks during animation");
        input.wait(900);check(Notifications.list.length===0&&IslandState.sizes.notifhistory[1]===250,"Empty history does not shrink after departure");
        const viewport=input.findChild(center,"controlDetailViewport"),width=viewport.width,height=viewport.height;
        IslandState.closeMenu();input.wait(16);near(viewport.width,width,"Closing detail text follows current clip width");near(viewport.height,height,"Closing detail text follows current clip height");
    }
    Timer {interval:150;running:true;onTriggered:{try{exercise();console.log("POLISH GEOMETRY PASS");Qt.quit();}catch(e){console.error(e);Qt.exit(1);}}}
}
'''

CASES = {'side': SIDE, 'reverse': REVERSE, 'level': LEVEL, 'toast': TOAST, 'art': ART, 'geometry': GEOMETRY}

if __name__ == '__main__':
    for name in sys.argv[1:] or CASES:
        if name == 'art':
            server, source = artwork_source()
            try:
                run(source, 'POLISH ART PASS')
            finally:
                server.shutdown()
        else:
            run(CASES[name], f'POLISH {name.upper()} PASS', timeout=30)
