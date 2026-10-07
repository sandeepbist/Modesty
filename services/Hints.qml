pragma Singleton
import QtQuick
import Quickshell

Singleton {
    id: root
    property Item target: null
    property string text: ""
    property bool shown: false
    function show(item: Item, label: string): void { if (target === item && text === label && (shown || delay.running)) return; delay.stop(); shown = false; target = item; text = label; if (label.length) delay.restart(); }
    function hide(item: Item): void { if (target === item) { delay.stop(); shown = false; target = null; } }
    function clear(): void { delay.stop(); shown = false; target = null; }
    Timer { id: delay; interval: Preferences.tooltipDelay; onTriggered: root.shown = !!root.target }
    Connections { target: IslandState; function onStateChanged() { root.clear(); } }
}
