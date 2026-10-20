#!/usr/bin/env python3
"""Render the production orb with mutable battery and Wi-Fi inputs."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'STATUS ORB PASS'

with tempfile.TemporaryDirectory(prefix='modesty-status-orb-') as temporary:
    workspace = Path(temporary)
    stubs = {
        'services': {
            'SystemInfo': 'property bool hasBattery:true;property real batteryPercent:65;property bool charging:false;property bool wifiEnabled:true',
            'Wireless': 'property bool available:true;property string connectedName:"Fixture";property var networks:[{connected:true,signalStrength:.4}]',
            'DeviceStatus': 'property bool available:false;property bool batteryAvailable:true;property real battery:.8;property bool low:false;property string icon:"headphones";property string name:"Fixture headphones"',
            'Hints': 'property string text:"";function show(owner,value):void{text=value;}function hide(owner):void{text="";}',
        },
        'theme': {
            'Theme': 'property color text:"#eeeeee";property color red:"#ff4444";function withAlpha(value,alpha):color{return Qt.rgba(value.r,value.g,value.b,alpha);}',
            'Tokens': 'property bool reducedMotion:true;readonly property int animMedium:reducedMotion?0:240;property string iconFont:"sans-serif"',
        },
    }
    for directory, singletons in stubs.items():
        (workspace / directory).mkdir()
        for name, body in singletons.items():
            (workspace / directory / f'{name}.qml').write_text(
                'pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {' + body + '}\n')
        (workspace / directory / 'qmldir').write_text(''.join(
            f'singleton {name} 1.0 {name}.qml\n' for name in singletons))
    (workspace / 'components').mkdir()
    for source in ('modules/island/StatusOrb.qml', 'components/Icon.qml', 'components/CompactGlyph.qml'):
        content = (ROOT / source).read_text()
        for module in ('services', 'theme', 'components'):
            relative = module if source.startswith('modules/') else '../' + module
            content = content.replace(f'import qs.{module}', f'import "{relative}"')
        target = workspace / ('StatusOrb.qml' if source.startswith('modules/') else source)
        target.write_text(content)
    (workspace / 'components/ControlGlyphs.js').symlink_to(ROOT / 'components/ControlGlyphs.js')
    (workspace / 'shell.qml').write_text('''import QtQuick
import QtTest
import Quickshell
import "services"
import "theme"
ShellRoot {
    FloatingWindow {
        id:window;visible:true;implicitWidth:100;implicitHeight:100
        StatusOrb {id:orb;x:37;y:37}
    }
    TestCase {id:test;when:false}
    function check(ok,label) {if(!ok)throw new Error(label);}
    function near(actual,expected,label) {check(Math.abs(actual-expected)<.01,label+": "+actual+" != "+expected);}
    function signal(value) {Wireless.networks=[{connected:true,signalStrength:value}];test.wait(5);}
    function dots(count) {
        const items=orb.children.filter(c=>"modelData" in c&&typeof c.modelData==="number").sort((a,b)=>a.x-b.x);
        check(items.length===4,"Four real dots");
        for(let i=0;i<4;i++)near(items[i].color.a,i<count?.78:.3,"Left-first dot "+i);
    }
    function description(parts) {
        const text=orb.Accessible.name;
        for(const part of parts)check(text.includes(part),"Accessible description missing "+part+": "+text);
        test.mouseMove(window.contentItem,1,1);test.mouseMove(orb,13,13);test.wait(5);
        check(Hints.text==="","Hovering orb shows no tooltip");
    }
    Timer {interval:80;running:true;onTriggered:{try{
        const shape=orb.children.find(c=>"preferredRendererType" in c);
        const track=shape.data[0],fill=shape.data[1],arc=fill.pathElements[0];
        near(track.pathElements[0].startAngle,170,"Track starts centered over top");
        near(arc.startAngle,170,"Fill starts centered over top");
        near(track.pathElements[0].sweepAngle,200,"Track geometry");
        near(track.strokeColor.a,.18,"Faint track");
        near(arc.sweepAngle,130,"Laptop battery ring");dots(2);
        description(["Laptop battery 65%","Wi-Fi connected to Fixture","40% signal"]);
        for(const [strength,count] of [[0,0],[.001,1],[.25,1],[.2501,2],[.5,2],[.5001,3],[.75,3],[.7501,4],[1,4],[-.2,0],[1.2,4],[NaN,0],[Infinity,0],[-Infinity,0],[undefined,0],[null,0],[".5",0]]) {
            signal(strength);dots(count);near(arc.sweepAngle,130,"Wi-Fi must not change ring");
        }
        signal(.6);
        for(const percent of [0,100]) {
            SystemInfo.batteryPercent=percent;test.wait(5);
            near(arc.sweepAngle,percent*2,"Laptop battery bounds");dots(3);
        }
        SystemInfo.batteryPercent=20;test.wait(5);
        near(arc.sweepAngle,40,"Low laptop ring");dots(3);
        check(fill.strokeColor.toString()===Theme.red.toString(),"Laptop 20% red");
        SystemInfo.batteryPercent=21;test.wait(5);
        check(fill.strokeColor.toString()===Theme.text.toString(),"Laptop 21% normal text");dots(3);
        SystemInfo.batteryPercent=90;SystemInfo.charging=true;test.wait(5);
        near(arc.sweepAngle,180,"Battery must not change dots");dots(3);
        description(["Laptop battery 90%","plugged in","60% signal"]);
        SystemInfo.hasBattery=false;test.wait(5);
        near(arc.sweepAngle,0,"Missing battery has no filled fallback");near(fill.strokeColor.a,0,"Missing battery hides fill");
        near(track.strokeColor.a,.18,"Missing battery preserves track");dots(3);
        description(["Laptop battery unavailable","60% signal"]);
        SystemInfo.hasBattery=true;SystemInfo.charging=false;SystemInfo.wifiEnabled=false;test.wait(5);
        dots(0);near(arc.sweepAngle,180,"Wi-Fi off leaves battery");check(orb.glyph==="wifi_off","Wi-Fi off icon");
        description(["Wi-Fi off"]);
        SystemInfo.wifiEnabled=true;Wireless.available=false;test.wait(5);dots(0);description(["Wi-Fi unavailable"]);
        Wireless.available=true;Wireless.networks=[{connected:false,signalStrength:1}];test.wait(5);
        dots(0);description(["Wi-Fi disconnected"]);
        Wireless.networks=[];test.wait(5);dots(0);
        signal(.25);DeviceStatus.available=true;test.wait(5);
        near(arc.sweepAngle,160,"Headphones battery ring");dots(1);check(orb.glyph==="headphones","Headphones icon");
        description(["Fixture headphones","80% battery","Laptop battery 90%","25% signal"]);
        signal(.9);near(arc.sweepAngle,160,"Overlay ring independent of Wi-Fi");dots(4);
        SystemInfo.batteryPercent=10;test.wait(5);
        near(arc.sweepAngle,160,"Overlay ignores laptop ring");dots(4);
        check(fill.strokeColor.toString()===Theme.text.toString(),"Overlay ignores laptop low color");
        DeviceStatus.battery=.1;DeviceStatus.low=true;DeviceStatus.icon="earbuds";test.wait(5);
        near(arc.sweepAngle,20,"Earbuds battery ring");dots(4);check(orb.glyph==="earbuds","Earbuds icon");
        check(fill.strokeColor.toString()===Theme.red.toString(),"Peripheral low battery red");
        description(["Fixture headphones","10% battery","low battery","Laptop battery 10%"]);
        DeviceStatus.batteryAvailable=false;test.wait(5);
        near(fill.strokeColor.a,0,"Unknown peripheral battery hides fill");near(arc.sweepAngle,0,"Unknown peripheral has no laptop fallback");dots(4);
        description(["Fixture headphones, battery unavailable","90% signal"]);
        DeviceStatus.available=false;SystemInfo.batteryPercent=40;test.wait(5);
        Tokens.reducedMotion=false;SystemInfo.batteryPercent=80;signal(.25);test.wait(40);
        check(arc.sweepAngle>80&&arc.sweepAngle<160,"Normal ring animates");
        const left=orb.children.filter(c=>"modelData" in c&&typeof c.modelData==="number").sort((a,b)=>a.x-b.x);
        check(left[1].color.a>.3&&left[1].color.a<.78,"Dot colors transition softly");
        test.wait(450);near(arc.sweepAngle,160,"Animated ring settles");dots(1);
        Tokens.reducedMotion=true;SystemInfo.batteryPercent=50;signal(.75);
        near(arc.sweepAngle,100,"Reduced motion ring changes immediately");dots(3);
        check(orb.width===26&&orb.height===26,"Orb geometry");
        console.log("STATUS ORB PASS");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''')
    environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software',
                       QS_NO_RELOAD_POPUP='1', XDG_STATE_HOME=str(workspace / 'state'),
                       XDG_CONFIG_HOME=str(workspace / 'config'), XDG_CACHE_HOME=str(workspace / 'cache'))
    result = subprocess.run(['qs', '--no-color', '-p', str(workspace)], env=environment,
                            capture_output=True, text=True, timeout=20)
    output = result.stdout + result.stderr
    assert result.returncode == 0 and MARKER in output, output
    assert not any(error in output for error in ('ReferenceError', 'TypeError', 'SyntaxError', 'ERROR')), output
    print(MARKER)
