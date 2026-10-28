#!/usr/bin/env python3
"""Exercise production notification cards and popup transitions offscreen."""
from qml import run

SOURCE = '''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.components
import qs.services
import qs.theme
ShellRoot {
    id:test
    property var delivered:[]
    property var stack
    FloatingWindow {
        id:window
        visible:true;implicitWidth:700;implicitHeight:600
        Item {id:host;x:20;y:20;width:TEST_WIDTH;height:240}
        NotificationCard {id:history;x:390;y:20;width:280;height:implicitHeight;onToggleExpanded:expanded=!expanded;onDismissed:Notifications.close(notification)}
        TextInput {id:focusGuard;x:400;y:500;width:100;height:30;text:"Keep focus"}
    }
    Component {id:stackComponent;Island.ToastStack {width:host.width;height:host.height}}
    TestCase {id:input;when:false}
    function check(ok,message) {if(!ok)throw new Error(message);}
    function near(actual,expected,message) {check(Math.abs(actual-expected)<.1,message+" actual="+actual+" expected="+expected);}
    function walk(item) {let result=[item];for(const child of item.children||[])result=result.concat(walk(child));return result;}
    function child(item,name) {const found=input.findChild(item,name);check(!!found,"Missing "+name);return found;}
    function card() {return child(stack,"popupCard");}
    function buttons(item) {return walk(item).filter(child=>"modelData" in child&&"clicked" in child);}
    function record(title,timeout=0) {
        Notifications.previewNotify(timeout);
        const n=Notifications.list[0];n.summary=title;n.body="A readable message";
        n.localActions=[{identifier:"default",text:"Open",invoke:()=>test.delivered.push("default")},
                        {identifier:"reply",text:"Reply",invoke:()=>test.delivered.push("reply")}];
        return n;
    }
    function settle() {input.wait(70);}
    function clickText(item,name) {const label=child(item,name);input.mouseClick(label,label.width/2,label.height/2);}
    function exercise() {
        focusGuard.forceActiveFocus();
        const first=record("First message");history.notification=first;
        stack=stackComponent.createObject(host);settle();
        check(focusGuard.activeFocus,"Toast arrival steals keyboard focus");
        const popup=card(),scroll=child(stack,"notificationScroll");
        for(const toggle of [false,true]) {
            IslandState.openMenu("calendar");
            check(IslandState.state==="calendar"&&first.popup&&!first.popupClosing,"Hidden toast setup failed");
            if(toggle)IslandState.toggle("calendar");else IslandState.dismissCurrent();
            check(IslandState.menu==="none"&&first.popup&&!first.popupClosing,"Menu dismissal also dismisses hidden toast");
        }
        check(Theme.mode==="TEST_MODE","Requested color mode not active");
        check(popup.notification===first&&popup.interactive,"Newest popup not shown");
        near(popup.opacity,1,"Reduced motion did not settle immediately");
        near(popup.transform[0].y,0,"Reduced motion leaves a slide offset");
        near(Notifications.popupHeight,popup.implicitHeight,"Popup height does not follow card");
        const icon=child(popup,"notificationIcon"),summary=child(popup,"notificationSummary"),body=child(popup,"notificationBody"),app=child(popup,"notificationAppName"),dismiss=child(popup,"notificationDismiss");
        near(icon.width,18,"Popup icon is not compact");near(summary.mapToItem(popup,0,0).x,14,"Message retains icon gutter");
        near(summary.width,popup.width-28,"Message does not use full width");
        check(summary.mapToItem(popup,0,0).y>icon.y+icon.height,"Summary overlaps compact header");
        check(app.mapToItem(popup,app.width,0).x<=dismiss.x,"App name overlaps dismiss target");
        check(dismiss.visible&&dismiss.width>=32&&dismiss.height>=32,"Dismiss target is hidden or too small");
        check(summary.font.pixelSize===14&&body.font.pixelSize===12,"Message type hierarchy changed");
        check(!child(popup,"notificationTimestamp").visible,"Popup adds a timestamp");
        check(buttons(popup).length===1&&buttons(popup)[0].text==="Reply","Default action duplicated");
        const primary=child(popup,"notificationActivate");
        dismiss.forceActiveFocus();
        for(let i=0;i<12&&!primary.activeFocus;i++)input.keyClick(Qt.Key_Tab);
        check(primary.activeFocus&&primary.activeFocusOnTab&&primary.background.border.width===1,"Primary message lacks Tab or visible focus");
        for(const key of [Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space]) {
            const before=delivered.length;input.keyClick(key);
            check(delivered.length===before+1&&delivered.pop()==="default","Primary key does not invoke default exactly once "+key);
        }
        clickText(popup,"notificationAppName");clickText(popup,"notificationSummary");clickText(popup,"notificationBody");
        check(delivered.join()==="default,default,default","Header/message default action lost");
        const reply=buttons(popup)[0];input.mouseClick(reply);check(delivered.pop()==="reply"&&delivered.length===3,"Secondary click also activates default");
        input.mouseMove(reply,reply.width/2,reply.height/2);settle();
        check(reply.hovered&&reply.background.color.a<.06&&reply.background.children[0].color.a<.08,"Popup action hover is not muted");
        input.mousePress(reply,reply.width/2,reply.height/2);settle();
        check(reply.pressed&&reply.background.children[0].color.a>=.11,"Popup action press feedback lost");
        input.mouseRelease(reply,reply.width/2,reply.height/2);check(delivered.pop()==="reply","Release action lost");
        reply.forceActiveFocus();check(reply.activeFocus&&reply.background.border.width===1,"Action has no visible focus");
        input.keyClick(Qt.Key_Space);check(delivered.pop()==="reply","Keyboard secondary action lost");
        check(!history.expanded&&!child(history,"notificationActions").visible,"History starts expanded");
        near(child(history,"notificationIcon").width,28,"History icon changed");
        near(child(history,"notificationSummary").mapToItem(history,0,0).x,50,"History gutter changed");
        input.mouseClick(history,70,20);settle();check(history.expanded&&buttons(history)[0].visible,"History does not expand");
        check(child(history,"notificationTimestamp").text===Qt.formatDateTime(first.receivedAt,"ddd, h:mm ap")&&child(history,"notificationTimestamp").visible,"History timestamp missing");
        input.mouseClick(buttons(history)[0]);check(delivered.pop()==="reply","History secondary action lost");
        input.mouseClick(history,70,20);settle();check(!history.expanded,"History does not collapse");
        first.summary="A long readable title ".repeat(20);first.body="Full message retained for history. ".repeat(40);settle();
        check(summary.text===first.summary&&summary.lineCount===2&&summary.truncated,"Popup title is not clamped to two lines");
        check(body.text===first.body&&body.lineCount===2&&body.truncated,"Popup body is not clamped to two lines");
        check(child(history,"notificationSummary").lineCount===1&&child(history,"notificationBody").lineCount===1,"Collapsed history line clamps changed");
        history.expanded=true;settle();check(child(history,"notificationBody").lineCount>2&&!child(history,"notificationBody").truncated,"Expanded history loses full text");history.expanded=false;
        const withBody=popup.implicitHeight;Preferences.notificationBody=false;settle();
        check(!body.visible&&popup.implicitHeight<withBody,"Body preference leaves text or space");Preferences.notificationBody=true;
        first.summary="Short title";first.body="";first.localActions=first.localActions.slice(0,1);settle();
        check(!body.visible&&!child(popup,"notificationActions").visible&&buttons(popup).length===0,"Empty content reserves action row");
        near(popup.implicitHeight,summary.mapToItem(popup,0,0).y+summary.height+14,"Empty actions reserve trailing spacing");
        first.localActions=[];IslandState.menu="idle";clickText(popup,"notificationSummary");
        check(IslandState.menu==="notifhistory","No-default message does not open history");
        IslandState.closeMenu();primary.forceActiveFocus();input.keyClick(Qt.Key_Return);
        check(IslandState.menu==="notifhistory","No-default keyboard message does not open history");IslandState.closeMenu();
        first.localActions=Array.from({length:8},(_,i)=>({identifier:"action"+i,text:"Action "+i+" with a very long unbroken label ABCDEFGHIJKLMNOPQRSTUVWXYZ",invoke:()=>test.delivered.push("action"+i)}));settle();
        check(scroll.contentHeight>scroll.height&&scroll.clip,"Busy popup is not bounded and scrollable");
        for(const button of buttons(popup)) {
            check(button.text===button.modelData.text&&button.contentItem.text===button.modelData.text,"Action label lost logical text");
            check(button.width<=popup.width-28&&button.height>=30,"Action escapes narrow card");
            check(button.contentItem.lineCount>1&&!button.contentItem.truncated&&button.contentItem.height>=button.contentItem.implicitHeight-.1,"Long action is clipped "+[button.width,button.height,button.contentItem.width,button.contentItem.height,button.contentItem.implicitHeight,button.contentItem.lineCount,button.contentItem.truncated]);
        }
        const last=buttons(popup)[7];
        buttons(popup)[0].forceActiveFocus();
        for(let i=1;i<8;i++) {input.keyClick(Qt.Key_Tab);settle();check(buttons(popup)[i].activeFocus,"Tab skips secondary action "+i);}
        check(last.mapToItem(scroll,0,0).y>=0&&last.mapToItem(scroll,0,last.height).y<=scroll.height+.1,"Keyboard focus leaves last action outside viewport");
        input.keyClick(Qt.Key_Space);check(delivered.pop()==="action7","Last keyboard action unreachable");
        scroll.contentY=0;settle();
        input.mouseMove(scroll,scroll.width-12,scroll.height/2);input.mouseWheel(scroll,scroll.width-12,scroll.height/2,0,-2400);input.wait(300);
        check(scroll.contentY>0,"Wheel does not scroll busy popup");
        scroll.contentY=scroll.contentHeight-scroll.height;settle();input.mouseClick(last);check(delivered.pop()==="action7","Last scrolled action unreachable");
        scroll.contentY=0;settle();input.mouseMove(popup,80,35);settle();
        check(first.popupHovered,"Hover does not pause record");
        const second=record("Replacement",180);settle();
        check(stack.shown===second&&!first.popupHovered&&second.popupHovered,"Stationary pointer hover not transferred");
        near(Notifications.popupHeight,popup.implicitHeight,"Replacement popup height is stale");
        near(scroll.contentY,0,"Replacement retains stale scroll offset");
        input.wait(260);check(second.popup&&!second.popupClosing&&!second.expiry.running,"Hovered replacement expires");
        input.mouseMove(host,host.width+30,host.height+30);settle();check(!second.popupHovered&&second.expiry.running,"Pointer exit does not resume expiry");
        input.wait(260);check(!second.popup&&Notifications.list.includes(second),"Expiry does not retain history");
        const third=record("Dismiss me");settle();const before=delivered.length;
        child(popup,"notificationDismiss").forceActiveFocus();input.keyClick(Qt.Key_Return);settle();
        check(!third.popup&&Notifications.list.includes(third)&&delivered.length===before,"Popup dismiss removes history or activates default");
        history.notification=third;settle();input.mouseClick(child(history,"notificationDismiss"));settle();
        check(!Notifications.list.includes(third),"History dismiss retains record");
        const fourth=record("Destroy hovered stack");settle();input.mouseMove(popup,80,35);settle();check(fourth.popupHovered,"Destruction setup is not hovered");
        stack.destroy();settle();check(!fourth.popupHovered,"Destroyed stack retains hover pause");
        IslandState.closeMenu();IslandState.dismissCurrent();check(fourth.popupClosing,"Visible toast dismissal misses current record");
    }
    Component.onCompleted: {Preferences.motion="instant";Preferences.notificationBody=true;Theme.setMode("TEST_MODE");}
    Timer {interval:180;running:true;onTriggered:{try {
        exercise();console.log("NOTIFICATION POPUP TEST_MODE TEST_WIDTH PASS");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

for mode, width in (('dark', 350), ('light', 220)):
    run(SOURCE.replace('TEST_MODE', mode).replace('TEST_WIDTH', str(width)),
        f'NOTIFICATION POPUP {mode} {width} PASS')

MOTION = '''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    id:test
    property var stack
    property var first
    property var second
    property var newest
    property var duringClose
    property int invoked:0
    property int phase:0
    property int ticks:0
    FloatingWindow {visible:true;implicitWidth:500;implicitHeight:400;Item {id:host;x:20;y:20;width:350;height:240}}
    Component {id:stackComponent;Island.ToastStack {width:host.width;height:host.height}}
    TestCase {id:input;when:false}
    function check(ok,message) {if(!ok)throw new Error(message+" phase="+phase);}
    function card() {return input.findChild(stack,"popupCard");}
    function next() {phase++;ticks=0;}
    function record(title) {Notifications.previewNotify(0);const n=Notifications.list[0];n.summary=title;n.localActions=[{identifier:"default",text:"Open",invoke:()=>test.invoked++}];return n;}
    Component.onCompleted: {Preferences.motion="gentle";Preferences.motionSpeed=1;}
    Timer {interval:40;running:true;repeat:true;onTriggered:{try {
        ticks++;
        if(phase===0) {
            check(!Tokens.reducedMotion&&Tokens.animMedium===240,"Normal motion not active");
            first=record("Entry");stack=stackComponent.createObject(host);next();
        } else if(phase===1&&ticks===2) {
            check(stack.shown===first&&card().opacity>0&&card().opacity<1,"Initial entry skips fade or delays content "+card().opacity);
            check(card().transform[0].y>=-6&&card().transform[0].y<0,"Entry exceeds gentle 6px slide");next();
        } else if(phase===2&&ticks>7) {
            check(card().opacity===1&&card().transform[0].y===0,"Entry does not settle");
            second=record("Superseded");next();
        } else if(phase===3&&ticks===2) {newest=record("Newest");next();
        } else if(phase===4&&ticks>14) {
            check(stack.shown===newest&&card().opacity===1,"Interrupted swap does not settle on newest record");
            check(!first.popupHovered&&!second.popupHovered,"Swap leaves old hover state");
            input.mouseMove(card(),80,35);next();
        } else if(phase===5&&ticks===2) {
            check(newest.popupHovered,"Close setup is not hovered");Notifications.dismiss(newest);
            check(!card().interactive&&newest.popupClosing,"Closing popup remains interactive");
            input.mouseClick(input.findChild(stack,"notificationActivate"),80,20);next();
        } else if(phase===6&&ticks===2) {
            check(invoked===0&&card().opacity>0&&card().opacity<1&&newest.popup,"Close skips fade or accepts activation");
            check(card().transform[0].y<=0&&card().transform[0].y>=-6,"Exit exceeds gentle 6px slide");next();
        } else if(phase===7&&ticks>20) {
            check(!newest.popup&&!newest.popupHovered&&Notifications.list.includes(newest),"Animated dismiss loses history or hover cleanup");
            check(stack.shown===second&&card().opacity===1,"Older popup does not recover after closing newest");
            duringClose=record("Close during replacement");Notifications.dismiss(duringClose);next();
        } else if(phase===8&&ticks>20) {
            check(stack.shown===second&&!duringClose.popup&&card().interactive&&card().opacity===1,"Closing incoming record destabilizes replacement");
            input.mouseMove(card(),80,35);next();
        } else if(phase===9&&ticks===2) {stack.destroy();next();
        } else if(phase===10&&ticks===2) {
            check(!second.popupHovered,"Animated stack destruction retains hover");
            console.log("NOTIFICATION MOTION PASS");Qt.quit();
        }
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''
run(MOTION, 'NOTIFICATION MOTION PASS')
