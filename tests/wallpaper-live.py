#!/usr/bin/env python3
"""Check native wallpaper pixels and redraw lifecycle; requires --live and Hyprland."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--live", action="store_true", required=True)
parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
SOURCE = """//@ pragma DefaultEnv QSG_USE_SIMPLE_ANIMATION_DRIVER=1
//@ pragma DefaultEnv QT_QUICK_CONTROLS_STYLE=Basic
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "modules/wallpaper" as Wallpaper
import qs.services
ShellRoot {
 id:root
 property int frames:0
 property int dummyFrames:0
 property var image:wall.contentItem.children.find(x=>"decodeWidth" in x&&"ready" in x)
 Component.onCompleted:{Quickshell.watchFiles=false;Preferences.wallpaperDuration=.24;Preferences.motion="gentle";SystemInfo.wallpaperDisplay="";console.log("PROBE_READY");}
 PanelWindow {
  id:dummy;screen:Quickshell.screens[0];anchors{top:true;left:true} margins{top:Math.max(0,screen.height-360);left:420} implicitWidth:16;implicitHeight:16;exclusionMode:ExclusionMode.Ignore;mask:Region{}
  WlrLayershell.layer:WlrLayer.Overlay;WlrLayershell.namespace:"modesty-wallpaper-animation-check"
  Rectangle {anchors.fill:parent;color:"white";NumberAnimation on opacity {from:.2;to:1;duration:800;loops:Animation.Infinite;running:true}}
 }
 Wallpaper.Wallpaper {
  id:wall;screen:Quickshell.screens[0];anchors{bottom:false;right:false;top:true;left:true} margins{top:Math.max(0,screen.height-360);left:0} implicitWidth:320;implicitHeight:240
  WlrLayershell.layer:WlrLayer.Overlay;WlrLayershell.namespace:"modesty-wallpaper-lifecycle-check"
 }
 Connections {target:dummy.contentItem.Window.window;function onFrameSwapped(){root.dummyFrames++;}}
 Connections {target:wall.contentItem.Window.window;function onFrameSwapped(){root.frames++;}}
 IpcHandler {target:"probe"
  function source(path:string):void {root.image.source=path;}
  function size(width:int,height:int):void {wall.implicitWidth=width;wall.implicitHeight=height;}
  function decode(width:int,height:int):void {root.image.decodeWidth=width;root.image.decodeHeight=height;}
  function shown(value:bool):void {wall.visible=value;}
  function duration(value:int):void {Preferences.wallpaperDuration=value/1000;}
  function motion(value:string):void {Preferences.motion=value;}
  function status():string {return JSON.stringify({frames:root.frames,dummyFrames:root.dummyFrames,updates:wall.updatesEnabled,ready:root.image.ready,source:root.image.source,width:wall.width,height:wall.height,error:SystemInfo.error,pixels:root.image.children.map(x=>({source:String(x.source),opacity:x.opacity,status:x.status}))});}
  function quit():void {Qt.quit();}
 }
}"""

with tempfile.TemporaryDirectory(prefix="modesty-wallpaper-live-") as directory:
    workspace = Path(directory)
    for name in ("modules", "services", "theme", "components", "assets", "scripts"):
        (workspace / name).symlink_to(ROOT / name, target_is_directory=True)
    config = workspace / "shell.qml"
    config.write_text(SOURCE)
    colors = {"red": (230, 44, 44), "green": (39, 216, 75), "blue": (43, 101, 232)}
    for name, color in colors.items():
        Image.new("RGB", (320, 240), color).save(workspace / (name + ".png"))
    environment = dict(os.environ, MODESTY_PREVIEW="1", QS_NO_RELOAD_POPUP="1",
                       XDG_STATE_HOME=str(workspace / "state"), XDG_CACHE_HOME=str(workspace / "cache"))
    with (workspace / "app.log").open("w") as log:
        app = subprocess.Popen(["quickshell", "--no-color", "-p", str(config)], env=environment,
                               stdout=log, stderr=subprocess.STDOUT)
        def call(*args):
            return subprocess.check_output(["quickshell", "ipc", "-p", str(config), "call", "probe", *map(str, args)],
                                           text=True, timeout=4)
        def status():
            return json.loads(call("status"))
        def source(name):
            call("source", (workspace / (name + ".png")).as_uri())
        def capture(label, expected):
            time.sleep(1)
            layers = json.loads(subprocess.check_output(["hyprctl", "layers", "-j"], text=True))
            window = next(w for monitor in layers.values() for level in monitor["levels"].values()
                          for w in level if w["pid"] == app.pid and w["namespace"] == "modesty-wallpaper-lifecycle-check")
            path = workspace / "capture.png"
            subprocess.run(["grim", "-g", f"{window['x']},{window['y']} 320x240", str(path)], check=True)
            with Image.open(path) as image:
                pixels = [image.convert("RGB").getpixel(point) for point in ((80, 60), (160, 120), (240, 180))]
            assert pixels == [expected] * 3, (label, pixels, expected, status())
            print("PASS native wallpaper pixels", label, flush=True)
        try:
            deadline = time.monotonic() + 10
            while "PROBE_READY" not in (workspace / "app.log").read_text():
                assert app.poll() is None, (workspace / "app.log").read_text()
                assert time.monotonic() < deadline, "Wallpaper check startup timeout"
                time.sleep(.1)
            for name, color in colors.items():
                source(name)
                capture(name, color)
            before = status()
            time.sleep(1)
            after = status()
            assert after["dummyFrames"] - before["dummyFrames"] > 10, "Other-window animation did not run"
            assert after["frames"] - before["frames"] <= 1, "Settled wallpaper continues redrawing"
            for name in colors:
                source(name)
                time.sleep(.045)
            capture("rapid-blue", colors["blue"])
            call("decode", 120, 90)
            capture("decode-blue", colors["blue"])
            call("size", 384, 260)
            capture("resize-blue", colors["blue"])
            call("shown", "false")
            source("green")
            time.sleep(.4)
            call("shown", "true")
            capture("remap-green", colors["green"])
            call("duration", 0)
            source("red")
            capture("instant-red", colors["red"])
            call("motion", "instant")
            call("duration", 240)
            source("green")
            capture("reduced-green", colors["green"])
            source("missing")
            capture("error-retained", colors["green"])
            assert status()["error"], "Failed load did not report an error"
            call("source", "")
            capture("empty", (18, 26, 27))
            output = (workspace / "app.log").read_text()
            assert "ReferenceError" not in output and "TypeError" not in output, output
            print("PASS native wallpaper lifecycle and settled redraw suspension")
        finally:
            if app.poll() is None:
                app.terminate()
            app.wait(timeout=4)
