//@ pragma Env QT_QPA_PLATFORMTHEME=generic
//@ pragma Env MODESTY_PREVIEW=1
import QtQuick
import Quickshell
import "modules/island" as Island
import "modules/canvas" as Canvas
ShellRoot {
    Island.Island { id:island;visible: false }
    Island.IslandDropTarget { sourceIsland:island;visible: false }
    Canvas.CommandCanvas { visible: false }
    Timer { interval: 150; running: true; onTriggered: { console.log("VALIDATION COMPLETE"); Qt.quit(); } }
}
