#!/usr/bin/env python3
"""Capture native dock motion at the production outer scale and reject visual regressions."""
import argparse, json, os, re, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageChops
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,default=ROOT)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--crisp',action='store_true')
parser.add_argument('--font-size',type=int,default=15)
parser.add_argument('--aperture',action='store_true',help='Freeze compact agent reveal and reject ink outside its rounded aperture')
args=parser.parse_args()
root=args.source.resolve();out=args.output.resolve()
if out.exists() and any(out.iterdir()):parser.error('output must be empty to prevent stale capture acceptance')
out.mkdir(parents=True,exist_ok=True)
settings=dict(uiScale=.9,barHeight=35,collapsedWidth=105,clusterGap=8,expandedRadius=30,innerPadding=15,fontFamily="Inter Variable",clockFontFamily="Inter Variable",showSeconds=False)
palette={"dark":{"bg":"#131315","bgSolid":"#131315","surface":"#212122","surfaceSolid":"#212122","text":"#e4e2e3","subtext":"#c5c6cd","accent":"#bdc7dd","accentText":"#252f40","secondary":"#c4c6d0","tertiary":"#dabed4","green":"#8fd49a","yellow":"#dcbf76","red":"#ffb4ab"},"light":{"bg":"#fbf8fa","bgSolid":"#fbf8fa","surface":"#efeced","surfaceSolid":"#efeced","text":"#1b1b1d","subtext":"#45474c","accent":"#212b3c","accentText":"#ffffff","secondary":"#52565e","tertiary":"#372434","green":"#286c39","yellow":"#805800","red":"#ad0d13"}}
qml = r'''//@ pragma DefaultEnv QSG_USE_SIMPLE_ANIMATION_DRIVER=1
import QtQuick
import Quickshell
import qs.services
import qs.components
import qs.theme
import "modules/island" as Island
ShellRoot {
 id:probe
 property int phase:0
 property var samples:[]
 property var label:null
 property var glyph:null
 property var wifi:null
 property var signals:null
 property var orb:null
 property bool finishing:false
 property var marks:null
 property var values:[]
 property int shot:0
 property bool grabbing:false
 property QtObject monitor:QtObject {property string name:"fixture";property var activeWorkspace:null}
 Component {id:workspace;QtObject {property int id:0;property string name:"";property var monitor;property bool urgent:false;function activate(){}}}
 FloatingWindow {visible:true;implicitWidth:640;implicitHeight:170
  Rectangle {id:canvas;anchors.fill:parent;color:"#25445a"
   Island.IslandSurface {id:surface;anchors.horizontalCenter:parent.horizontalCenter;y:40;availableWidth:640;availableHeight:130;scale:Preferences.uiScale;transformOrigin:Item.Top;monitor:probe.monitor}
  }
 }
 function walk(item){let a=[item];for(const c of item.children||[])a=a.concat(walk(c));return a;}
 function snapshot(){
  const digits=walk(label).find(c=>c instanceof SlidingDigits&&c.visible);
  const letters=digits?walk(digits).filter(c=>c instanceof PanelText&&c.visible&&c.text.length===1).map(c=>({text:c.text,x:c.mapToItem(canvas,0,0).x,y:c.mapToItem(canvas,0,0).y})):[];
  const sampleText=digits?walk(digits).find(c=>c instanceof PanelText&&c.visible&&c.text.length===1):null;
  const rendering=sampleText?{value:sampleText.renderType,name:sampleText.renderType===Text.CurveRendering?"CurveRendering":sampleText.renderType===Text.QtRendering?"QtRendering":sampleText.renderType===Text.NativeRendering?"NativeRendering":"Unknown",family:sampleText.font.family,pixelSize:sampleText.font.pixelSize}:null;
  const active=walk(marks).filter(c=>c instanceof Rectangle&&c.height===4&&c.width>4&&c.width<14).map(c=>({x:c.mapToItem(canvas,c.width/2,0).x,width:c.width}));

  const wi=wifi||glyph;
  const wifiCenter=wi?wi.mapToItem(orb,wi.width/2,wi.height/2):null;
  return {rendering,wifi:{count:wifi?1:(glyph&&glyph.visible?1:0)+(signals&&signals.opacity>0?1:0),centerError:wifiCenter?Math.abs(wifiCenter.x-13):null,opacity:wi?wi.opacity:0},phase,ms:Date.now(),p:surface.dockProgress,width:surface.dockWidth,labelCenter:label.mapToItem(canvas,label.width/2,0).x,letters,compactWifi:glyph?{opacity:glyph.opacity,x:glyph.mapToItem(canvas,glyph.width/2,0).x}:null,marker:active,status:{x:surface.controlStage.x,width:surface.controlStage.width}};
 }
 Component.onCompleted:{
  Quickshell.watchFiles=false;const settings=SETTINGS;for(const key of Object.keys(settings))Preferences[key]=settings[key];Theme.loadWallpaperPalette(PALETTE);Theme.setPalette("wallpaper");Preferences.crispText=CRISP;Preferences.motion="instant";Preferences.uiScale=.9;Preferences.barHeight=35;Preferences.collapsedWidth=105;Preferences.clusterGap=8;Preferences.shadows=true;Preferences.showAlbum=false;Preferences.showStatus=true;
  const all=walk(surface);label=all.find(c=>c instanceof RollingText&&c.text===Time.timeStr);orb=all.find(c=>c instanceof Island.StatusOrb);wifi=walk(orb).find(c=>c.objectName==="statusWifi");signals=walk(orb).find(c=>c instanceof Island.DockSignals);glyph=walk(orb).find(c=>c instanceof CompactGlyph&&c.glyph==="wifi");label.text="04:25";label.font.pixelSize=FONT_SIZE;marks=all.find(c=>c instanceof Island.WorkspaceMarks);
  for(let i=0;i<2;i++)values.push(workspace.createObject(probe,{id:i+1,name:String(i+1),monitor:probe.monitor}));
  monitor.activeWorkspace=values[0];marks.workspaces=values;
 }
 FrameAnimation {running:phase>0&&!finishing;onTriggered:probe.samples.push(probe.snapshot())}
 Timer {interval:([700,700,700,700,65,35,120,55,250,900][phase]||700);running:!finishing;repeat:true;onTriggered:{
  phase++;
  if(phase===1){Preferences.motion="gentle";Preferences.motionSpeed=1.15;IslandState.restingMode=IslandState.Dock;}
  if(phase===2)monitor.activeWorkspace=values[1];
  if(phase===3)IslandState.restingMode=IslandState.Pills;
  if(phase===4)IslandState.restingMode=IslandState.Dock;
  if(phase===5)IslandState.restingMode=IslandState.Pills;
  if(phase===6||phase===8)IslandState.restingMode=IslandState.Dock;
  if(phase===7||phase===9)IslandState.restingMode=IslandState.Pills;
  if(phase===10){finishing=true;finishWait.start();}
 }}
 Timer {interval:35;repeat:true;running:CAPTURE&&!finishing;onTriggered:{
  if(grabbing)return;grabbing=true;
  const n=shot++;console.log("SHOT",n,JSON.stringify(snapshot()));
  canvas.grabToImage(function(result){result.saveToFile("OUTPUT/"+String(n).padStart(3,"0")+".png");grabbing=false;});
 }}
 Timer {id:finishWait;interval:20;repeat:true;onTriggered:if(!grabbing){console.log("MOTION_RESULT",JSON.stringify({samples,final:surface.diagnostics()}));Qt.quit();}}
 Timer {interval:45;running:phase===4;onTriggered:monitor.activeWorkspace=values[0]}
 Timer {interval:65;running:phase===6;onTriggered:monitor.activeWorkspace=values[1]}
}
'''
STUB='pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {property bool preview:true;property bool available:true;property bool enabled:true;property bool hardwareEnabled:true;property var adapters:[];property var device:null;property var networks:[{connected:true,name:"Fixture",signalStrength:.58,known:true}];property string connectedName:"Fixture";property bool busy:false;property string error:"";property var passwordNetwork:null;property string connectivity:"Full";property string adapterName:"";function join(){}function cancel(){}function advanced(){}function disconnect(){}function forget(){}function needsPsk(){return false;}}\n'

