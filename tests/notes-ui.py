#!/usr/bin/env python3
from qml import run

run('''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    id: test
    property int phase: 0
    property string firstId: ""
    property string secondId: ""
    property string firstBody: ""
    property real firstScroll: 0
    property int firstCursor: 0
    FloatingWindow {
        id: window; visible: true; implicitWidth: 900; implicitHeight: 700
        Loader {
            id: panel; x: 30; y: 30; width: 396; height: 386
            sourceComponent: Island.NotesMenu {}
        }
    }
    TestCase {id: keyboard; when: false}
    function check(value, message) {if (!value) throw new Error(message);}
    function child(name) {const item=keyboard.findChild(panel.item,name);check(item,"Missing "+name);return item;}
    function settle() {keyboard.tryVerify(()=>!Notes.saving,2000,"Preview mutation did not settle");check(!Notes.saving,"Preview mutation still saving");}
    function type(text) {for(let i=0;i<text.length;i++)keyboard.keyClick(text[i]);}
    Component.onCompleted: Preferences.set("motion", "instant")
    Timer {id: steps; interval: 180; repeat: false; running: true; onTriggered: {try {
        if(phase===0) {
            check(Notes.loaded,"Preview service not loaded");
            check(Notes.items.length===0,"Preview read live notes");
            check(child("notesBody").activeFocus,"Open did not focus body");
            type("First thought");
            firstId=Notes.activeId;
            check(firstId&&Notes.draft.body==="First thought","Typing did not create service-owned draft");
            keyboard.keyClick(Qt.Key_Z,Qt.ControlModifier);
            check(child("notesBody").text!=="First thought","Normal undo lost history during draft sync");
            keyboard.keyClick(Qt.Key_Z,Qt.ControlModifier|Qt.ShiftModifier);
            check(child("notesBody").text==="First thought","Normal redo failed");
            firstId=Notes.activeId;
            keyboard.keyClick(Qt.Key_Tab);
            check(child("notesBody").text==="First thought"&&!child("notesBody").activeFocus,"Tab inserted text or failed visible focus navigation");
            child("notesBody").forceActiveFocus();
            keyboard.keyClick(Qt.Key_S,Qt.ControlModifier);settle();
            check(!Notes.dirty,"Ctrl+S did not flush preview draft");
            child("notesBody").text=Array.from({length:45},(_,i)=>"Line "+i+" of the first thought").join("\\n");
            firstBody=child("notesBody").text;
            child("notesBody").cursorPosition=27;
            child("notesScroll").contentY=65;
            panel.item.remember();firstCursor=27;firstScroll=child("notesScroll").contentY;
            keyboard.keyClick(Qt.Key_N,Qt.ControlModifier);
            check(!Notes.activeId&&!child("notesBody").text,"Ctrl+N did not open blank draft");
        } else if(phase===1) {
            check(child("notesBody").activeFocus,"New note did not focus body");
            type("Second thought");secondId=Notes.activeId;
            check(secondId!==firstId&&Notes.items.length===2,"New note replaced existing note");
            panel.item.selectNote(firstId);
        } else if(phase===2) {
            check(child("notesBody").text===firstBody,"Switch lost first draft");
            check(child("notesBody").cursorPosition===firstCursor,"Switch lost per-note cursor");
            check(Math.abs(child("notesScroll").contentY-firstScroll)<2,"Switch lost per-note scroll");
            panel.active=false;
        } else if(phase===3) {
            check(Notes.draft.body===firstBody,"Unload lost service-owned draft");
            panel.active=true;
        } else if(phase===4) {
            check(child("notesBody").text===firstBody,"Reopen lost draft body="+child("notesBody").text.length+" draft="+Notes.draft.body.length+" expected="+firstBody.length+" active="+Notes.activeId);
            child("notesActions").forceActiveFocus();keyboard.keyClick(Qt.Key_Space);
            keyboard.tryVerify(()=>child("notesOverflow").opened,1000,"Keyboard actions menu did not open");
            keyboard.keyClick(Qt.Key_Down);keyboard.keyClick(Qt.Key_Return);settle();
            check(Notes.read(firstId).note.pinned,"Keyboard pin action failed");
            keyboard.keyClick(Qt.Key_F,Qt.ControlModifier);
        } else if(phase===5) {
            check(Notes.libraryOpen&&child("notesSearch").activeFocus,"Ctrl+F did not open/focus search");
            check(panel.item.compact&&panel.item.listVisible&&!panel.item.editorVisible,"Narrow library does not separate list/editor");
            type("Second");check(panel.item.results.length===1,"Search did not filter body text");
            keyboard.keyClick(Qt.Key_Down);keyboard.keyClick(Qt.Key_Return);
        } else if(phase===6) {
            check(Notes.activeId===secondId&&panel.item.editorVisible&&!panel.item.listVisible,"Keyboard result selection failed");
            keyboard.keyClick(Qt.Key_Escape);
            check(!panel.item.query&&panel.item.editorVisible,"Escape did not clear search before leaving editor");
            keyboard.keyClick(Qt.Key_Escape);
            check(panel.item.listVisible&&!panel.item.editorVisible,"Back did not return to compact library");
            panel.width=656;
        } else if(phase===7) {
            check(!panel.item.compact&&panel.item.listVisible&&panel.item.editorVisible,"Wide library did not show split view");
            panel.item.selectNote(secondId);Notes.setPinned(secondId,true);settle();
            panel.item.category="pinned";panel.item.query="";
            check(panel.item.results.length===2&&panel.item.results.some(note=>note.id===secondId),"Pinned collection missing note");
            check(panel.item.libraryTitle(panel.item.results.find(note=>note.id===secondId))==="Second thought","Optional title did not use body line");
            check(panel.item.libraryPreview(panel.item.results.find(note=>note.id===secondId))==="","One-line note duplicated title and preview");
            Notes.setStatus(secondId,"archived");settle();panel.item.category="archived";
            check(panel.item.results.length===1&&!Notes.read(secondId).note.pinned,"Archive failed or retained pin");
            Notes.setStatus(secondId,"trash");settle();panel.item.category="trash";
            check(panel.item.results.length===1&&Notes.undo,"Trash/Undo state missing");
            Notes.undoTrash();settle();check(Notes.read(secondId).note.status==="archived","Undo did not restore archive");
            Notes.setStatus(secondId,"active");settle();check(Notes.read(secondId).note.status==="active","Restore failed");
            panel.item.copyNote();check(Quickshell.clipboardText==="Second thought","Copy failed");
            const original=child("notesBody").text;panel.item.insertText("- [ ] ");
            check(child("notesBody").text!==original,"Formatting insertion failed");
            keyboard.keyClick(Qt.Key_Z,Qt.ControlModifier);check(child("notesBody").text===original,"Formatting lost native undo");
            check(!child("notesVoice").enabled,"Preview voice control enabled hardware input");
            Notes.setStatus(secondId,"trash");settle();panel.item.deleteId=secondId;
        } else if(phase===8) {
            check(!child("notesBody").enabled,"Delete confirmation left editor enabled");
            child("notesDeleteCancel").forceActiveFocus();keyboard.keyClick(Qt.Key_Space);
            check(!panel.item.deleteId&&Notes.read(secondId).ok,"Cancel permanently deleted note");
            panel.item.deleteId=secondId;child("notesDeleteConfirm").forceActiveFocus();keyboard.keyClick(Qt.Key_Space);settle();
            check(!Notes.read(secondId).ok,"Confirmed deletion retained note");
            panel.item.selectNote(firstId);keyboard.wait(1);
            Notes.error="Simulated save failure";check(child("notesRetry").visible&&!child("notesRecover").visible,"Readable Notes failure controls incorrect");
            child("notesRetry").forceActiveFocus();check(child("notesRetry").activeFocus,"Retry focus rejected window="+window.activeFocusItem+" modal="+panel.item.deleteId);keyboard.keyClick(Qt.Key_Space);settle();
            check(!Notes.error,"Keyboard retry did not clear failure focused="+child("notesRetry").activeFocus+" enabled="+child("notesRetry").enabled+" error="+Notes.error);
            panel.item.enabled=false;
            const before=Notes.draft.body;child("notesBody").forceActiveFocus();keyboard.keyClick(Qt.Key_X);
            check(Notes.draft.body===before,"Hidden content accepted keyboard input");
            console.log("PASS Notes UI: draft survival, native undo/redo, keyboard, search, geometry, lifecycle and hidden input");Qt.quit();return;
        }
        phase++;steps.restart();
    } catch(error) {console.error(error);Qt.exit(1);}}}
}
''', 'PASS Notes UI: draft survival, native undo/redo, keyboard, search, geometry, lifecycle and hidden input')

