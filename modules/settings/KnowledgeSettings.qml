import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Quickshell
import qs.services
import qs.components
import qs.theme

ColumnLayout {
    function reveal(key){return key==="rebuild"&&Preferences.lumaKnowledgeRoots.length?rebuildIndex:addFolder;}
    spacing:12
    Component.onCompleted:Knowledge.refresh()
    FolderDialog {
        id:picker;title:"Choose a knowledge folder"
        onAccepted:{
            const path=decodeURIComponent(String(selectedFolder).replace(/^file:\/\//,""));
            Preferences.set("lumaKnowledgeRoots",Preferences.lumaKnowledgeRoots.concat([path]));
            if(!Preferences.lumaKnowledgeRoots.includes(path)){Knowledge.error="Choose a visible folder inside your home directory, rather than the whole home folder.";return;}
            Knowledge.rebuild();
        }
    }
    RowLayout {
        Layout.fillWidth:true;spacing:8
        PanelText {Layout.fillWidth:true;text:"Search inside your PDFs and notes.";font.pixelSize:12;color:Theme.subtext}
        IconButton {icon:"info";size:14;color:Theme.subtext;label:"Indexed locally. Submitted questions share matching passages with Jev and your answer provider. Scanned PDFs need a text layer."}
    }
    Repeater {
        model:Preferences.lumaKnowledgeRoots
        RowLayout {
            required property string modelData
            Layout.fillWidth:true;spacing:10
            Icon {icon:"folder";size:18;color:Theme.subtext}
            PanelText {Layout.fillWidth:true;text:modelData.replace(Quickshell.env("HOME"),"~");font.pixelSize:12;elide:Text.ElideMiddle}
            IconButton {icon:"close";size:14;label:"Remove knowledge folder";enabled:!Knowledge.busy;onClicked:{Preferences.set("lumaKnowledgeRoots",Preferences.lumaKnowledgeRoots.filter(p=>p!==modelData));Knowledge.rebuild();}}
        }
    }
    RowLayout {
        Layout.fillWidth:true;spacing:8
        ActionButton {id:addFolder;objectName:"custom-folders";text:"Add folder";enabled:!Knowledge.busy;onClicked:picker.open()}
        IconButton {id:rebuildIndex;objectName:"custom-rebuild";icon:"refresh";size:16;label:"Refresh local index";visible:Preferences.lumaKnowledgeRoots.length>0;enabled:!Knowledge.busy;onClicked:Knowledge.rebuild()}
        Item {Layout.fillWidth:true}
        ActivityPulse {running:Knowledge.busy;visible:running}
    }
    PanelText {Layout.fillWidth:true;visible:Knowledge.busy||!!Knowledge.error||Preferences.lumaKnowledgeRoots.length>0;text:Knowledge.error||(Knowledge.busy?"Updating local passages…":Knowledge.stats.documents+" documents · "+Knowledge.stats.passages+" passages");font.pixelSize:11;color:Knowledge.error?Theme.red:Theme.subtext;wrapMode:Text.WordWrap}
}
