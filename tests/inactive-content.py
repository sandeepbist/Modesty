#!/usr/bin/env python3
from qml import run

run('''import QtQuick
import Quickshell
import "modules/island" as Island
import qs.components
import qs.services
import qs.theme
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property real physicalWidth: 120
    property real physicalHeight: 40
    property int inactiveChanges: 0
    property int welcomePaints: 0
    property var panes: []
    property var wrappers: []
    property var launcherItem
    property var wifiItem
    property real closeOpacity: 0
    property double deadline: Date.now() + 15000
    FloatingWindow {
        visible: true; implicitWidth: 1000; implicitHeight: 1000
        Island.Stage {
            id: stage; stage: "clock"
            width: root.physicalWidth; height: root.physicalHeight
            targetWidth: IslandState.sizes[panel]?.[0] ?? 120
            targetHeight: IslandState.sizes[panel]?.[1] ?? 40
        }
        Island.ControlCenter {
            id: center; x: 350; y: 100
            width: Preferences.controlsWidth - Preferences.innerPadding * 2
            height: ControlLayout.panelHeight - Preferences.innerPadding * 2
        }
        Item {
            id: helloBox; y: 800; visible: false
            WelcomeWord { id: welcome; width: 230; height: 68; progress: 1; ink: "#ef0000" }
        }
    }
    function walk(item, predicate) {
        let found = predicate(item) ? [item] : [];
        for (const child of item.children || []) found = found.concat(walk(child, predicate));
        return found;
    }
    function pane(name) { return panes.find(item => item.modelData === name); }
    function controls() { return walk(center, item => "usable" in item && "toggleTile" in item); }
    function check(ok, label) { if (!ok) throw new Error(label + " phase=" + phase); }
    function near(actual, expected, label) { check(Math.abs(actual - expected) < .0001, label + " actual=" + actual + " expected=" + expected); }
    function next() { phase++; ticks = 0; }
    function geometry(amount) {
        const item = pane("clock");
        physicalWidth = item.inset * 2 + item.width * amount;
        physicalHeight = item.inset * 2 + item.height * Math.min(1, amount + .1);
    }
    function redPixels() {
        const pixels = welcome.getContext("2d").getImageData(0, 0, welcome.width, welcome.height).data;
        let count = 0;
        for (let i = 0; i < pixels.length; i += 4)
            if (pixels[i + 3] > 0 && pixels[i] > pixels[i + 2]) count++;
        return count;
    }
    Component.onCompleted: {
        Preferences.motion = "gentle"; Preferences.motionSpeed = 1;
        ControlLayout.items = ControlLayout.items.filter(item => item.id !== "focus");
        welcome.paint.connect(() => root.welcomePaints++);
    }
    Timer {
        interval: 40; running: true; repeat: true
        onTriggered: { try {
            check(Date.now() < deadline, "Timed out"); ticks++;
            if (phase === 0) {
                panes = walk(stage, item => "outgoingScale" in item);
                if (panes.length !== 17 || !pane("clock").item || !pane("launcher").item) return;
                check(welcome.length > 0 && welcome.inkBounds.width > 0, "Hidden welcome lost metrics");
                welcomePaints = 0;
                launcherItem = pane("launcher").item;
                IslandState.menu = "clock"; stage.panel = "clock"; next();
            } else if (phase === 1 && ticks === 1) geometry(.7);
            else if (phase === 1 && ticks > 6) {
                near(pane("clock").visibleScale, .7, "Partial opening scale");
                check(!pane("clock").presented && pane("clock").opacity > .1, "Partial opening did not reveal");
                closeOpacity = pane("clock").opacity;
                stage.panel = "idle";
                near(pane("clock").outgoingScale, .7, "Close snapshot raced selection");
                const t = (.7 - .55) / .43;
                near(pane("clock").outgoingReveal, t * t * (3 - 2 * t), "Close reveal snapshot");
                geometry(.4); next();
            } else if (phase === 2) {
                near(pane("clock").transform[0].xScale, .7, "Outgoing scale followed closing bounds");
                check(pane("clock").opacity > 0 && pane("clock").opacity < closeOpacity, "Outgoing fade lost");
                stage.panel = "clock"; next();
            } else if (phase === 3 && ticks === 1) geometry(.85);
            else if (phase === 3 && ticks > 6) {
                near(pane("clock").visibleScale, .85, "Reactivation retained outgoing scale");
                stage.panel = "idle";
                near(pane("clock").outgoingScale, .85, "Second interrupted close snapshot");
                next();
            } else if (phase === 4) {
                stage.panel = "clock"; geometry(1); next();
            } else if (phase === 5 && ticks > 6) {
                check(pane("clock").presented && pane("clock").opacity > .99, "Reopened content did not settle");
                stage.panel = "idle"; geometry(.3);
                near(pane("clock").outgoingScale, 1, "Settled close lost full scale");
                for (const item of panes) item.presentationScaleChanged.connect(() => root.inactiveChanges++);
                next();
            } else if (phase === 6) {
                if (ticks === 1) { physicalWidth = 340; physicalHeight = 160; }
                else if (ticks === 2) { physicalWidth = 145; physicalHeight = 55; welcome.progress = .6; }
                else if (ticks > 4) {
                    check(inactiveChanges === 0, "Inactive scales changed with stage geometry " + inactiveChanges);
                    check(welcomePaints === 0, "Hidden welcome painted during progress updates " + welcomePaints);
                    welcome.width = 250; welcome.progress = 1; helloBox.visible = true;
                    IslandState.menu = "launcher"; stage.panel = "launcher"; next();
                }
            } else if (phase === 7 && ticks > 3) {
                const launch = pane("launcher");
                check(launch.item === launcherItem && launch.enabled && launch.visible, "Launcher lost warm readiness");
                check(launch.item.diagnostics().activeFocus, "Launcher keyboard was not ready during reveal");
                check(welcomePaints > 0 && redPixels() > 0, "Welcome did not repaint latest hidden state");
                helloBox.visible = false; welcome.progress = 0; welcome.ink = "#0000ef"; welcome.requestPaint();
                walk(launch.item, item => item.objectName === "appSearch")[0].text = "old query";
                stage.panel = "idle"; stage.panel = "launcher"; next();
            } else if (phase === 8 && ticks > 2) {
                check(pane("launcher").item === launcherItem && launcherItem.diagnostics().query === "", "Launcher reopen lost query reset");
                check(redPixels() > 0, "Invisible Canvas executed drawing");
                helloBox.visible = true;
                wrappers = walk(center, item => "entry" in item && "pitch" in item && "modelData" in item);
                check(wrappers.length === 15 && controls().length === ControlLayout.items.length, "Unconfigured controls were instantiated");
                wifiItem = controls().find(item => item.kind === "wifi");
                wifiItem.forceActiveFocus(); check(wifiItem.activeFocus, "Configured tile lost keyboard focus");
                check(ControlLayout.move("wifi", 0, 7, 3, 1), "Layout move failed"); next();
            } else if (phase === 9) {
                const wifi = wrappers.find(item => item.modelData === "wifi");
                if (ticks === 1) check(wifi.y > 0 && wifi.y < wifi.pitch * 7, "Layout move stopped animating");
                if (ticks > 8) {
                    near(wifi.y, wifi.pitch * 7, "Layout move did not settle");
                    check(controls().find(item => item.kind === "wifi") === wifiItem && wifiItem.activeFocus, "Layout update recreated configured tile");
                    check(redPixels() === 0, "Welcome did not clear when visible again");
                    ControlLayout.add("focus"); next();
                }
            } else if (phase === 10 && ticks > 7) {
                check(controls().length === ControlLayout.items.length && controls().some(item => item.kind === "focus"), "Added control not ready");
                const current = walk(center, item => "entry" in item && "pitch" in item && "modelData" in item);
                check(wrappers.every(item => current.includes(item)), "Layout addition reset tile identities");
                ControlLayout.remove("focus"); next();
            } else if (phase === 11 && ticks > 2) {
                check(controls().length === ControlLayout.items.length && !controls().some(item => item.kind === "focus"), "Removed control retained heavy content");
                console.log("INACTIVE CONTENT CHECK PASS: interrupted fades, warm launcher, hidden Canvas and stable layout identities");
                Qt.quit();
            }
        } catch (error) { console.error(error); Qt.exit(1); } }
    }
}
''', 'INACTIVE CONTENT CHECK PASS: interrupted fades, warm launcher, hidden Canvas and stable layout identities')
