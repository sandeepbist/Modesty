#!/usr/bin/env python3
"""Check lyric boundaries and seeks against the existing linear display behavior."""
from qml import run

run('''import QtQuick
import Quickshell
import qs.services
ShellRoot {
    id: root
    property int barChanges: 0
    Connections { target: LiveMedia; function onBarsChanged() { root.barChanges++; } }
    function check(ok, label): void { if (!ok) throw new Error(label); }
    function verify(position): void {
        Media.position = position;
        let text = "", remaining = 8;
        for (const line of LiveMedia.lines) { if (line.time > position) break; text = line.text; }
        for (const line of LiveMedia.lines) { if (line.time > position) { remaining = Math.max(1, line.time - position); break; } }
        check(LiveMedia.lyric === text, "Wrong lyric at " + position);
        check(LiveMedia.lineRemaining === remaining, "Wrong remaining time at " + position);
    }
    Timer { interval: 80; running: true; onTriggered: { try {
        Preferences.mediaLyrics = true;
        LiveMedia.loadedKey = LiveMedia.trackKey;
        LiveMedia.lines = [{time:2,text:"First"},{time:5,text:""},{time:5,text:"Duplicate"},{time:9.25,text:"Last"}];
        for (const position of [0,2,4.75,5,5.1,9.25,100,3,0,6]) verify(position);
        LiveMedia.lines = [{time:8,text:"Late"},{time:2,text:"Out of order"},{time:10,text:"Last"}];
        for (const position of [0,2,8,9,10]) verify(position);
        LiveMedia.loadedKey = "different track";
        check(LiveMedia.lyric === "" && LiveMedia.lineRemaining === 8, "Stale track lyrics");
        LiveMedia.loadedKey = LiveMedia.trackKey;
        LiveMedia.lines = [];
        verify(0); verify(100);
        LiveMedia.lines = Array.from({length: 8192}, (_, index) => ({time:index / 4,text:"Line " + index}));
        for (const position of [0,1000,2047.75,1.5,2048]) verify(position);
        Preferences.mediaLyrics = false;
        check(LiveMedia.lyric === "", "Disabled lyrics visible");
        const initial = barChanges;
        LiveMedia.receiveBars("0;0;0;0;0;0;");
        check(barChanges === initial, "Silent frame rewrote bars");
        LiveMedia.receiveBars("100;200;0;-20;25;40;");
        check(barChanges === initial + 1, "New frame did not update bars");
        check(JSON.stringify(LiveMedia.bars) === "[1,1,0,0,0.25,0.4]", "Incorrect bar clamp");
        LiveMedia.receiveBars("100;200;0;-20;25;40;");
        LiveMedia.receiveBars("100;bad;0;0;25;40;");
        LiveMedia.receiveBars("10;20;");
        check(barChanges === initial + 1, "Repeated or invalid frame rewrote bars");
        console.log("LIVE MEDIA CHECK PASS: boundaries, duplicates, blank cues, seek, track changes and long lyrics"); Qt.quit();
    } catch(error) { console.error(error); Qt.exit(1); } } }
}
''', 'LIVE MEDIA CHECK PASS: boundaries, duplicates, blank cues, seek, track changes and long lyrics')
