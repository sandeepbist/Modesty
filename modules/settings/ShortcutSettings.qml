import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.components
import qs.services
import qs.theme
ColumnLayout {
    id:root
    spacing:12
    property string category:"Applications"
    property string editing:""
    readonly property var categories:["Applications","Workspaces","Media","System","Pill"]
    function displayChord(chord):string {
        if (!chord) return "Add shortcut";
        if (chord === "SUPER + SUPER_L" || chord === "SUPER + SUPER_R") return "Super";
        return chord.split(" + ").map(key=>({SUPER:"Super",CTRL:"Ctrl",ALT:"Alt",SHIFT:"Shift",grave:"`",Left:"←",Right:"→",Up:"↑",Down:"↓"})[key]||key).join(" + ");
    }
    function group(binding):string {
        const id=binding.id.split(":")[0];
        if(/Browser|Editor|Terminal|FileExplorer|Launcher|CommandCanvas|LumaVoice|MusicWs|CommunicationWs|TodoWs|SystemMonitorWs/.test(id))return "Applications";
        if(/Ws|Window|Group|GoTo|MoveWin/.test(id)||/dir/.test(binding.label))return "Workspaces";
        if(/Media|Volume|Audio|Brightness/.test(id+binding.label))return "Media";
        return "System";
    }
    function label(binding):string {
        const names={kbLauncher:"Applications",kbSession:"Power menu",kbShowSidebar:"Control center",kbShowPanels:"Show controls",kbClearNotifs:"Clear notifications",kbPrevWs:"Previous workspace",kbNextWs:"Next workspace",kbMusicWs:"Spotify",kbCommunicationWs:"Discord",kbSystemMonitorWs:"System monitor",kbClipboardDel:"Delete clipboard item",kbEmoji:"Emoji picker"};
        const id=binding.id.split(":")[0];
        return names[id]||binding.label.replace(/\bWs\b/g,"workspace");
    }
    readonly property var rows: {
        const desktop=Bindings.desktopBindings.map(b=>({key:"desktop:"+b.id,id:b.id,label:root.label(b),chord:b.chord,original:b.original,group:root.group(b),native:true}));
        const pill=Bindings.actions.map(a=>({key:"pill:"+a.id,id:a.id,label:a.label,chord:Bindings.assignments[a.id]||"",group:"Pill",native:false}));
        const query=search.text.trim().toLowerCase();
        return desktop.concat(pill).filter(b=>query?(b.label+" "+b.chord+" "+b.group).toLowerCase().includes(query):b.group===root.category);
    }
    Component.onCompleted:Bindings.refreshDesktop()
    EntryField {id:search;Layout.fillWidth:true;placeholderText:"Search shortcuts";onTextChanged:root.editing=""}
    Flow {Layout.fillWidth:true;spacing:6
        Repeater {model:root.categories
            ActionButton {required property string modelData;text:modelData;primary:root.category===modelData&&!search.text;onClicked:{search.clear();root.editing="";root.category=modelData;}}
        }
    }
    PanelText {Layout.fillWidth:true;visible:!!Bindings.error;text:Bindings.error;color:Theme.red;font.pixelSize:12;wrapMode:Text.Wrap;elide:Text.ElideNone}
    Repeater {model:root.rows
        Rectangle {
            id:row;required property var modelData
            readonly property bool editing:root.editing===modelData.key
            Layout.fillWidth:true;implicitHeight:editing?108:54
            radius:12;color:Theme.surfaceSolid
            border.width:editing?1:0;border.color:Theme.withAlpha(Theme.accent,.4)
            clip:true
            Behavior on implicitHeight {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
            RowLayout {x:14;y:0;width:parent.width-28;height:54;spacing:12
                PanelText {Layout.fillWidth:true;text:row.modelData.label;font.pixelSize:13;font.weight:Font.Medium}
                ActionButton {id:keycap;text:root.displayChord(row.modelData.chord);implicitHeight:30;
                    background:Rectangle {radius:9;color:keycap.hovered?Theme.withAlpha(Theme.text,.08):Theme.bgSolid;border.width:1;border.color:Theme.withAlpha(Theme.text,keycap.activeFocus?.3:.09);Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                    onClicked:{const opening=!row.editing;root.editing=opening?row.modelData.key:"";if(opening)chord.forceActiveFocus();}}
            }
            RowLayout {x:14;y:58;width:parent.width-28;height:36;spacing:8;visible:row.editing
                EntryField {id:chord;Layout.fillWidth:true;text:row.modelData.chord;placeholderText:"SUPER + ALT + T";font.pixelSize:12;onAccepted:save.clicked()}
                ActionButton {id:save;text:"Save";enabled:!Bindings.busy;onClicked:{if(row.modelData.native)Bindings.setDesktop(row.modelData.id,chord.text);else Bindings.set(row.modelData.id,chord.text);}}
                IconButton {icon:row.modelData.native?"restart_alt":"close";label:row.modelData.native?"Reset shortcut":"Remove shortcut";size:15;enabled:!Bindings.busy;onClicked:{if(row.modelData.native){chord.text=row.modelData.original;Bindings.setDesktop(row.modelData.id,chord.text);}else{chord.text="";Bindings.set(row.modelData.id,"");}}}
            }
        }
    }
    PanelText {Layout.fillWidth:true;visible:root.rows.length===0;text:"No shortcuts found";horizontalAlignment:Text.AlignHCenter;color:Theme.subtext}
}
