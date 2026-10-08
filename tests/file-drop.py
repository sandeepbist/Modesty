#!/usr/bin/env python3
"""Check drag ownership and stable native target geometry using production QML."""
from pathlib import Path
import tempfile
from qml import run

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "modules/island/IslandDropTarget.qml").read_text()
# Replace only the native layer facade; retain production geometry, mask and handlers.
source = source.replace("PanelWindow {", "FloatingWindow {", 1)
source = "\n".join(line for line in source.splitlines() if not line.strip().startswith(("exclusionMode:", "anchors {", "margins {", "WlrLayershell.")))
with tempfile.TemporaryDirectory(prefix="modesty-drop-target-") as temporary:
    directory = Path(temporary)
    (directory / "DropTarget.qml").write_text(source)

    run('''import QtQuick
import Quickshell
import qs.services
import "MODULE" as Island
ShellRoot {
    id: root
    Item { id: firstOwner }
    Item { id: secondOwner }
    FloatingWindow {
        id: source
        visible:true;implicitWidth:1000;implicitHeight:100
        property bool hiddenByFullscreen:false
        property alias surface:surface
        Item {
            id:surface;width:1000;height:100
            property alias clockStage:clock
            Item {
                id:clock;x:450;width:100;height:35
                property real hoverLift:0
                property string panel:"idle"
                property bool nearRest:true
                property alias capsule:capsule
                Rectangle {id:capsule;radius:17.5}
                signal activated(real localX)
            }
        }
    }
    Island.DropTarget {id:target;sourceIsland:source;visible:false}
    function check(ok,label) {if(!ok)throw new Error(label);}
    Timer {interval:100;running:true;onTriggered:{try {
        IslandDrop.beginDrag(firstOwner);
        check(IslandDrop.dragging&&IslandState.state==="dropcue","Drag cue missing");
        IslandDrop.beginDrag(secondOwner);
        IslandDrop.endDrag(firstOwner);
        check(IslandDrop.dragging&&IslandDrop.dragOwner===secondOwner,"Old target cleared the new target's drag");
        IslandDrop.endDrag(secondOwner);
        check(!IslandDrop.dragging,"Leaving current target retained drag state");
        IslandDrop.beginDrag(null);
        check(!IslandDrop.dragging,"Invalid owner started a drag");
        check(target.liveBox.width>=Math.ceil((IslandState.sizes.dropcue[0]+12)*Preferences.uiScale),"Native target is smaller than the expanded cue");
        target.heldBox=target.liveBox;target.holding=true;
        const held=target.box;
        clock.width=176;clock.x=412;clock.panel="dropcue";
        check(target.box.x===held.x&&target.box.width===held.width,"Cue animation moved the native surface");
        target.completing=true;target.holding=false;
        clock.width=380;clock.panel="files";
        check(target.box.x===held.x&&target.box.width===held.width,"Drop completion moved the native surface");
        target.completing=false;
        check(target.box.width===target.liveBox.width,"Finished target retained stale geometry");
        check(!IslandDrop.accept([])&&IslandDrop.files.length===0,"Preview executed file processing");
        console.log("FILE DROP CHECK PASS: ownership, cue coverage, frozen geometry and completion");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''.replace('MODULE', directory.as_uri()),'FILE DROP CHECK PASS: ownership, cue coverage, frozen geometry and completion')
