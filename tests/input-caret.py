#!/usr/bin/env python3
"""Keep native editing authoritative while the shared caret moves and blinks."""
from pathlib import Path
import re
from qml import ROOT, run

for path in (ROOT/'components/EntryField.qml', *ROOT.glob('modules/**/*.qml')):
    source = path.read_text()
    for match in re.finditer(r'\b(TextInput|TextField|TextArea)\s*\{', source):
        tail = source[match.end():]
        depth = 1
        end = 0
        for end, character in enumerate(tail):
            depth += (character == '{') - (character == '}')
            if not depth:
                break
        block = tail[:end]
        assert 'cursorDelegate:' in block, f'Native editor has no shared caret: {path}'

caret = (ROOT/'components/InputCaret.qml').read_text()
assert not re.search(r'editor\.(text|selectedText|preeditText)\b', caret), 'Caret copies editor content'
assert 'ShaderEffectSource' not in caret, 'Caret captures sensitive pixels'

run('''import QtQuick
import QtQuick.Controls
import QtTest
import Quickshell
import qs.components
import qs.services
import qs.theme
ShellRoot {
    id:root
    property int phase:0
    FloatingWindow {
        visible:true;implicitWidth:550;implicitHeight:350
        TextInput {id:plain;x:20;y:15;width:200;height:35;font.pixelSize:18;clip:true;selectByMouse:true;cursorDelegate:InputCaret {editor:plain}}
        EntryField {id:field;x:20;y:65;width:220;text:"office"}
        Flickable {
            id:view;x:20;y:115;width:280;height:150;clip:true
            TextArea.flickable:TextArea {id:body;wrapMode:TextEdit.Wrap;textFormat:TextEdit.PlainText;selectByMouse:true;cursorDelegate:InputCaret {editor:body;viewport:view}}
        }
        EntryField {id:secure;x:20;y:290;width:220;echoMode:TextInput.Password;passwordMaskDelay:0}
    }
    TestCase {id:keyboard;when:false}
    function check(ok,label){if(!ok)throw new Error(label);}
    function caret(editor){const found=keyboard.findChild(editor,"inputCaret");check(found,"Missing native caret");return found;}
    function placed(editor){const draw=caret(editor),native=editor.cursorRectangle;check(Math.abs(draw.x-native.x)<.01&&Math.abs(draw.y-native.y)<.01,"Caret root moved away from native geometry");}
    Timer {interval:120;running:true;repeat:true;onTriggered:{try{
        if(root.phase===0){Preferences.motion="fluid";Preferences.motionSpeed=1;plain.forceActiveFocus();}
        else if(root.phase===1){placed(plain);check(!caret(plain).moving,"Initial caret swept from origin");keyboard.keyClick("a");keyboard.wait(16);check(caret(plain).moving&&Math.abs(caret(plain).visualX-caret(plain).x)>.1,"TextInput had no caret movement");}
        else if(root.phase===2){check(plain.text==="a"&&plain.cursorPosition===1,"Caret changed native typing");placed(plain);keyboard.keyClick(Qt.Key_Z,Qt.ControlModifier);check(plain.text==="","Undo lost native history");keyboard.keyClick(Qt.Key_Z,Qt.ControlModifier|Qt.ShiftModifier);check(plain.text==="a","Redo lost native history");plain.selectAll();}
        else if(root.phase===3){check(plain.selectedText==="a"&&!caret(plain).moving&&!caret(plain).blinking,"Selection changed or retained caret work");field.forceActiveFocus();field.cursorPosition=2;}
        else if(root.phase===4){placed(field);check(!caret(plain).blinking&&!caret(plain).moving,"Unfocused caret retained work");keyboard.keyClick("x");keyboard.wait(16);check(caret(field).moving&&Math.abs(caret(field).visualX-caret(field).x)>.1,"Native typing had no caret movement");Preferences.motion="instant";check(!caret(field).moving&&caret(field).visualX===caret(field).x,"Reduced motion retained caret travel");body.forceActiveFocus();body.text="Line one\\nمرحبا office 👩‍💻\\nLast line";body.cursorPosition=body.length;}
        else if(root.phase===5){Preferences.motion="fluid";placed(body);keyboard.keyClick("q");keyboard.wait(16);check(caret(body).moving&&Math.abs(caret(body).visualX-caret(body).x)>.1,"TextArea had no caret movement");view.contentY=15;keyboard.wait(1);check(!caret(body).moving&&caret(body).visualX===caret(body).x,"Viewport scroll retained caret travel");keyboard.keyClick(Qt.Key_Home);placed(body);secure.forceActiveFocus();keyboard.keyClick("k");}
        else if(root.phase===6){check(secure.text==="k"&&secure.echoMode===TextInput.Password,"Secure editor changed native echo policy");secure.echoMode=TextInput.Normal;check(secure.echoMode===TextInput.Normal,"Reveal changed native echo policy");secure.clear();field.forceActiveFocus();field.readOnly=true;secure.visible=false;}
        else if(root.phase===7){check(!caret(secure).blinking&&!caret(secure).moving,"Hidden caret retained work");check(!caret(field).blinking&&!caret(field).moving,"Read-only caret retained work");console.log("INPUT CARET PASS");Qt.quit();}
        root.phase++;
    }catch(error){console.error(error);Qt.exit(1);}}}
}''', 'INPUT CARET PASS')