if args.aperture:
 qml=r'''import QtQuick
import Quickshell
import qs.services
import qs.components
import qs.theme
import "modules/island" as Island
ShellRoot {
 id:probe
 property int phase:0
 property bool busy:false
 property var captures:[]
 property var cases:CASES
 FloatingWindow {visible:true;implicitWidth:640;implicitHeight:180
  Rectangle {id:canvas;anchors.fill:parent;color:"#25445a"
   Island.IslandSurface {id:surface;anchors.horizontalCenter:parent.horizontalCenter;y:40;availableWidth:640;availableHeight:140;scale:.9;transformOrigin:Item.Top}
  }
 }
 function walk(item){let a=[item];for(const c of item.children||[])a=a.concat(walk(c));return a;}
 function select(){const c=cases[phase];Preferences.collapsedWidth=c.collapsedWidth;Audio.indicatorKind=c.privacy?"microphone":"";surface.agentReveal=c.reveal;}
 Component.onCompleted:{
  Quickshell.watchFiles=false;Preferences.motion="instant";Preferences.showStatus=false;Preferences.showAlbum=false;Preferences.uiScale=.9;Preferences.barHeight=35;Preferences.privacyRadar=true;Preferences.clockFontFamily="Inter Variable";Preferences.fontFamily="Inter Variable";Preferences.contextEvents=false;Preferences.agentActivity=false;Preferences.shadows=false;Preferences.crispText=CRISP;Theme.setPalette("midnight");
  AgentWork.providerLabel="OpenCode ×12";AgentWork.kind="working";AgentWork.pulse=true;
  const time=walk(surface).find(c=>c instanceof RollingText&&c.text===Time.timeStr);time.text="04:25";time.font.pixelSize=FONT_SIZE;select();
 }
 Timer {interval:35;running:true;repeat:true;onTriggered:{
  if(busy)return;busy=true;
  const s=surface.clockStage;const c=cases[phase];const name=String(phase).padStart(3,"0")+".png";
  const agent=walk(surface).find(item=>item instanceof RollingText&&item.text===AgentWork.providerLabel&&item.font.pixelSize===13);
  const row=agent.parent;const time=walk(surface).find(item=>item instanceof RollingText&&item.text==="04:25");
  captures.push({file:name,requested:c,reveal:surface.agentReveal,agent:{visible:row.visible&&agent.visible,opacity:row.opacity,width:row.width,y:row.y,center:row.mapToItem(canvas,row.width/2,0).x},clockCenter:time.mapToItem(canvas,time.width/2,0).x,stage:{x:s.mapToItem(canvas,0,s.hoverLift).x,y:s.mapToItem(canvas,0,s.hoverLift).y,width:s.width*.9,height:s.height*.9,radius:s.capsule.radius*.9}});
  canvas.grabToImage(r=>{r.saveToFile("OUTPUT/"+name);phase++;if(phase===cases.length){console.log("APERTURE_RESULT",JSON.stringify(captures));Qt.quit();}else{select();busy=false;}});
 }}
}'''.replace('CASES',json.dumps([dict(reveal=p/20,privacy=privacy,collapsedWidth=width) for width in (90,105) for privacy in (False,True) for p in range(21)]))

