#!/usr/bin/env python3
import re
from qml import ROOT, run

island = (ROOT / 'modules/island/Island.qml').read_text()
mask = re.search(r'    mask: Region \{.*?\n    \}', island, re.S)
assert mask, 'Production Island input mask missing'

run('''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    id: test
    property int phase: 0
    property var popup: null
    FloatingWindow {
        id: root; visible: true; implicitWidth: 1100; implicitHeight: 700
        property bool captureActive: false
        property bool hiddenByFullscreen: false
        Island.IslandSurface {
            id: surface; anchors.horizontalCenter: parent.horizontalCenter; y: 45
            availableWidth: root.width; availableHeight: root.height - y
            scale: Preferences.uiScale; transformOrigin: Item.Top
            visible: !root.hiddenByFullscreen
        }
        PRODUCTION_MASK
    }
    TestCase {id: driver; when: false}
    function check(value, message) {if (!value) throw new Error(message);}
    function child(name) {const value = driver.findChild(surface, name); check(value, "Missing " + name); return value;}
    function menu() {
        if (!popup) popup = driver.findChild(child("notesPanel"), "notesOverflow");
        check(popup, "Missing notesOverflow"); return popup;
    }
    function action(text) {
        for (let i = 0; i < menu().count; i++) if (menu().itemAt(i).text === text) return menu().itemAt(i);
        throw new Error("Missing action " + text);
    }
    function open() {
        menu();
        driver.mouseClick(child("notesActions"));
        driver.tryVerify(() => menu().opened, 1000, "Pointer did not open Notes menu");
    }
    function settle() {driver.tryVerify(() => !Notes.saving, 2000, "Preview mutation did not settle");}
    function pointerAction(text) {
        const row = action(text);
        for (let i = 0; i < menu().count; i++)
            if (menu().itemAt(i) === row) menu().contentItem.positionViewAtIndex(i, ListView.Contain);
        driver.mouseMove(row, row.width / 2, row.height / 2);
        check(row.hovered && row.highlighted, "Pointer hover ignored " + text);
        driver.mouseClick(row, row.width / 2, row.height / 2);
        driver.tryVerify(() => !menu().visible, 1000, "Action did not close menu " + text);
        settle();
    }
    function regionContains(region, point) {
        if (!region.item) return false;
        const local = region.item.mapFromItem(surface.parent, point.x, point.y);
        return local.x >= 0 && local.y >= 0 && local.x < region.item.width && local.y < region.item.height;
    }
    function verifyBounds() {
        const popup = menu().contentItem.parent;
        const exposed = surface.popupInputRegion;
        check(exposed === popup, "Notes popup visual bounds absent from native input exposure");
        const region = Array.from(root.mask.regions).find(value => value.item === popup);
        check(region, "Notes popup absent from production Island input mask");
        check(region.width === 0 && region.height === 0, "Popup mask adds fixed or fullscreen input bounds");
        check(Math.abs(menu().scale - Preferences.uiScale) < .001, "Popup scale differs from Notes scale");
        for (let i = 0; i < menu().count; i++) {
            const row = menu().itemAt(i);
            if (!row.text) continue;
            check(row.enabled === (row.text !== "Talk to Luma"), "Action enabled state incorrect " + row.text);
            const point = row.mapToItem(surface.parent, row.width / 2, row.height / 2);
            if (row.y + row.height / 2 - menu().contentItem.contentY < menu().contentItem.height)
                check(regionContains(region, point), "Visible row outside popup native bounds " + row.text);
        }
        const origin = popup.mapToItem(surface.parent, 0, 0);
        const bottom = popup.mapToItem(surface.parent, popup.width, popup.height);
        check(origin.x >= 0 && origin.y >= 0 && bottom.x <= root.width + .5 && bottom.y <= root.height + .5,
              "Popup escaped window bounds");
    }
    Component.onCompleted: {
        Preferences.set("motion", "instant"); Preferences.set("welcomeAtLogin", false);
        Notes.items = [{id:"popup-fixture",title:"Popup fixture",body:"Useful thought",status:"active",pinned:false,revision:1,
                        createdAt:"2026-10-13T00:00:00Z",updatedAt:"2026-10-13T00:00:00Z"}];
        Notes.select("popup-fixture"); IslandState.openMenu("notes");
    }
    Timer {id: steps; interval: 180; repeat: false; running: true; onTriggered: {try {
        if (phase === 0) {
            driver.tryVerify(() => !!driver.findChild(surface, "notesActions"), 2000);
            settle(); open(); verifyBounds();
            pointerAction("Pin note");
            check(Notes.read("popup-fixture").note.pinned, "Pointer pin ignored");
            open(); pointerAction("Unpin note");
            check(!Notes.read("popup-fixture").note.pinned, "Pointer unpin ignored");
            open(); pointerAction("Copy note body");
            check(Quickshell.clipboardText === "Useful thought", "Pointer copy ignored");
            open(); pointerAction("Export note");
            check(Notes.exportPath === "Preview export", "Pointer export note ignored");
            Notes.exportPath = "";
            open(); pointerAction("Export this collection");
            check(Notes.exportPath === "Preview export", "Pointer export collection ignored");
            open(); pointerAction("Insert bullet");
            check(child("notesBody").text === "- Useful thought", "Pointer insert bullet ignored");
            child("notesBody").cursorPosition = 0;
            open(); pointerAction("Insert task");
            check(child("notesBody").text === "- [ ] - Useful thought", "Pointer insert task ignored");
            open(); pointerAction("Archive note");
            check(Notes.read("popup-fixture").note.status === "archived", "Pointer archive ignored");
            open(); pointerAction("Restore note");
            check(Notes.read("popup-fixture").note.status === "active", "Pointer restore ignored");
            open(); pointerAction("Move to Trash");
            check(Notes.read("popup-fixture").note.status === "trash", "Pointer Trash ignored");
            open(); pointerAction("Delete permanently…");
            check(child("notesPanel").deleteId === "popup-fixture", "Pointer delete confirmation ignored");
            driver.mouseClick(child("notesDeleteCancel"));
            check(!child("notesPanel").deleteId && Notes.read("popup-fixture").ok, "Pointer delete cancel failed");
            open(); pointerAction("Restore note");
            check(Notes.read("popup-fixture").note.status === "active", "Pointer Trash restore ignored");
            child("notesActions").forceActiveFocus(); driver.keyClick(Qt.Key_Space);
            driver.tryVerify(() => menu().opened, 1000, "Keyboard did not open menu");
            for (let i = 0; i < menu().count && !action("Pin note").highlighted; i++)
                driver.keyClick(menu().currentIndex < 0 ? Qt.Key_Down : Qt.Key_Up);
            check(action("Pin note").highlighted, "Keyboard did not select Pin note");
            driver.keyClick(Qt.Key_Return); settle();
            check(Notes.read("popup-fixture").note.pinned, "Keyboard pin ignored");
            open(); driver.keyClick(Qt.Key_Escape);
            driver.tryVerify(() => !menu().visible, 1000, "Escape failed to close dropdown");
            check(IslandState.menu === "notes", "Escape closed Notes instead of dropdown");
            open(); driver.mouseClick(child("notesBody"), 12, 20);
            driver.tryVerify(() => !menu().visible, 1000, "Outside click failed to dismiss dropdown");
            check(IslandState.menu === "notes", "Outside dropdown click closed Notes");
            Preferences.set("uiScale", .85);
        } else if (phase === 1) {
            open(); verifyBounds(); pointerAction("Copy note body");
            check(Quickshell.clipboardText === child("notesBody").text, "Small-scale pointer copy ignored");
            Preferences.set("uiScale", 1.25); Theme.setMode("light");
        } else if (phase === 2) {
            open(); verifyBounds(); pointerAction("Copy note body");
            check(Quickshell.clipboardText === child("notesBody").text, "Large-scale pointer copy ignored");
            Notes.libraryOpen = true;
            surface.availableHeight = 245;
        } else if (phase === 3) {
            open(); verifyBounds();
            check(menu().contentItem.contentHeight > menu().contentItem.height && menu().contentItem.interactive,
                  "Short dropdown cannot scroll to hidden actions");
            menu().currentIndex = 10;
            menu().contentItem.positionViewAtIndex(10, ListView.Contain);
            driver.wait(30); pointerAction("Insert code block");
            check(child("notesBody").text.includes("```\\n\\n```\\n"), "Scrolled pointer action ignored");
            open(); IslandState.openMenu("calendar");
        } else if (phase === 4) {
            check(!surface.popupInputRegion, "Panel switch retained popup input bounds");
            check(!driver.findChild(surface, "notesOverflow")?.visible, "Panel switch retained dropdown");
            popup = null;
            IslandState.openMenu("notes"); surface.availableHeight = 655;
        } else if (phase === 5) {
            open(); root.hiddenByFullscreen = true;
            driver.tryVerify(() => !menu().visible, 1000, "Hidden panel retained dropdown");
            check(!surface.popupInputRegion, "Hidden panel retained popup input bounds");
            check(!Array.from(root.mask.regions).some(value => value.item === menu().contentItem.parent),
                  "Closed popup still captures native input");
            root.hiddenByFullscreen = false;
        } else if (phase === 6) {
            open(); surface.enabled = false;
            driver.tryVerify(() => !menu().visible, 1000, "Disabled panel retained dropdown");
            check(!surface.popupInputRegion, "Disabled panel retained popup input bounds");
            console.log("PASS Notes popup: pointer, keyboard, Escape, outside dismissal, scale, scroll, native mask geometry and lifecycle");
            Qt.quit(); return;
        }
        phase++; steps.restart();
    } catch (error) {console.error(error); Qt.exit(1);}}}
}
'''.replace('PRODUCTION_MASK', mask.group(0)),
    'PASS Notes popup: pointer, keyboard, Escape, outside dismissal, scale, scroll, native mask geometry and lifecycle')