run('''import QtQuick
import Quickshell
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    id: test
    property int phase: 0
    FloatingWindow {visible:true;implicitWidth:1100;implicitHeight:700
        Island.IslandSurface {id:surface;availableWidth:1100;availableHeight:600}
    }
    function check(value,message) {if(!value)throw new Error(message);}
    Component.onCompleted: {Preferences.set("motion","instant");IslandState.openMenu("notes");}
    Timer {interval:150;repeat:true;running:true;onTriggered:{try {
        if(phase===0) {
            check(surface.clockStage.targetWidth===440&&surface.clockStage.targetHeight===440,"Capture target differs from 440x440");
            Notes.libraryOpen=true;
        } else if(phase===1) {
            check(surface.clockStage.targetWidth===700&&surface.clockStage.targetHeight===496,"Library target differs from 700x496");
            surface.availableWidth=500;surface.availableHeight=290;
        } else if(phase===2) {
            check(surface.clockStage.width<=surface.clockStage.maximumWidth,"Width escaped screen clamp");
            check(surface.clockStage.height<=surface.maximumHeight,"Height escaped screen clamp");
            check(surface.clockStage.targetWidth>=0&&surface.clockStage.targetHeight<=surface.maximumHeight,"Invalid compact targets");
            const custom=[{id:"wifi",x:1,y:1,w:3,h:1}];ControlLayout.items=custom;Preferences.set("footerVisible",false);
            check(!ControlLayout.footerShown,"Disabled footer reserves space for obsolete Notes fallback");
            check(JSON.stringify(ControlLayout.items)===JSON.stringify(custom),"Notes discovery moved custom controls");
            console.log("PASS Notes geometry: capture/library targets, screen clamps and custom layout discovery");Qt.quit();return;
        }
        phase++;
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''', 'PASS Notes geometry: capture/library targets, screen clamps and custom layout discovery')

