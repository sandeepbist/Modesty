#!/usr/bin/env python3
import os,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1]
SOURCE='''import QtQuick
import Quickshell
import Quickshell.Widgets
import "modules/island" as Island
import qs.services
ShellRoot {
 property int frame:0
 readonly property var cases:[
 [{x:60,y:40,width:35,height:35,radius:17.5,alpha:1},{x:130,y:40,width:105,height:35,radius:17.5,alpha:1},{x:270,y:40,width:35,height:35,radius:17.5,alpha:1}],
 [{x:60,y:40,width:35,height:35,radius:17.5,alpha:0},{x:130,y:40,width:105,height:35,radius:17.5,alpha:1},{x:270,y:40,width:35,height:35,radius:17.5,alpha:1}],
 [{x:60,y:40,width:35,height:35,radius:17.5,alpha:.5},{x:130,y:40,width:105,height:35,radius:17.5,alpha:1},{x:270,y:40,width:35,height:35,radius:17.5,alpha:1}],
 [{x:80,y:40,width:200,height:65,radius:20,alpha:1},{x:80,y:40,width:200,height:65,radius:20,alpha:1},{x:80,y:40,width:200,height:65,radius:20,alpha:1}],
 [{x:80,y:40,width:200,height:65,radius:20,alpha:1},{x:80,y:40,width:200,height:65,radius:20,alpha:0},{x:80,y:40,width:200,height:65,radius:20,alpha:0}],
 [{x:60,y:40,width:100,height:50,radius:15,alpha:1},{x:120,y:40,width:100,height:50,radius:15,alpha:1},{x:120,y:40,width:100,height:50,radius:15,alpha:0}],
 [{x:80,y:40,width:200,height:65,radius:20,alpha:0},{x:80,y:40,width:200,height:65,radius:20,alpha:0},{x:80,y:40,width:200,height:65,radius:20,alpha:0}]]
 FloatingWindow {visible:true;implicitWidth:360;implicitHeight:160
  Rectangle {id:canvas;anchors.fill:parent;color:"#80e090"
   Island.DockContour {id:contour;frames:cases[Math.min(frame,cases.length-1)]}
  }
 }
 Component.onCompleted:{Preferences.motion="instant";Preferences.shadows=true;}
 Timer {interval:60;repeat:true;running:true;onTriggered:canvas.grabToImage(function(result){result.saveToFile("OUTPUT/"+frame+".png");frame++;if(frame===cases.length){console.log("DOCK CONTOUR GL PASS");Qt.quit();}})}
}
'''
with tempfile.TemporaryDirectory(prefix='modesty-contour-pixels-') as d:
    w=Path(d)
    for n in ('components','modules','assets','theme','services','scripts'):(w/n).symlink_to(ROOT/n)
    (w/'shell.qml').write_text(SOURCE.replace('OUTPUT',str(w)))
    env=dict(os.environ,MODESTY_PREVIEW='1',QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='rhi',QSG_RHI_BACKEND='opengl',QSG_INFO='1',XDG_STATE_HOME=str(w/'state'),XDG_CACHE_HOME=str(w/'cache'))
    r=subprocess.run(['qs','--no-color','-p',str(w)],env=env,capture_output=True,text=True,timeout=20)
    log=r.stdout+r.stderr
    assert r.returncode==0 and 'DOCK CONTOUR GL PASS' in log and 'OpenGL' in log,log
    assert not any(x in log for x in ('ERROR','TypeError','ReferenceError','Failed to')),log
    images=[Image.open(w/f'{i}.png').convert('RGB') for i in range(7)]
    assert images[1].getpixel((77,57))==images[1].getpixel((10,10)),'Zero-alpha owner leaves a phantom'
    a,b,c=(images[i].getpixel((77,57)) for i in range(3))
    assert all(min(x,y)<z<max(x,y) for x,y,z in zip(a,b,c)),'Shape opacity does not affect fill'
    assert ImageChops.difference(images[3],images[4]).getbbox() is None,'Coincident owners duplicate shadow, lighting or border'
    assert images[5].getpixel((121,65))==images[5].getpixel((100,65))==images[5].getpixel((180,65)),'Union has an internal outline'
    assert images[6].getpixel((150,65))==images[6].getpixel((10,10)), 'Hidden owners leave rendered geometry'
print('DOCK CONTOUR GL PASS: zero alpha, partial alpha, coincident shadow and exterior-only border')
