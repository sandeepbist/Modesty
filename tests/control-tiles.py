#!/usr/bin/env python3
"""Production control tiles must create only the controls their kind needs."""
from qml import run

run('''import QtQuick
import Quickshell
import "modules/island" as Island
import qs.services
ShellRoot {
    id: root
    property int phase: 0
    FloatingWindow {
        id: window
        visible: true; implicitWidth: 700; implicitHeight: 700
        color: "#111111"
        Grid {
            id: grid; columns: 4; spacing: 10; anchors.centerIn: parent
            Repeater {
                model: ["media", "display", "sound", "wifi", "bluetooth", "lock", "appearance", "notifications", "peace", "nightlight", "focus", "awake", "recorder", "power"]
                Island.ControlTile { required property string modelData; kind: modelData; width: 150; height: 140 }
            }
        }
    }
    function walk(item, predicate) {
        let found = predicate(item) ? [item] : [];
        for (const child of item.children || []) found = found.concat(walk(child, predicate));
        return found;
    }
    function verify(): void {
        try {
            for (const tile of grid.children.filter(child => "kind" in child)) {
                // ScrollBar also exposes orientation/snapMode; range endpoints
                // distinguish the actual level Slider from notification scrollbars.
                const sliders = walk(tile, item => "from" in item && "to" in item && "snapMode" in item);
                const art = walk(tile, item => "decodeWidth" in item && "transitionDuration" in item);
                if (sliders.length !== (["display","sound"].includes(tile.kind) ? 1 : 0)) throw new Error(tile.kind + " creates unused sliders: " + sliders.length);
                if (art.length !== (tile.kind === "media" ? 1 : 0)) throw new Error(tile.kind + " creates unused art: " + art.length);
                if (sliders.length && (sliders[0].orientation !== (tile.vertical ? Qt.Vertical : Qt.Horizontal)
                    || sliders[0].width <= 0 || sliders[0].height <= 0)) throw new Error(tile.kind + " lost slider geometry");
            }
            const tiles = grid.children.filter(child => "kind" in child);
            if (phase === 0) { for (const tile of tiles) { tile.width = 72; tile.height = 160; } }
            else if (phase === 1) tiles[3].kind = "media";
            else if (phase === 2) tiles[3].kind = "display";
            else if (phase === 3) tiles[3].kind = "wifi";
            else { console.log("CONTROL TILE CHECK PASS: kind changes, slider orientation and unused subtree removal"); Qt.quit(); }
            phase++;
        } catch (error) { console.error(error); Qt.exit(1); }
    }
    Timer { interval: 120; running: true; repeat: true; onTriggered: root.verify() }
}
''', 'CONTROL TILE CHECK PASS: kind changes, slider orientation and unused subtree removal')
