import QtQuick
import "../../services/FileUrls.js" as FileUrls
import QtQuick.Controls
import QtQuick.Layouts
import QtCore
import Qt.labs.folderlistmodel
import qs.components
import qs.services
import qs.theme

// The attachment browser stays inside Luma's layer and palette.
Item {
    id:root
    objectName:"lumaFilePicker"
    signal accepted(var paths)
    signal cancelled()
    property url folder:StandardPaths.writableLocation(StandardPaths.DownloadLocation)||StandardPaths.writableLocation(StandardPaths.HomeLocation)
    property var selected:[]
    property string notice:""
    readonly property string home:localPath(StandardPaths.writableLocation(StandardPaths.HomeLocation))
    readonly property int capacity:Math.max(0,3-Luma.attachments.length)
    readonly property string path:localPath(folder)
    readonly property string displayPath:path===home?"~":path.startsWith(home+"/")?"~"+path.slice(home.length):path
    function localPath(url):string {return decodeURIComponent(url.toString().replace(/^file:\/\//,""));}
    function localUrl(path:string):string {return FileUrls.fromPath(path);}
    function navigate(url):void {root.folder=url;filter.clear();notice="";}
    function toggle(path:string):void {
        notice="";
        if(Luma.attachments.includes(path))return;
        if(selected.includes(path))selected=selected.filter(p=>p!==path);
        else if(selected.length<capacity)selected=selected.concat([path]);
        else notice="Up to three attachments";
    }
    function submit():void {if(selected.length&&!Luma.busy)accepted(selected.slice(0,capacity));}
    function activate(index:int):void {
        if(index<0||index>=directory.count)return;
        if(directory.isFolder(index))navigate(directory.get(index,"fileUrl"));
        else toggle(directory.get(index,"filePath"));
    }
    function focusFilter():void {filter.forceActiveFocus();}
    function step(amount:int):void {
        entries.currentIndex=Math.max(0,Math.min(entries.count-1,entries.currentIndex+amount));
        entries.positionViewAtIndex(entries.currentIndex,ListView.Contain);
    }
    function sizeLabel(bytes):string {return bytes<1024?bytes+" B":bytes<1048576?Math.ceil(bytes/1024)+" KB":(bytes/1048576).toFixed(1)+" MB";}
    FolderListModel {
        id:directory
        folder:root.folder
        showDotAndDotDot:false;showHidden:false;showOnlyReadable:true;showDirsFirst:true;showDirs:!filter.text.trim()
        sortField:FolderListModel.Name;sortCaseSensitive:false;caseSensitive:false
        onFolderChanged:{entries.currentIndex=0;entries.contentY=0;}
    }
    Timer {id:filterDelay;interval:90;onTriggered:{directory.nameFilters=filter.text.trim()?["*"+filter.text.trim().replace(/[?*\[\]]/g,"")+"*"]:["*"];entries.currentIndex=0;entries.contentY=0;}}
    Keys.onEscapePressed:cancelled()
    Keys.onPressed:event=>{
        if((event.key===Qt.Key_Return||event.key===Qt.Key_Enter)&&(event.modifiers&Qt.ControlModifier)){root.submit();event.accepted=true;}
        else if(event.key===Qt.Key_L&&(event.modifiers&Qt.ControlModifier)){location.forceActiveFocus();location.selectAll();event.accepted=true;}
        else if(event.key===Qt.Key_Up&&(event.modifiers&Qt.AltModifier)){root.navigate(directory.parentFolder);event.accepted=true;}
    }
    ColumnLayout {
        anchors.fill:parent;spacing:12
        RowLayout {
            Layout.fillWidth:true;spacing:8
            IconButton {icon:"arrow_upward";size:16;label:"Parent folder";enabled:root.path!=="/";onClicked:root.navigate(directory.parentFolder)}
            TextInput {
                id:location;objectName:"lumaAttachmentPath";Layout.fillWidth:true;Layout.preferredHeight:32
                color:activeFocus?Theme.text:"transparent"
                Binding {target:location;property:"text";value:root.displayPath;when:!location.activeFocus;restoreMode:Binding.RestoreNone}
                font.family:Tokens.font;font.pixelSize:12;font.weight:Font.Medium
                verticalAlignment:TextInput.AlignVCenter;clip:true;selectByMouse:true
                selectionColor:Theme.accent;selectedTextColor:Theme.accentText;renderType:Tokens.textRenderType
                Accessible.name:"Folder path"
                Keys.forwardTo:[root]
                PanelText {anchors.fill:parent;text:root.displayPath;visible:!location.activeFocus;font:location.font;color:Theme.subtext;verticalAlignment:Text.AlignVCenter}
                onAccepted:{const value=text.trim().replace(/^~(?=\/|$)/,root.home);if(value.startsWith("/")){root.navigate(root.localUrl(value));root.focusFilter();}}
                Keys.onEscapePressed:root.cancelled()
            }
            IconButton {icon:"close";size:16;label:"Back to conversation";onClicked:root.cancelled()}
        }
        RowLayout {
            Layout.fillWidth:true;spacing:4
            Repeater {
                model:[{icon:"home",path:root.home,label:"Home"},{icon:"download",path:root.localPath(StandardPaths.writableLocation(StandardPaths.DownloadLocation)),label:"Downloads"},{icon:"description",path:root.localPath(StandardPaths.writableLocation(StandardPaths.DocumentsLocation)),label:"Documents"}]
                IconButton {required property var modelData;icon:modelData.icon;size:16;label:modelData.label;color:root.path===modelData.path?Theme.accent:Theme.subtext;onClicked:root.navigate(root.localUrl(modelData.path))}
            }
            Item {Layout.fillWidth:true}
            TextInput {
                id:filter;objectName:"lumaAttachmentFilter";Layout.preferredWidth:Math.min(220,root.width*.5);Layout.preferredHeight:32
                color:Theme.text;font.family:Tokens.font;font.pixelSize:13
                verticalAlignment:TextInput.AlignVCenter;clip:true;selectByMouse:true
                selectionColor:Theme.accent;selectedTextColor:Theme.accentText;renderType:Tokens.textRenderType
                Accessible.name:"Find files in this folder"
                Keys.forwardTo:[root]
                onTextChanged:filterDelay.restart()
                onAccepted:root.activate(entries.currentIndex)
                Keys.onUpPressed:root.step(-1)
                Keys.onDownPressed:root.step(1)
                Keys.onEscapePressed:root.cancelled()
                PanelText {anchors.fill:parent;text:"Find a file…";font.pixelSize:13;color:Theme.withAlpha(Theme.subtext,.7);verticalAlignment:Text.AlignVCenter;visible:!filter.text&&!filter.preeditText}
            }
        }
        ListView {
            id:entries;objectName:"lumaAttachmentList";Layout.fillWidth:true;Layout.fillHeight:true;clip:true
            model:directory;currentIndex:0;spacing:4
            boundsBehavior:Flickable.StopAtBounds
            Keys.forwardTo:[root]
            ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
            Keys.onUpPressed:root.step(-1)
            Keys.onDownPressed:root.step(1)
            Keys.onReturnPressed:root.activate(currentIndex)
            Keys.onEnterPressed:root.activate(currentIndex)
            Keys.onSpacePressed:if(currentIndex>=0&&!directory.isFolder(currentIndex))root.toggle(directory.get(currentIndex,"filePath"))
            delegate:ItemDelegate {
                id:entry;required property int index;required property string fileName
                required property string filePath;required property bool fileIsDir;required property double fileSize
                width:entries.width-8;height:43;hoverEnabled:true;focusPolicy:Qt.NoFocus
                readonly property bool chosen:root.selected.includes(filePath)||Luma.attachments.includes(filePath)
                onClicked:{entries.currentIndex=index;entries.forceActiveFocus();root.activate(index);}
                Accessible.name:fileName;Accessible.description:fileIsDir?"Folder":chosen?"Selected attachment":"File"
                background:Rectangle {
                    radius:11;color:Theme.withAlpha(Theme.text,entry.pressed?.06:entry.hovered?.035:0)
                    border.width:entry.chosen||entry.index===entries.currentIndex?1:0
                    border.color:entry.chosen?Theme.accent:Theme.withAlpha(Theme.text,.14)
                    Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                }
                contentItem:RowLayout {
                    spacing:12
                    Icon {icon:entry.fileIsDir?"folder":"description";size:18;color:entry.chosen?Theme.accent:Theme.subtext}
                    PanelText {Layout.fillWidth:true;text:entry.fileName;font.pixelSize:13;font.weight:entry.chosen?Font.Medium:Font.Normal}
                    PanelText {text:entry.fileIsDir?"":root.sizeLabel(entry.fileSize);font.pixelSize:11;color:Theme.subtext;visible:!entry.chosen}
                    Icon {icon:entry.fileIsDir?"chevron_right":"check";size:15;color:entry.chosen?Theme.accent:Theme.subtext;visible:entry.fileIsDir||entry.chosen}
                }
                leftPadding:12;rightPadding:12
            }
            PanelText {anchors.centerIn:parent;text:directory.status===FolderListModel.Loading?"Loading…":"No files here";font.pixelSize:13;color:Theme.subtext;visible:!entries.count}
        }
        RowLayout {
            Layout.fillWidth:true;spacing:12
            PanelText {Layout.fillWidth:true;text:root.notice|| (root.selected.length===1?root.selected[0].split("/").pop():root.selected.length?root.selected.length+" files":"");font.pixelSize:12;color:root.notice?Theme.yellow:Theme.subtext}
            ActionButton {text:"Attach";enabled:root.selected.length>0&&!Luma.busy;onClicked:root.submit()}
        }
    }
    Component.onCompleted:Qt.callLater(focusFilter)
}
