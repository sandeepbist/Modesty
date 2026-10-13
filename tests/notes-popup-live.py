#!/usr/bin/env python3
"""Verify the production Notes popup with native Wayland pointer events.

Requires --live, Hyprland, and an explicit virtual-pointer helper. The helper
reads `move X Y`, `down 272 0`, and `up 272 0` and acknowledges each with `ok`.
Its absolute extents must match --pointer-size, which defaults to 1920 1080.
"""
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import tempfile
import time


SOURCE = '''//@ pragma DefaultEnv QT_QUICK_CONTROLS_STYLE=Basic
import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    id: root
    property var island: null
    property bool ready: false
    property int backstopClicks: 0
    readonly property string monitorName: MONITOR_NAME
    Component.onCompleted: {
        Quickshell.watchFiles = false;
        Preferences.set("motion", "instant"); Preferences.set("welcomeAtLogin", false);
        Notes.items = [{id:"native-popup-fixture",title:"Native popup fixture",body:"Useful thought",status:"active",pinned:false,revision:1,
                        createdAt:"2026-10-13T00:00:00Z",updatedAt:"2026-10-13T00:00:00Z"}];
        Notes.select("native-popup-fixture");
        console.log("BACKSTOP_READY");
    }
    PanelWindow {
        id: backstop
        screen: Quickshell.screens.find(screen => screen.name === root.monitorName)
        anchors {top:true;bottom:true;left:true;right:true}
        exclusiveZone: 0
        exclusionMode: ExclusionMode.Ignore
        color: "transparent"
        WlrLayershell.namespace: BACKSTOP_NAMESPACE
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
        MouseArea {anchors.fill:parent;acceptedButtons:Qt.AllButtons;onClicked:root.backstopClicks++;onWheel:event=>event.accepted=true}
    }
    Component {
        id: islandFactory
        Island.Island {
            screen: backstop.screen
            exclusiveZone: 0
            WlrLayershell.namespace: ISLAND_NAMESPACE
        }
    }
    TestCase {id: finder;when:false}
    function child(name) {return root.island ? finder.findChild(root.island.surface, name) : null;}
    function menu() {const panel = child("notesPanel"); return panel ? finder.findChild(panel, "notesOverflow") : null;}
    function rectangle(item) {
        const start = item.mapToItem(root.island.contentItem, 0, 0);
        const end = item.mapToItem(root.island.contentItem, item.width, item.height);
        return {x:start.x,y:start.y,width:end.x-start.x,height:end.y-start.y};
    }
    function snapshot() {
        const popup = menu(), body = child("notesBody"), rows = [];
        if (popup && popup.visible) for (let index = 0; index < popup.count; index++) {
            const row = popup.itemAt(index);
            if (!row.text) continue;
            const bounds = rectangle(row), center = row.mapToItem(root.island.contentItem, row.width/2, row.height/2);
            const edge = row.mapToItem(root.island.contentItem, Math.max(row.width/2,row.width-8), row.height/2);
            const viewport = popup.contentItem;
            const local = row.mapToItem(viewport, row.width/2, row.height/2);
            rows.push(Object.assign({index,text:row.text,enabled:row.enabled,hovered:row.hovered,highlighted:row.highlighted,
                       center:{x:center.x,y:center.y},edge:{x:edge.x,y:edge.y},inView:local.y>=0&&local.y<viewport.height}, bounds));
        }
        return {ready:root.ready,preview:Preferences.preview,scale:Preferences.uiScale,mode:Theme.mode,
                screenWidth:backstop.screen.width,screenHeight:backstop.screen.height,
                opened:!!popup?.opened,visible:!!popup?.visible,menu:IslandState.menu,
                body:body?.text,pinned:!!Notes.read("native-popup-fixture").note?.pinned,saving:Notes.saving,
                backstopClicks:root.backstopClicks,rows,button:child("notesActions")?rectangle(child("notesActions")):null,
                popup:popup?.visible?rectangle(popup.contentItem.parent):null,
                scrollable:!!popup&&popup.contentItem.contentHeight>popup.contentItem.height,
                popupMask:!!popup&&Array.from(root.island.mask.regions).some(region=>region.item===popup.contentItem.parent)};
    }
    Timer {
        interval: 30;repeat:true;running:!!root.island&&!root.ready
        onTriggered: if (child("notesActions") && child("notesBody")?.text === "Useful thought" && !Notes.saving) {
            root.ready = true; console.log("ISLAND_READY");
        }
    }
    IpcHandler {
        target: "notesPopupProbe"
        function start():void {if(!root.island){root.island=islandFactory.createObject(root);IslandState.openMenu("notes");}}
        function status():string {return JSON.stringify(root.snapshot());}
        function configure(scale:int,mode:string,height:int):void {
            root.menu()?.close(); Preferences.set("uiScale",scale/100); Theme.setMode(mode);
            root.island.surface.availableHeight=height>0?height:root.island.height-root.island.surface.y;
            IslandState.openMenu("notes");
        }
        function open():void {root.menu().open();}
        function prepare(text:string):void {
            const popup=root.menu();
            for(let index=0;index<popup.count;index++) if(popup.itemAt(index).text===text)
                popup.contentItem.positionViewAtIndex(index,ListView.Contain);
            child("notesBody").cursorPosition=0;
        }
        function close():void {root.menu().close();IslandState.dismissCurrent();}
    }
}
'''


