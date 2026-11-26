#!/usr/bin/env python3
"""Exercise production PowerMenu with inert session services and real Qt input."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = r'''import QtQuick
import QtTest
import Quickshell
import qs.services
import qs.theme
import "modules/island" as Island
ShellRoot {
    FloatingWindow {
        id: window; visible:true; implicitWidth:460; implicitHeight:210
        Island.PowerMenu { id:panel; x:20; y:20; width:420; height:150; focus:true; Rectangle {anchors.fill:parent;color:"#080b0b";z:-1} }
        Item {id:other;focus:false}
    }
    FloatingWindow {id:decoy;visible:false;implicitWidth:80;implicitHeight:80}
    TestCase {id:input;when:false}
    function check(ok,message) {if(!ok)throw new Error(message);}
    function walk(item) {let all=[item];for(const child of item.children||[])all=all.concat(walk(child));return all;}
    function button(action) {return walk(panel).find(c=>c.objectName==="power-"+action);}
    function count() {return SystemInfo.calls.length+Session.calls.length;}
    function focus(action) {button(action).forceActiveFocus();input.wait(20);}
    function press(action) {const b=button(action);input.mousePress(b,b.width/2,b.height/2);}
    function release(action) {const b=button(action);input.mouseRelease(b,b.width/2,b.height/2);}
    Timer {interval:150;running:true;onTriggered:{try {
        check(panel.actions.map(a=>a.label).join("|")==="Sleep|Log out|Lock|Reboot|Power off","Action order");
        check(IslandState.height===159,"Panel measurement "+IslandState.height);
        check(panel.uptimeSeconds>=0,"Local uptime unavailable");
        for(const action of ["suspend","lock"]) {
            input.mouseClick(button(action),button(action).width/2,button(action).height/2);
        }
        check(Session.calls.join("|")==="sleep:suspend|lock:false","Secure session routing");
        let before=count();
        for(const action of ["logout","reboot","poweroff"]) {
            input.mouseClick(button(action),26,26);input.wait(950);
            check(count()===before,"Tap invoked "+action);
            press(action);input.wait(300);
            check(panel.progress>0&&panel.progress<1,"Missing hold feedback");
            release(action);input.wait(750);check(count()===before,"Short hold invoked "+action);
            press(action);input.wait(800);check(count()===before,"Hold completed before 900 ms");
            input.wait(200);check(count()===++before,"Completed hold failed "+action);
            input.wait(1000);check(count()===before,"Repeated hold invocation");release(action);
        }
        for(const mode of ["outside","hide","disable","focus","escape","button-hide","button-disable","deactivate"]) {
            press("poweroff");input.wait(200);
            if(mode==="outside")input.mouseMove(panel,0,0);
            if(mode==="hide")panel.visible=false;
            if(mode==="disable")panel.enabled=false;
            if(mode==="focus")other.forceActiveFocus();
            if(mode==="escape")input.keyClick(Qt.Key_Escape);
            if(mode==="button-hide")button("poweroff").visible=false;
            if(mode==="button-disable")button("poweroff").enabled=false;
            if(mode==="deactivate") {
                decoy.visible=true;decoy.contentItem.Window.window.requestActivate();input.wait(50);
                check(!panel.Window.window.active,"Window deactivation fixture failed");
            }
            input.wait(950);panel.visible=true;panel.enabled=true;
            button("poweroff").visible=true;button("poweroff").enabled=true;
            decoy.visible=false;window.contentItem.Window.window.requestActivate();input.wait(20);release("poweroff");
            check(count()===before&&panel.pressTarget===-1,"Cancel failed "+mode);
        }
        for(const key of [Qt.Key_Space,Qt.Key_Return]) {
            focus("logout");input.keyPress(key);input.wait(200);input.keyRelease(key);input.wait(950);
            check(count()===before,"Short key hold invoked");
            input.keyPress(key);input.wait(1000);check(count()===++before,"Key hold failed");
            input.keyPress(key);input.wait(950);check(count()===before,"Key hold repeated");input.keyRelease(key);
        }
        focus("reboot");input.keyClick(Qt.Key_Right);check(panel.selected===4,"Arrow navigation");
        focus("lock");input.keyClick(Qt.Key_Tab);check(button("reboot").activeFocus,"Tab navigation");
        input.keyClick(Qt.Key_Backtab);check(button("lock").activeFocus,"Backtab navigation");
        button("logout").Accessible.pressAction();input.wait(950);check(count()===before,"Accessibility bypassed hold");
        button("lock").Accessible.pressAction();check(Session.calls[Session.calls.length-1]==="lock:false","Accessible Lock failed");before=count();
        press("logout");input.wait(200);panel.visible=false;panel.visible=true;input.wait(1000);release("logout");
        check(count()===before,"Reopen retained hold");
        panel.width=220;input.wait(50);
        const first=button("suspend").mapToItem(panel,0,0),last=button("poweroff").mapToItem(panel,button("poweroff").width,0);
        check(first.x>=0&&last.x<=panel.width,"Small screen overflow");
        console.log("POWER MENU PASS");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''

with tempfile.TemporaryDirectory(prefix='modesty-power-') as temporary:
    workspace = Path(temporary)
    (workspace / 'runtime').mkdir(mode=0o700)
    (workspace / 'modules/island').mkdir(parents=True)
    (workspace / 'modules/island/PowerMenu.qml').write_bytes((ROOT / 'modules/island/PowerMenu.qml').read_bytes())
    (workspace / 'components').symlink_to(ROOT / 'components', target_is_directory=True)
    (workspace / 'services').mkdir()
    stubs = {
        'Preferences': 'property int innerPadding:16',
        'IslandState': 'property real height:0; function measurePanel(name,value) {if(name!=="power")throw Error(name);height=value;}',
        'Session': 'property var calls:[];function lock(value) {calls=calls.concat(["lock:"+value]);}function requestSleep(mode) {calls=calls.concat(["sleep:"+mode]);}',
        'SystemInfo': 'property var calls:[];function action(name,value) {calls=calls.concat([name]);}',
    }
    for name, body in stubs.items():
        (workspace / f'services/{name}.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject {' + body + '}')
    (workspace / 'services/qmldir').write_text(''.join(f'singleton {name} 1.0 {name}.qml\n' for name in stubs))
    (workspace / 'theme').mkdir()
    (workspace / 'theme/Theme.qml').write_text('''pragma Singleton
import QtQuick
QtObject {
    property color text:"#edf0ef";property color subtext:"#99a3a1"
    property color accent:"#67b7b5";property color accentText:"#080b0b";property color red:"#e57474"
    function withAlpha(color,alpha) {return Qt.rgba(color.r,color.g,color.b,alpha);}
}''')
    (workspace / 'theme/Tokens.qml').write_text('''pragma Singleton
import QtQuick
QtObject {property int animFast:0;property int animMedium:0;property int captionSize:11
property string iconFont:"Material Symbols Rounded";property string font:"sans-serif"
property string clockFont:font
property int textRenderType:Text.QtRendering;property bool reducedMotion:true}''')
    (workspace / 'theme/qmldir').write_text('singleton Theme 1.0 Theme.qml\nsingleton Tokens 1.0 Tokens.qml\n')
    (workspace / 'shell.qml').write_text(SOURCE)
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software', MODESTY_PREVIEW='1',
               XDG_STATE_HOME=str(workspace / 'state'), XDG_CACHE_HOME=str(workspace / 'cache'),
               XDG_RUNTIME_DIR=str(workspace / 'runtime'), XDG_CONFIG_HOME=str(workspace / 'config'),
               XDG_DATA_HOME=str(workspace / 'data'),
               DBUS_SYSTEM_BUS_ADDRESS='unix:path=' + str(workspace / 'no-system-bus'))
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'HYPRLAND_INSTANCE_SIGNATURE', 'DBUS_SESSION_BUS_ADDRESS'):
        env.pop(name, None)
    result = subprocess.run(['dbus-run-session', '--', 'qs', '--no-color', '-p', str(workspace)],
                            env=env, capture_output=True, text=True, timeout=50)
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'POWER MENU PASS' in output, output
    assert not any(error in output for error in ('ReferenceError', 'TypeError', 'Binding loop', 'Unable to assign')), output
    assert not list((workspace / 'state').rglob('*')), 'Unexpected settings write'
    print('POWER MENU PASS (isolated inert backend; pointer, keyboard, cancellation, geometry)')