run('''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
import qs.theme
ShellRoot {
    property int phase: 0
    FloatingWindow {visible:true;implicitWidth:800;implicitHeight:550
        Island.NotesMenu {id:panel;width:656;height:460}
    }
    TestCase {id:keyboard;when:false}
    function check(value,message) {if(!value)throw new Error(message);}
    Component.onCompleted: {
        Preferences.set("motion","instant");
        Notes.items=[
            {id:"old",title:"",body:"\\nIdea <one>\\nA safe & useful preview",status:"active",pinned:false,revision:1,createdAt:"2025-01-01T00:00:00Z",updatedAt:"2025-01-01T00:00:00Z"},
            {id:"new",title:"Recent thought",body:"Some words",status:"active",pinned:false,revision:1,createdAt:"2026-01-01T00:00:00Z",updatedAt:"2026-01-01T00:00:00Z"}
        ];
        Notes.select("old");Notes.libraryOpen=true;
    }
    Timer {interval:150;repeat:true;running:true;onTriggered:{try {
        if(phase===0) {
            check(panel.results.map(note=>note.id).join(",")==="new,old","Library initial order incorrect");
            check(panel.libraryTitle(panel.results[1])==="Idea <one>","Fallback title did not skip blank lines");
            check(panel.libraryPreview(panel.results[1])==="A safe & useful preview","Fallback preview duplicated heading");
            panel.query="safe";
            check(panel.markedText("A safe & useful preview").includes("<b>safe</b>")&&panel.markedText("<safe>").includes("&lt;"),"Search highlight lost match or escaped literal code");
            panel.query="";
            keyboard.findChild(panel,"notesBody").forceActiveFocus();keyboard.keyClick(Qt.Key_X);keyboard.keyClick(Qt.Key_S,Qt.ControlModifier);
        } else if(phase===1) {
            if(Notes.saving)return;
            check(panel.results.map(note=>note.id).join(",")==="new,old","Autosave reordered list during typing");
            keyboard.findChild(panel,"notesSearch").forceActiveFocus();
            check(panel.results.map(note=>note.id).join(",")==="old,new","Return to library did not refresh order");
            console.log("PASS Notes library: fallback titles, safe highlights and stable typing order");Qt.quit();return;
        }
        phase++;
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''', 'PASS Notes library: fallback titles, safe highlights and stable typing order')

