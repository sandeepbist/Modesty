#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = r'''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.components
ShellRoot {
 id:root
 property string output:OUTPUT_DIR
 property bool captured:false
 property string captureError:""
 property var protectedItems:[]
 FloatingWindow {id:window;visible:true;implicitWidth:1920;implicitHeight:400
  Island.IslandSurface {id:surface;availableWidth:1920;availableHeight:400;scale:Preferences.uiScale;transformOrigin:Item.TopLeft}
 }
 TestCase {id:input;when:false}
 Component {id:hideForMask;Binding {property:"opacity";value:0;restoreMode:Binding.RestoreBindingOrValue}}
 function check(ok,label){if(!ok)throw new Error(label);}
 function walk(item){let all=[item];for(const c of item.children||[])all=all.concat(walk(c));return all;}
 function box(item){const p=item.mapToItem(surface,0,0),q=item.mapToItem(surface,item.width,item.height);return {x:p.x,y:p.y,w:q.x-p.x,h:q.y-p.y};}
 function isolate(item,ancestor){
  const bindings=[];
  for(let c=item;c!==(ancestor.contentItem||ancestor);c=c.parent){check(!!c.parent,"Paint ancestor missing");for(const sibling of c.parent.children)if(sibling!==c)bindings.push(hideForMask.createObject(root,{target:sibling}));}
  return bindings;
 }
 function grab(item,path,expected){
  captured=false;captureError="";
  item.grabToImage(result=>{
   try{check(JSON.stringify(box(item))===JSON.stringify(expected),"Paint callback geometry drift "+JSON.stringify({path,expected,actual:box(item)}));check(protectedItems.every(row=>JSON.stringify(box(row.item))===JSON.stringify(row.box)),"Paint isolation changes content geometry");check(result.saveToFile(path),"Paint capture failed");}catch(e){captureError=e.toString();}
   captured=true;
  },Qt.size(surface.availableWidth,Math.ceil(surface.height*Preferences.uiScale)));
  input.tryVerify(()=>captured,3000,"Paint capture timed out");check(!captureError,captureError);
 }
 Component.onCompleted:{
  Quickshell.watchFiles=false;Preferences.motion="instant";Preferences.uiScale=.9;Preferences.barHeight=35;
  Preferences.collapsedWidth=105;Preferences.contextEvents=false;Preferences.privacyIndicatorRightPadding=19;
  Preferences.showSeconds=false;IslandState.restingMode=IslandState.Pills;
  Audio.directCameras=[{directCamera:true,label:"Fixture camera"}];AgentWork.pulse=true;
 }
 Timer {interval:150;running:true;onTriggered:{try{
  const viewport=walk(surface).find(c=>c instanceof Island.ClockViewport),privacy=walk(viewport).find(c=>c instanceof PrivacyIndicator);
  const lamp=privacy.children.find(c=>c.width===privacy.dotSize&&c.height===privacy.dotSize),capsule=surface.clockStage.capsule;
  const spring=surface.data.find(c=>c instanceof FrameSpring&&c.maximumValue===1);check(!!spring&&!!lamp,"Paint fixture missing driver or lamp");
  let id=0;
  for(const scale of [.85,1,1.25])for(const crisp of [false,true])for(const name of ["OpenCode ×12","Provider with a considerably longer name ×123"])for(const gap of [0,25,40]){
   Preferences.uiScale=scale;Preferences.crispText=crisp;Preferences.privacyIndicatorGap=gap;AgentWork.providerLabel=name;input.wait(40);
   const label=walk(surface.clockStage).find(c=>c instanceof RollingText&&c.text===name);check(!!label,"Provider paint label missing");
   for(const p of [.1,.5,.85,.95]){
    spring.reset(p);input.wait(20);const position=spring.value,velocity=spring.velocity;
    protectedItems=[label,label.parent,lamp,privacy,capsule].map(item=>({item,box:box(item)}));
    const provider=box(surface),dot=box(surface),bindings=isolate(label.parent,capsule).concat(isolate(capsule,surface));
    grab(surface,output+"/provider-"+id+".png",provider);for(const binding of bindings)binding.destroy();input.wait(10);
    const hidden=isolate(lamp,surface);grab(surface,output+"/lamp-"+id+".png",dot);for(const binding of hidden)binding.destroy();input.wait(10);
    check(spring.value===position&&spring.velocity===velocity,"Paint capture changed spring state");
    check(JSON.stringify(box(surface))===JSON.stringify(provider),"Paired capture geometry drift");
    console.log("PROVIDER_PAINT "+JSON.stringify({id,scale,crisp,name,gap,p,provider,dot,position,velocity}));
    if(scale===1&&((crisp&&name==="OpenCode ×12"&&gap===25)||(!crisp&&name.startsWith("Provider")&&gap===0)))grab(surface,output+"/scene-"+id+".png",box(surface));
    id++;
   }
  }
  console.log("PROVIDER PAINT PASS");Qt.quit();
 }catch(e){console.error(e);Qt.exit(1);}}}
}'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='modesty-provider-paint-') as directory:
        work = Path(directory)
        output = args.output.resolve() if args.output else work / 'evidence'
        output.mkdir(parents=True, exist_ok=True)
        for folder in ('components', 'modules', 'assets', 'theme', 'services', 'scripts'):
            (work / folder).symlink_to(ROOT / folder, target_is_directory=True)
        (work / 'shell.qml').write_text(SOURCE.replace('OUTPUT_DIR', json.dumps(str(output))))
        env = dict(os.environ, MODESTY_PREVIEW='1', QT_QPA_PLATFORM='offscreen',
                   QT_QUICK_BACKEND='rhi', QSG_RHI_BACKEND='opengl', QS_NO_RELOAD_POPUP='1',
                   QT_NO_XDG_DESKTOP_PORTAL='1', QT_QPA_PLATFORMTHEME='generic',
                   XDG_STATE_HOME=str(work / 'state'), XDG_CACHE_HOME=str(work / 'cache'))
        result = subprocess.run(['dbus-run-session', '--', 'qs', '--no-color', '-p', str(work)],
                                env=env, capture_output=True, text=True, timeout=60)
        log = result.stdout + result.stderr
        (output / 'native.log').write_text(log)
        (output / 'native-exit.json').write_text(json.dumps(dict(exit_code=result.returncode)))
        assert result.returncode == 0 and 'PROVIDER PAINT PASS' in log, log[-4000:]
        assert not any(e in log for e in ('ReferenceError', 'TypeError', 'Unable to assign', 'Binding loop')), log[-4000:]
        rows = [json.loads(line.split('PROVIDER_PAINT ', 1)[1]) for line in log.splitlines() if 'PROVIDER_PAINT ' in line]
        assert len(rows) == 144, len(rows)
        for row in rows:
            provider = output / f"provider-{row['id']}.png"
            lamp = output / f"lamp-{row['id']}.png"
            a, b = (Image.open(path).getchannel('A') for path in (provider, lamp))
            assert a.size == b.size and a.width == 1920, (a.size, b.size)
            products = [x * y for x, y in zip(a.tobytes(), b.tobytes())]
            row.update(alpha_contacts=sum(value > 0 for value in products),
                       maximum_alpha_product=max(products, default=0), physical_size=a.size,
                       provider_ink=a.getbbox(), lamp_ink=b.getbbox())
        (output / 'painted-overlap.json').write_text(json.dumps(rows, indent=2))
        assert all(r['lamp_ink'] for r in rows), 'Lamp masks must contain actual ink'
        assert all(r['provider_ink'] for r in rows if r['p'] <= .5), 'Early provider masks must contain actual ink'
        assert all(not r['provider_ink'] for r in rows if r['p'] >= .85), 'Provider must retire before the clock settles'
        contacts = [r for r in rows if r['alpha_contacts']]
        assert not contacts, ('Privacy/provider painted contacts', [(r['id'], r['gap'], r['p'], r['alpha_contacts']) for r in contacts])
        print('PROVIDER PAINT PASS', len(rows), 'pairs, zero raw contacts')


if __name__ == '__main__':
    main()