with tempfile.TemporaryDirectory(prefix='modesty-motion-regression-') as directory:
 w=Path(directory)
 for name in ('components','modules','assets','theme','scripts'):(w/name).symlink_to(root/name)
 shutil.copytree(root/'services',w/'services')
 (w/'services/Wireless.qml').write_text(STUB)
 (w/'services/Audio.qml').write_text('pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton {property var outputs:[];property var inputs:[];property var streams:[];property var microphoneStreams:[];property var videoCaptureStreams:[];property var directCameras:[];property var captureStreams:[];property string captureSummary:"";property string indicatorKind:"";property var sink:null;property var source:null;property bool muted:false;property real volume:0;function setVolume(v){} }')

 (w/'shell.qml').write_text(qml.replace('FONT_SIZE',str(args.font_size)).replace('SETTINGS',json.dumps(settings)).replace('PALETTE',json.dumps(palette)).replace('CRISP','true' if args.crisp else 'false').replace('CAPTURE','true').replace('OUTPUT',str(out)))
 env=dict(os.environ,MODESTY_PREVIEW='1',QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='rhi',QSG_RHI_BACKEND='opengl',QSG_INFO='1',QS_NO_RELOAD_POPUP='1',QT_NO_XDG_DESKTOP_PORTAL='1',QT_QPA_PLATFORMTHEME='generic',XDG_STATE_HOME=str(w/'state'),XDG_CACHE_HOME=str(w/'cache'))
 try:
  r=subprocess.run(['dbus-run-session','--','quickshell','--no-color','-p',str(w)],env=env,capture_output=True,text=True,timeout=20)
 except subprocess.TimeoutExpired as error:
  (out/'run.log').write_bytes((error.stdout or b'')+(error.stderr or b''))
  raise
 log=r.stdout+r.stderr;(out/'run.log').write_text(log)
 if args.aperture:
  match=re.search(r'APERTURE_RESULT (\[[^\n]+\])',log)
  assert r.returncode==0 and match and 'OpenGL' in log,log[-4000:]
  assert not re.search(r'\bERROR\b|TypeError|ReferenceError|Unable to assign|Binding loop|Failed to',log),log[-4000:]
  captures=json.loads(match[1]);(out/'manifest.json').write_text(json.dumps(captures,indent=2))
  spills=[];endpoints=[]
  for sample in captures:
   box=sample['stage'];im=Image.open(out/sample['file']).convert('RGB');outside=[];foreground=0
   for y in range(int(box['y'])-1,int(box['y']+box['height'])+2):
    for x in range(max(0,int(box['x'])-50),min(im.width,int(box['x']+box['width'])+50)):
     if min(im.getpixel((x,y)))<=115:continue
     foreground+=1
     dx=abs(x+.5-box['x']-box['width']/2)-box['width']/2+box['radius']
     dy=abs(y+.5-box['y']-box['height']/2)-box['height']/2+box['radius']
     distance=(max(dx,0)**2+max(dy,0)**2)**.5+min(max(dx,dy),0)-box['radius']
     if distance>1:outside.append([x,y])
   if outside:spills.append(dict(file=sample['file'],pixels=len(outside),locations=outside))
   if sample['reveal']==1:endpoints.append(dict(sample,foregroundPixels=foreground))
  centers=[s['agent']['center'] for s in captures]
  summary=dict(captures=len(captures),spillCaptures=len(spills),maxSpillPixels=max([s['pixels'] for s in spills],default=0),agentCenterPhysicalRange=max(centers)-min(centers),spills=spills,compactEndpoints=endpoints)
  (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
  assert len(captures)==84 and len(endpoints)==4,'Expected all 84 captures and four compact endpoints'
  assert all(abs(s['stage']['height']-31.5)<.001 and abs(s['agent']['center']-s['clockCenter'])<=.5 for s in captures),'Agent center or resting height changed'
  assert summary['agentCenterPhysicalRange']<.001,'Agent shifts horizontally during reveal'
  assert all(s['agent']['visible'] and s['agent']['opacity']==1 and s['agent']['width']>0 and s['agent']['y']==0 and s['foregroundPixels']>20 for s in endpoints),'Compact agent label lost visible ink'
  assert not spills,f'{len(spills)} frames escape rounded aperture, maximum {summary["maxSpillPixels"]} foreground pixels'
  print('DOCK AGENT APERTURE PASS')
  raise SystemExit(0)
 match=re.search(r'MOTION_RESULT (\{[^\n]+\})',log)
 assert r.returncode==0 and match and 'OpenGL' in log,log[-4000:]
 assert not re.search(r'\bERROR\b|TypeError|ReferenceError|Unable to assign|Binding loop|Failed to',log),log[-4000:]
 result=json.loads(match[1]);(out/'result.json').write_text(json.dumps(result,indent=2))
 samples=[s for s in result['samples'] if 0<s['p']<1 and s['letters']]
 xs=[s['letters'][0]['x'] for s in samples]
 shots=[(int(a),json.loads(b)) for a,b in re.findall(r'SHOT (\d+) (\{[^\n]+\})',log)]
 manifest=[];crops=[]
 for n,s in shots:
  path=out/f'{n:03}.png'
  if not path.exists():continue
  im=Image.open(path).convert('RGB')
  if s['letters'] and s['phase']>0:
   x=round(s['labelCenter']);y=round(s['letters'][0]['y'])
   crop=im.crop((x-23,y+5,x+23,y+26));crops.append(crop)
  manifest.append(dict(file=path.name,progress=s['p'],phase=s['phase'],ms=s['ms']))
 assert len(samples)>20 and len(crops)>20,'Native driver did not exercise moving ink'
 diffs=[max(a[1] for a in ImageChops.difference(crops[0],im).getextrema()) for im in crops]
 marker=[s['marker'][0]['x'] for s in samples if s['marker']]
 summary=dict(firstGlyphPhysicalRange=max(xs)-min(xs),clockCropMaxChannelDiff=max(diffs),maxWifiCenterError=max(s['wifi']['centerError'] or 0 for s in samples),minimumWifiOpacity=min(s['wifi']['opacity'] for s in samples),maxWifiDrawings=max(s['wifi']['count'] for s in samples),frames=len(manifest),nativeScale=.9,renderMode=samples[0]['rendering']['name'],renderTypeValue=samples[0]['rendering']['value'],font=samples[0]['rendering']['family'],fontPixelSize=samples[0]['rendering']['pixelSize'],crispSetting=args.crisp)
 assert all(s['rendering']==samples[0]['rendering'] for s in samples),'Runtime text renderer changed during the run'
 failures=[]
 if summary['firstGlyphPhysicalRange']>.001:failures.append('clock glyph drifts %.6f physical pixels'%summary['firstGlyphPhysicalRange'])
 if summary['clockCropMaxChannelDiff']>1:failures.append('frozen clock raster changes by %d channel values'%summary['clockCropMaxChannelDiff'])
 if summary['maxWifiCenterError']>.001:failures.append('compact Wi-Fi leaves its center by %.6f logical pixels'%summary['maxWifiCenterError'])
 if summary['minimumWifiOpacity']<.999:failures.append('retained Wi-Fi fades to %.6f'%summary['minimumWifiOpacity'])
 if summary['maxWifiDrawings']!=1:failures.append('multiple visible Wi-Fi drawings: %d'%summary['maxWifiDrawings'])
 summary['failures']=failures
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2));(out/'summary.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps(summary,indent=2))
 assert not failures,'; '.join(failures)
print('DOCK MOTION PASS')