def command(*args):
    return subprocess.check_output(list(map(str, args)), text=True, timeout=4)


def until(function, message, timeout=4):
    deadline = time.monotonic() + timeout
    while True:
        value = function()
        if value:
            return value
        assert time.monotonic() < deadline, message
        time.sleep(.04)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--pointer", type=Path, required=True, help="Explicit stdin virtual-pointer helper")
    parser.add_argument("--pointer-size", type=int, nargs=2, default=(1920, 1080), metavar=("WIDTH", "HEIGHT"),
                        help="Absolute extents compiled into the explicit helper")
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path, help="Save source identity, native observations, and fixture log as JSON")
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    pointer_path = args.pointer.resolve()
    report = {"sourceRoot": str(source_root), "pointer": str(pointer_path), "pointerSize": args.pointer_size, "cases": []}
    assert os.environ.get("WAYLAND_DISPLAY"), "Requires a native Wayland session"
    assert pointer_path.is_file() and os.access(pointer_path, os.X_OK), "Explicit pointer helper is not executable"
    assert (source_root / "modules/island/Island.qml").is_file(), "Source root has no production Island"
    monitors = json.loads(command("hyprctl", "monitors", "-j"))
    assert len(monitors) == 1, "Pointer verification requires one monitor to prove absolute extents"
    monitor = monitors[0]
    assert monitor["x"] == monitor["y"] == monitor.get("transform", 0) == 0 and monitor["scale"] == 1, \
        "Pointer verification requires an untransformed monitor at origin with scale 1"
    assert [monitor["width"], monitor["height"]] == list(args.pointer_size), \
        "Monitor dimensions differ from the declared pointer helper extents"
    original_cursor = json.loads(command("hyprctl", "cursorpos", "-j"))
    executable = shutil.which("quickshell") or shutil.which("qs")
    assert executable, "Quickshell is not installed"

    with tempfile.TemporaryDirectory(prefix="modesty-notes-popup-live-") as directory:
        workspace = Path(directory)
        for name in ("modules", "services", "theme", "components", "assets", "scripts"):
            (workspace / name).symlink_to(source_root / name, target_is_directory=True)
        namespace = f"modesty-notes-native-{os.getpid()}"
        backstop_namespace, island_namespace = namespace + "-backstop", namespace + "-island"
        config = workspace / "shell.qml"
        config.write_text(SOURCE.replace("MONITOR_NAME", json.dumps(monitor["name"]))
                          .replace("BACKSTOP_NAMESPACE", json.dumps(backstop_namespace))
                          .replace("ISLAND_NAMESPACE", json.dumps(island_namespace)))
        environment = dict(os.environ, MODESTY_PREVIEW="1", QT_QPA_PLATFORM="wayland", QS_NO_RELOAD_POPUP="1",
                           HOME=str(workspace / "home"), XDG_CONFIG_HOME=str(workspace / "config"),
                           XDG_STATE_HOME=str(workspace / "state"), XDG_CACHE_HOME=str(workspace / "cache"),
                           XDG_DATA_HOME=str(workspace / "data"))
        for name in ("home", "config", "state", "cache", "data"):
            (workspace / name).mkdir()
        app = pointer = None
        log_path = workspace / "app.log"

        def call(*args):
            return command(executable, "ipc", "-p", config, "call", "notesPopupProbe", *args)

        def status():
            return json.loads(call("status"))

        def layers():
            return json.loads(command("hyprctl", "layers", "-j"))[monitor["name"]]["levels"]["3"]

        def own_layer(name):
            return next((layer for layer in layers() if layer["pid"] == app.pid and layer["namespace"] == name), None)

        def proof():
            overlay = layers()
            backstop = next((index for index, layer in enumerate(overlay) if layer["pid"] == app.pid and layer["namespace"] == backstop_namespace), -1)
            island = next((index for index, layer in enumerate(overlay) if layer["pid"] == app.pid and layer["namespace"] == island_namespace), -1)
            assert 0 <= backstop < island == len(overlay)-1, "Compositor does not place test Island above its backstop and other overlays"
            report["layerProof"] = overlay
            return overlay[island]

        def native(*parts):
            assert pointer.poll() is None, "Virtual pointer helper exited"
            pointer.stdin.write(" ".join(map(str, parts)) + "\n")
            pointer.stdin.flush()
            assert select.select([pointer.stdout], [], [], 4)[0], "Virtual pointer acknowledgement timeout"
            assert pointer.stdout.readline().strip() == "ok", "Virtual pointer did not acknowledge input"

        def move(point):
            window = proof()
            x, y = round(window["x"] + point["x"]), round(window["y"] + point["y"])
            assert 0 <= x < monitor["width"] and 0 <= y < monitor["height"], "Target escaped monitor bounds"
            native("move", x, y)
            return {"x": x, "y": y}

        def open_menu():
            until(lambda: status()["button"], "Notes controls did not load")
            call("open")
            def opened():
                value = status()
                return value if value["opened"] else None
            return until(opened, "Notes popup did not open")

        def hover(text, case):
            call("prepare", text)
            time.sleep(.08)
            before = status()
            row = next(value for value in before["rows"] if value["text"] == text)
            assert row["enabled"] and row["inView"], f"Action is not enabled and visible: {text}"
            button = before["button"]
            def hovered():
                value = status()
                item = next((item for item in value["rows"] if item["text"] == text), None)
                return value if item and item["hovered"] and item["highlighted"] else None
            for position in ("center", "edge"):
                popup = before["popup"]
                target = row[position]
                assert popup["x"] < target["x"] < popup["x"] + popup["width"] and \
                    popup["y"] < target["y"] < popup["y"] + popup["height"], "Native target escaped the popup clip"
                move({"x": button["x"] + button["width"]/2, "y": button["y"] + button["height"]/2})
                point = move(target)
                attempt = {"text": text, "position": position, "point": point, "row": row}
                case["hovers"].append(attempt)
                try:
                    after = until(hovered, f"Native {position} hover ignored {text}; point={point}")
                except BaseException:
                    attempt["observed"] = status()
                    raise
                attempt["observed"] = next(item for item in after["rows"] if item["text"] == text)
                attempt["backstopClicks"] = after["backstopClicks"]
            return point

        def click(text, case):
            open_menu()
            point = hover(text, case)
            clicks = status()["backstopClicks"]
            native("down", 272, 0)
            native("up", 272, 0)
            until(lambda: not status()["visible"], f"Native click did not close {text}")
            until(lambda: not status()["saving"], f"Fake Notes mutation did not settle after {text}")
            after = status()
            case["clicks"].append({"text": text, "point": point, "observed": after})
            assert after["backstopClicks"] == clicks, f"Native click escaped to backstop: {text}"
            assert after["menu"] == "notes" and "body" in after, f"Native menu action unexpectedly closed Notes: {text}"
            assert not after["popupMask"], "Closed popup retains a production input region"
            return after, point

        def interrupted(signum, frame):
            raise KeyboardInterrupt(f"Signal {signum}")

        previous_handlers = {signum: signal.signal(signum, interrupted) for signum in (signal.SIGTERM, signal.SIGINT)}
        try:
            with log_path.open("w") as log:
                app = subprocess.Popen([executable, "--no-color", "-p", str(config)], env=environment,
                                       stdout=log, stderr=subprocess.STDOUT)
                until(lambda: "BACKSTOP_READY" in log_path.read_text() or app.poll() is not None, "Backstop startup timeout", 10)
                assert app.poll() is None, log_path.read_text()
                until(lambda: own_layer(backstop_namespace), "Backstop never mapped")
                call("start")
                until(lambda: "ISLAND_READY" in log_path.read_text() or app.poll() is not None, "Production Island startup timeout", 10)
                assert app.poll() is None, log_path.read_text()
                until(lambda: own_layer(island_namespace), "Production Island never mapped")
                proof()
                initial = status()
                assert initial["preview"] and initial["ready"], "Fixture is not isolated preview Notes"
                assert [initial["screenWidth"], initial["screenHeight"]] == list(args.pointer_size), "Qt screen dimensions differ from pointer extents"
                pointer = subprocess.Popen([str(pointer_path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                           stderr=subprocess.DEVNULL, text=True, bufsize=1)
                expected_body = "Useful thought"
                for mode in ("dark", "light"):
                    for scale in (85, 100, 125):
                        case = {"mode": mode, "scale": scale/100, "hovers": [], "clicks": []}
                        report["cases"].append(case)
                        call("configure", scale, mode, 0)
                        time.sleep(.15)
                        opened = open_menu()
                        assert opened["mode"] == mode and opened["scale"] == scale/100, "Scale or mode did not apply"
                        enabled = [row["text"] for row in opened["rows"] if row["enabled"]]
                        assert "Pin note" in enabled and "Insert code block" in enabled and "Insert task" in enabled, "Fixture actions are missing"
                        assert not next(row for row in opened["rows"] if row["text"] == "Talk to Luma")["enabled"], "Preview voice action is enabled"
                        for text in enabled:
                            hover(text, case)
                        after, _ = click("Pin note", case)
                        assert after["pinned"], "Native Pin did not change the fake note"
                        after, _ = click("Unpin note", case)
                        assert not after["pinned"], "Native Unpin did not change the fake note"
                        after, _ = click("Insert task", case)
                        expected_body = "- [ ] " + expected_body
                        assert after["body"] == expected_body, "Native Insert task produced the wrong editor body"
                        call("configure", scale, mode, 245)
                        time.sleep(.15)
                        assert open_menu()["scrollable"], "Short Notes popup does not scroll"
                        after, stale_point = click("Insert code block", case)
                        expected_body = "```\n\n```\n" + expected_body
                        assert after["body"] == expected_body, "Native last Insert action produced the wrong editor body"
                        call("close")
                        until(lambda: not status()["visible"] and status()["menu"] == "none", "Notes panel did not close")
                        time.sleep(.15)
                        assert not status()["popupMask"], "Closed Notes panel retains popup input"
                        clicks = status()["backstopClicks"]
                        proof()
                        native("move", stale_point["x"], stale_point["y"])
                        native("down", 272, 0)
                        native("up", 272, 0)
                        until(lambda: status()["backstopClicks"] == clicks + 1, "Stale popup position still captures input after close")
                        print(f"PASS native Notes popup {mode} scale={scale/100}: {len(enabled)} enabled rows with center and edge hover, pin, task, scrolled code, released input", flush=True)
                output = log_path.read_text()
                assert "ReferenceError" not in output and "TypeError" not in output, output
                report["result"] = "pass"
        except BaseException as error:
            report.update(result="fail", error=str(error))
            print(f"FAIL production native Notes popup source-root={source_root}: {error}", flush=True)
            raise
        finally:
            cleanup_errors = []
            restored = False
            try:
                if pointer and pointer.poll() is None:
                    native("up", 272, 0)
                    native("move", round(original_cursor["x"]), round(original_cursor["y"]))
                    cursor = json.loads(command("hyprctl", "cursorpos", "-j"))
                    restored = all(abs(cursor[axis]-original_cursor[axis]) <= 1 for axis in ("x", "y"))
            except BaseException as error:
                report["pointerRestoreFallback"] = str(error)
            try:
                if not restored:
                    subprocess.run(["hyprctl", "dispatch", "movecursor", f"{round(original_cursor['x'])} {round(original_cursor['y'])}"],
                                   capture_output=True, text=True, timeout=4, check=True)
                cursor = json.loads(command("hyprctl", "cursorpos", "-j"))
                assert all(abs(cursor[axis]-original_cursor[axis]) <= 1 for axis in ("x", "y")), "Cursor restoration did not reach saved position"
                report["cursorRestored"] = True
            except BaseException as error:
                cleanup_errors.append(str(error))
                report["cursorRestored"] = False
            finally:
                for process in (pointer, app):
                    if process and process.poll() is None:
                        try:
                            process.terminate()
                            try:
                                process.wait(timeout=4)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait(timeout=4)
                        except BaseException as error:
                            cleanup_errors.append(str(error))
                for signum, handler in previous_handlers.items():
                    signal.signal(signum, handler)
                report["fixtureLog"] = log_path.read_text() if log_path.exists() else ""
                if cleanup_errors:
                    report["cleanupErrors"] = cleanup_errors
                    if report.get("result") == "pass":
                        report.update(result="fail", error="; ".join(cleanup_errors))
                if args.report:
                    args.report.parent.mkdir(parents=True, exist_ok=True)
                    args.report.write_text(json.dumps(report, indent=2) + "\n")
            if cleanup_errors and "error" in report and report["error"] == "; ".join(cleanup_errors):
                raise AssertionError(report["error"])
    print(f"PASS production native Notes popup source-root={source_root}", flush=True)


if __name__ == "__main__":
    main()
