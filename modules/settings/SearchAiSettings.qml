import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.services
import qs.components
import qs.theme

ColumnLayout {
    id:root
    required property QtObject drafts
    function reveal(key) {
        if(key==="gemini"||key==="jev")return credentials.itemAt(key==="gemini"?0:1).input;
        return {"notes":notes,"save-notes":Preferences.preview?notes:saveNotes,"clear-notes":Preferences.preview?notes:clearNotes,"delete-conversations":deleteConversations}[key]||notes;
    }
    spacing:12
    readonly property string backend:Qt.resolvedUrl("../../scripts/command-canvas.py").toString().replace("file://","")
    Component.onCompleted:Luma.refreshUsage()
    RowLayout {Layout.fillWidth:true;spacing:8
        PanelText {Layout.fillWidth:true;text:"Recent API calls · "+(Luma.usage.gemini||0)+" answers · "+(Luma.usage.jev||0)+" Jev decisions";font.pixelSize:12;color:Theme.subtext;wrapMode:Text.WordWrap}
        ActionButton {text:"Refresh";implicitHeight:28;onClicked:Luma.refreshUsage()}
    }
    PanelText {Layout.fillWidth:true;visible:!!Luma.usage.failures;text:(Luma.usage.previews||0)+" automatic answer calls · "+Luma.usage.failures+" failed calls. Local commands use no API quota.";font.pixelSize:12;color:Theme.subtext;wrapMode:Text.WordWrap}
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
                if(command==="key-clear"){root.drafts[modelData.id]="";keyInput.clear();}
                message="";
                worker.command=command==="jev-check"?["python3",Luma.backend,command]:["python3",root.backend,command,modelData.id];
                worker.running=true;
            }
            function save():void {
                if(worker.running)return;
                pendingKey=keyInput.text.trim();root.drafts[modelData.id]="";keyInput.clear();run("key-set");
            }
            Component.onCompleted:run("key-status")
            PanelText {text:credential.modelData.label;font.pixelSize:12;font.weight:Font.Medium}
            RowLayout {
                Layout.fillWidth:true;spacing:8
                EntryField {id:keyInput;objectName:"custom-"+credential.modelData.id;Layout.fillWidth:true;echoMode:TextInput.Password;text:root.drafts[credential.modelData.id];onTextEdited:root.drafts[credential.modelData.id]=text;placeholderText:credential.configured?"Replace saved key":"API key";Accessible.name:credential.modelData.label+" API key";onAccepted:if(text.trim().length>=20)credential.save()}
                ActionButton {text:"Save";enabled:!worker.running&&keyInput.text.trim().length>=20;onClicked:credential.save()}
                ActionButton {text:"Remove";visible:credential.configured;enabled:!worker.running;onClicked:credential.run("key-clear")}
            }
            RowLayout {
                Layout.fillWidth:true
                PanelText {Layout.fillWidth:true;text:credential.message||(worker.running?"Checking…":credential.configured?"Saved privately on this PC":"No key saved");font.pixelSize:12;color:Theme.subtext;wrapMode:Text.WordWrap}
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
        id:notesFrame
        Layout.fillWidth:true;implicitHeight:164;radius:12;color:Theme.withAlpha(Theme.text,.025)
        border.width:1;border.color:notes.activeFocus?Theme.accent:Theme.withAlpha(Theme.text,Tokens.borderAlpha)
        Flickable {
            id:notesViewport;objectName:"custom-notes-viewport"
            anchors.left:parent.left;anchors.top:parent.top;anchors.bottom:parent.bottom;anchors.margins:6
            width:parent.width-30;clip:true;boundsBehavior:Flickable.StopAtBounds
            ScrollBar.vertical:SettingsScrollBar {parent:notesFrame;anchors.top:parent.top;anchors.bottom:parent.bottom;anchors.right:parent.right;anchors.margins:6}
            TextArea.flickable:TextArea {
                id:notes;objectName:"custom-notes";padding:6;text:root.drafts.hasNotes?root.drafts.notes:Luma.memory;placeholderText:"Preferences Luma should remember. Saved only when you choose Save.";wrapMode:TextEdit.Wrap
                onTextEdited:{root.drafts.notes=text;root.drafts.hasNotes=true;}
                textFormat:TextEdit.PlainText
                color:Theme.text;placeholderTextColor:Theme.subtext;font.family:Tokens.font;font.pixelSize:12
                selectionColor:Theme.accent;selectedTextColor:Theme.accentText;background:Item {}
                Accessible.name:"Luma personal notes"
            }
        }
    }
    PanelText {Layout.fillWidth:true;visible:!!Luma.memoryError;text:Luma.memoryError;font.pixelSize:12;color:Theme.red;wrapMode:Text.WordWrap}
    Flow {Layout.fillWidth:true;spacing:8
        ActionButton {id:saveNotes;objectName:"custom-save-notes";text:"Save notes";enabled:!Preferences.preview&&!Luma.savingMemory;onClicked:{if(Preferences.preview)return;Luma.saveMemory(notes.text);root.drafts.hasNotes=false;root.drafts.notes="";}}
        ActionButton {id:clearNotes;objectName:"custom-clear-notes";text:"Clear notes";enabled:!Preferences.preview&&!Luma.savingMemory;onClicked:{if(Preferences.preview)return;notes.clear();Luma.saveMemory("");root.drafts.hasNotes=false;root.drafts.notes="";}}
        ActionButton {id:deleteConversations;objectName:"custom-delete-conversations";text:"Delete all conversations";enabled:!Luma.busy;onClicked:Luma.clear()}
    }
}