run('''import QtQuick
import QtTest
import Quickshell
import "modules/island" as Island
import qs.services
ShellRoot {
    property int phase:0
    property string identifier:""
    FloatingWindow {visible:true;implicitWidth:700;implicitHeight:500
        Island.NotesMenu {id:panel;width:396;height:386}
    }
    TestCase {id:keyboard;when:false}
    function check(value,message) {if(!value)throw new Error(message);}
    function child(name) {return keyboard.findChild(panel,name);}
    function settle() {keyboard.tryVerify(()=>!Notes.saving,2000);check(!Notes.saving,"Save did not settle");}
    Component.onCompleted:Preferences.set("motion","instant")
    Timer {interval:150;repeat:true;running:true;onTriggered:{try {
        if(phase===0) {
            Notes.edit({title:"t".repeat(300),body:"Saved body"},0,0);Notes.flush("fixture");settle();identifier=Notes.activeId;
            const title=child("notesTitle");title.forceActiveFocus();title.cursorPosition=title.length;
            keyboard.keyClick(Qt.Key_X);
            check(title.text==="t".repeat(300)&&Notes.draft.title===title.text&&!Notes.dirty&&!Notes.error,"301st key escaped title limit");
            title.select(295,300);Quickshell.clipboardText="paste overflow";keyboard.keyClick(Qt.Key_V,Qt.ControlModifier);
            check(title.text==="t".repeat(295)+"paste"&&Notes.draft.title===title.text&&Notes.dirty,"Native paste exceeded title limit or lost accepted replacement");
            title.selectAll();Quickshell.clipboardText="p".repeat(301);keyboard.keyClick(Qt.Key_V,Qt.ControlModifier);
            check(title.text==="p".repeat(300)&&Notes.draft.title===title.text,"Oversized title paste diverged from service draft");
            Notes.flush("title-limit");settle();
            child("notesBody").text="before\\0after";
            check(Notes.draft.body==="before\\0after"&&Notes.dirty&&Notes.error,"NUL editor text escaped service draft");
            const failure=Notes.flush("nul");check(Notes.receipt(failure.ticket).status==="refused","Invalid editor content was persisted");
            Notes.retry();check(Notes.saveState==="Failed"&&Notes.dirty,"Retry mislabeled invalid editor Saved");
            panel.newNote();
        } else if(phase===1) {
            check(!child("notesBody").text,"New note did not clear editor");panel.selectNote(identifier);
        } else if(phase===2) {
            check(child("notesBody").text==="before\\0after"&&Notes.draft.body===child("notesBody").text&&Notes.dirty,"Switch discarded rejected editor content");
            panel.copyNote();check(Quickshell.clipboardText==="before\\0after","Copy lost rejected editor text");
            child("notesRetry").forceActiveFocus();keyboard.keyClick(Qt.Key_Space);
            check(Notes.saveState==="Failed"&&Notes.dirty&&child("notesBody").text===Notes.draft.body,"Native Retry cleared invalid draft failure");
            child("notesBody").forceActiveFocus();keyboard.keyClick(Qt.Key_A,Qt.ControlModifier);
            for(const character of "Recovered")keyboard.keyClick(character);
            keyboard.keyClick(Qt.Key_S,Qt.ControlModifier);settle();
            check(Notes.saveState==="Saved"&&Notes.draft.body==="Recovered","Corrected editor content did not save");
            const count=Notes.items.length;
            panel.newNote();keyboard.tryVerify(()=>child("notesBody").activeFocus,1000);
            keyboard.keyClick(Qt.Key_X);keyboard.keyClick(Qt.Key_Z,Qt.ControlModifier);settle();
            check(!Notes.activeId&&!Notes.dirty&&Notes.items.length===count&&!Notes.error,"Undo of unsaved first character left an empty failed note");
            child("notesBody").text="\\0";
            Notes.flush("invalid-blank");child("notesBody").clear();Notes.retry();settle();
            check(!Notes.activeId&&!Notes.dirty&&Notes.items.length===count&&!Notes.error,"Cleared invalid new draft remained unsavable");
            console.log("PASS Notes native limits: keyboard, paste, invalid draft retry, switch, copy and correction");Qt.quit();return;
        }
        phase++;
    }catch(error){console.error(error);Qt.exit(1);}}}
}
''', 'PASS Notes native limits: keyboard, paste, invalid draft retry, switch, copy and correction')
