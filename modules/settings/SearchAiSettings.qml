import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.services
import qs.components
import qs.theme

ColumnLayout {
    id:root
    function reveal(key) {
        if(key==="gemini"||key==="jev")return credentials.itemAt(key==="gemini"?0:1).input;
        return {"notes":notes,"save-notes":saveNotes,"clear-notes":clearNotes,"delete-conversations":deleteConversations}[key]||notes;
    }
    spacing:12
    readonly property string backend:Qt.resolvedUrl("../../scripts/command-canvas.py").toString().replace("file://","")
    Component.onCompleted:Luma.refreshUsage()
    RowLayout {Layout.fillWidth:true;spacing:8
        PanelText {Layout.fillWidth:true;text:"Recent API calls · "+(Luma.usage.gemini||0)+" answers · "+(Luma.usage.jev||0)+" Jev decisions";font.pixelSize:11;color:Theme.subtext;wrapMode:Text.WordWrap}
        ActionButton {text:"Refresh";implicitHeight:28;onClicked:Luma.refreshUsage()}
    }
    PanelText {Layout.fillWidth:true;visible:!!Luma.usage.failures;text:(Luma.usage.previews||0)+" automatic answer calls · "+Luma.usage.failures+" failed calls. Local commands use no API quota.";font.pixelSize:11;color:Theme.subtext;wrapMode:Text.WordWrap}
    Repeater {
        id:credentials;model:[{id:"gemini",label:"Gemini · answers"},{id:"jev",label:"Jev · tools & decisions"}]
        ColumnLayout {
            id:credential;required property var modelData
            Layout.fillWidth:true;spacing:8
            property alias input:keyInput
            property bool configured:false
            property string message:""
            property string pendingKey:""
            function run(command:string):void {
                if(worker.running)return;
                message="";
                worker.command=command==="jev-check"?["python3",Luma.backend,command]:["python3",root.backend,command,modelData.id];
                worker.running=true;
            }
            function save():void {
                if(worker.running)return;
                pendingKey=keyInput.text.trim();keyInput.clear();run("key-set");
            }
            Component.onCompleted:run("key-status")
            PanelText {text:credential.modelData.label;font.pixelSize:12;font.weight:Font.Medium}
            RowLayout {
                Layout.fillWidth:true;spacing:8
                EntryField {id:keyInput;objectName:"custom-"+credential.modelData.id;Layout.fillWidth:true;echoMode:TextInput.Password;placeholderText:credential.configured?"Replace saved key":"API key";Accessible.name:credential.modelData.label+" API key";onAccepted:if(text.trim().length>=20)credential.save()}
                ActionButton {text:"Save";enabled:!worker.running&&keyInput.text.trim().length>=20;onClicked:credential.save()}
                ActionButton {text:"Remove";visible:credential.configured;enabled:!worker.running;onClicked:credential.run("key-clear")}
            }
            RowLayout {
                Layout.fillWidth:true
                PanelText {Layout.fillWidth:true;text:credential.message||(worker.running?"Checking…":credential.configured?"Saved privately on this PC":"No key saved");font.pixelSize:11;color:Theme.subtext;wrapMode:Text.WordWrap}
                ActionButton {text:"Check connection";visible:credential.modelData.id==="jev"&&credential.configured;enabled:!worker.running;implicitHeight:28;onClicked:credential.run("jev-check")}
            }
            Process {
                id:worker;stdinEnabled:true
                onStarted:if(credential.pendingKey){write(credential.pendingKey+"\n");credential.pendingKey="";}
                stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.configured!==undefined)credential.configured=!!data.configured;credential.message=data.ok?(worker.command[2]==="jev-check"?"Connected to TypeSafe":""):data.error||data.text||"Could not save key";}catch(e){credential.message="Could not read key status";}}}
            }
        }
    }
    Rectangle {Layout.fillWidth:true;implicitHeight:1;color:Theme.withAlpha(Theme.text,.08)}
    PanelText {text:"Personal notes";font.pixelSize:12;font.weight:Font.Medium}
    Rectangle {
        Layout.fillWidth:true;implicitHeight:Math.max(96,notes.implicitHeight+24);radius:12;color:Theme.surfaceSolid
        border.width:notes.activeFocus?1:0;border.color:Theme.accent
        TextArea {
            id:notes;objectName:"custom-notes";anchors.fill:parent;padding:12;text:Luma.memory;placeholderText:"Preferences Luma should remember. Saved only when you choose Save.";wrapMode:TextEdit.Wrap
            textFormat:TextEdit.PlainText;
            color:Theme.text;placeholderTextColor:Theme.subtext;font.family:Tokens.font;font.pixelSize:12
            selectionColor:Theme.accent;selectedTextColor:Theme.accentText;background:Item {}
            Accessible.name:"Luma personal notes"
        }
    }
    PanelText {Layout.fillWidth:true;visible:!!Luma.memoryError;text:Luma.memoryError;font.pixelSize:11;color:Theme.red;wrapMode:Text.WordWrap}
    RowLayout {Layout.fillWidth:true;spacing:8
        ActionButton {id:saveNotes;objectName:"custom-save-notes";text:"Save notes";enabled:!Luma.savingMemory;onClicked:Luma.saveMemory(notes.text)}
        ActionButton {id:clearNotes;objectName:"custom-clear-notes";text:"Clear notes";enabled:!Luma.savingMemory;onClicked:{notes.clear();Luma.saveMemory("");}}
        ActionButton {id:deleteConversations;objectName:"custom-delete-conversations";text:"Delete all conversations";enabled:!Luma.busy;onClicked:Luma.clear()}
    }
}
