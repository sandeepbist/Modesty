import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.components
import qs.services
import qs.theme

ColumnLayout {
    id: root
    signal targetRequested(string key)
    function reveal(key) {
        if(key!=="show-artwork"&&!Preferences.terminalGreeting)return showArtwork.control;
        if(key==="gallery"){galleryOpen=true;return artworkSearch;}
        if(key==="palette"&&Preferences.terminalArtFormat!=="ascii")return formatOptions.itemAt(1);
        if(["pinned","favorites","hidden"].includes(key)&&!selected)return collections.itemAt(0);
        return {"show-artwork":showArtwork.control,"collection":collections.itemAt(0),"pinned":pinArtwork,"favorites":favoriteArtwork,"hidden":hideArtwork,"favorites-only":favoritesOnly.control,"minimal":minimalGreeting.control,"format":formatOptions.itemAt(0),"palette":paletteButton,"size":artworkSize.control}[key]||showArtwork.control;
    }
    spacing: 12
    property var artworks: []
    property string selectedId: Preferences.terminalArtPinned
    property bool galleryOpen: false
    property string search: ""
    property string error: ""
    readonly property var collection: artworks.filter(a => Preferences.terminalArtCollection === "all" || a.collection === Preferences.terminalArtCollection)
    readonly property var gallery: collection.filter(a => a.title.toLowerCase().includes(search.trim().toLowerCase()))
    readonly property var selected: artworks.find(a => a.id === selectedId) || collection[0] || null
    readonly property var enabledArt: collection.filter(a => !Preferences.terminalArtHidden.includes(a.id) && (!Preferences.terminalArtFavoritesOnly || Preferences.terminalArtFavorites.includes(a.id)))
    function toggleList(key, id): void {
        const values = Preferences[key];
        const removing = values.includes(id);
        Preferences.set(key, removing ? values.filter(v => v !== id) : values.concat([id]));
        if (key === "terminalArtHidden" && !removing && Preferences.terminalArtPinned === id) Preferences.set("terminalArtPinned", "");
    }
    function chooseCollection(value): void {
        Preferences.set("terminalArtCollection", value);
        Preferences.set("terminalArtPinned", "");
        selectedId = "";
        search = "";
    }
    Process {
        running: true
        command: ["python3", Qt.resolvedUrl("../../scripts/terminal_art.py").toString().replace("file://", "")]
        stdout: StdioCollector {onStreamFinished: {try {root.artworks=JSON.parse(text);} catch(e) {root.error="Couldn’t load artwork";}}}
        onExited: code => {if(code!==0)root.error="Couldn’t load artwork";}
    }
    RowLayout {
        Layout.fillWidth: true
        Item {Layout.fillWidth:true}
        ActionButton {text:root.galleryOpen?"Close gallery":"Browse artwork";enabled:Preferences.terminalGreeting;onClicked:root.galleryOpen=!root.galleryOpen}
    }
    PreferenceSwitch {id:showArtwork;Layout.fillWidth:true;label:"Show artwork";checked:Preferences.terminalGreeting;onToggled:checked=>Preferences.set("terminalGreeting",checked)}
    RowLayout {
        Layout.fillWidth:true;visible:!Preferences.terminalGreeting;spacing:8
        PanelText {Layout.fillWidth:true;text:"Turn on Show artwork to edit artwork controls.";font.pixelSize:12;color:Theme.subtext;wrapMode:Text.Wrap}
        ActionButton {text:"Go to Show artwork";onClicked:root.targetRequested("show-artwork")}
    }
    ColumnLayout {
        Layout.fillWidth:true
        enabled:Preferences.terminalGreeting
        spacing:12
        Flow {
            Layout.fillWidth:true
            spacing:6
            Repeater {
                id:collections;model:[{key:"portraits",name:"Portraits"},{key:"atelier",name:"Action cards"},{key:"legends",name:"Legends"},{key:"all",name:"All artwork"}]
                ActionButton {required property var modelData;text:modelData.name;primary:Preferences.terminalArtCollection===modelData.key;onClicked:root.chooseCollection(modelData.key)}
            }
        }
        Rectangle {
            Layout.fillWidth:true
            implicitHeight:218
            radius:18
            color:Theme.bgSolid
            border.width:1;border.color:Theme.withAlpha(Theme.text,.09)
            RowLayout {
                anchors.fill:parent;anchors.margins:16;spacing:18
                Item {
                    Layout.preferredWidth:Math.min(220,root.width*.44)
                    Layout.fillHeight:true
                    Image {
                        anchors.centerIn:parent
                        width:parent.width*(.65+.35*(Preferences.terminalArtSize-24)/36)
                        height:parent.height*(.65+.35*(Preferences.terminalArtSize-24)/36)
                        source:root.selected?root.selected.preview:""
                        sourceSize:Qt.size(480,480)
                        fillMode:Image.PreserveAspectFit
                        asynchronous:true
                        cache:false
                        Behavior on width {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                        Behavior on height {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                    }
                }
                ColumnLayout {
                    Layout.fillWidth:true;spacing:10
                    PanelText {Layout.fillWidth:true;text:root.selected?root.selected.title:"No artwork";font.pixelSize:16;font.weight:Font.Medium;wrapMode:Text.Wrap;elide:Text.ElideNone}
                    PanelText {Layout.fillWidth:true;text:root.selected&&Preferences.terminalArtHidden.includes(root.selected.id)?"Hidden from rotation":Preferences.terminalArtPinned?"Fixed artwork":"Rotating collection";font.pixelSize:12;color:Theme.subtext}
                    RowLayout {
                        visible:!!root.selected;spacing:8
                        IconButton {id:favoriteArtwork;objectName:"custom-favorites";icon:"favorite";label:root.selected&&Preferences.terminalArtFavorites.includes(root.selected.id)?"Remove favorite":"Add favorite";color:root.selected&&Preferences.terminalArtFavorites.includes(root.selected.id)?Theme.accent:Theme.subtext;onClicked:root.toggleList("terminalArtFavorites",root.selected.id)}
                        ActionButton {id:hideArtwork;objectName:"custom-hidden";text:root.selected&&Preferences.terminalArtHidden.includes(root.selected.id)?"Show":"Hide";onClicked:root.toggleList("terminalArtHidden",root.selected.id)}
                    }
                    ActionButton {
                        id:pinArtwork;objectName:"custom-pinned"
                        visible:!!root.selected
                        text:root.selected&&Preferences.terminalArtPinned===root.selected.id?"Rotate collection":"Keep this artwork"
                        onClicked:{
                            if(Preferences.terminalArtPinned===root.selected.id){Preferences.set("terminalArtPinned","");return;}
                            Preferences.set("terminalArtHidden",Preferences.terminalArtHidden.filter(v=>v!==root.selected.id));
                            if(Preferences.terminalArtFavoritesOnly&&!Preferences.terminalArtFavorites.includes(root.selected.id))root.toggleList("terminalArtFavorites",root.selected.id);
                            root.selectedId=root.selected.id;
                            Preferences.set("terminalArtPinned",root.selected.id);
                        }
                    }
                }
            }
        }
        EntryField {id:artworkSearch;objectName:"custom-gallery";Layout.fillWidth:true;visible:root.galleryOpen;placeholderText:"Find artwork";text:root.search;onTextEdited:root.search=text}
        Item {
            Layout.fillWidth:true
            implicitHeight:root.galleryOpen?grid.implicitHeight:0
            clip:true
            enabled:root.galleryOpen
            visible:implicitHeight>0
            Behavior on implicitHeight {NumberAnimation {duration:Tokens.reducedMotion?0:Tokens.animMedium;easing.type:Easing.OutCubic}}
            GridLayout {
                id:grid;width:parent.width;columns:3;columnSpacing:10;rowSpacing:10
                Repeater {
                    model:root.gallery
                    AbstractButton {
                        id:tile
                        required property var modelData
                        Layout.fillWidth:true
                        Layout.preferredWidth:(grid.width-20)/3
                        implicitHeight:160
                        hoverEnabled:true
                        Accessible.name:modelData.title
                        Accessible.description:Preferences.terminalArtHidden.includes(modelData.id)?"Hidden from rotation":"Select artwork"
                        onClicked:root.selectedId=modelData.id
                        HoverHandler {cursorShape:Qt.PointingHandCursor}
                        background:Rectangle {
                            radius:14;antialiasing:true
                            color:tile.hovered?Theme.withAlpha(Theme.text,.045):Theme.surfaceSolid
                            border.width:root.selected&&root.selected.id===tile.modelData.id||tile.activeFocus?2:1
                            border.color:root.selected&&root.selected.id===tile.modelData.id||tile.activeFocus?Theme.accent:Theme.withAlpha(Theme.text,.05)
                            Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                        }
                        contentItem:Item {
                            Image {
                                anchors.top:parent.top;anchors.topMargin:10;anchors.horizontalCenter:parent.horizontalCenter
                                width:parent.width-20;height:110
                                source:root.galleryOpen?tile.modelData.preview:""
                                sourceSize:Qt.size(240,240);asynchronous:true;cache:false;fillMode:Image.PreserveAspectFit
                                opacity:Preferences.terminalArtHidden.includes(tile.modelData.id)?.25:1
                                transform:Translate {y:tile.hovered?-2:0;Behavior on y {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}}
                            }
                            PanelText {anchors.left:parent.left;anchors.right:parent.right;anchors.bottom:parent.bottom;anchors.margins:12;text:tile.modelData.title;font.pixelSize:11;horizontalAlignment:Text.AlignHCenter}
                            Rectangle {
                                anchors.top:parent.top;anchors.right:parent.right;anchors.margins:8
                                width:22;height:22;radius:11;color:Theme.bgSolid
                                visible:Preferences.terminalArtFavorites.includes(tile.modelData.id)
                                Icon {anchors.centerIn:parent;icon:"favorite";size:12;color:Theme.accent}
                            }
                        }
                    }
                }
            }
        }
        PanelText {visible:!!root.error||root.enabledArt.length===0;Layout.fillWidth:true;text:root.error||"No artwork in this selection. Show an image or change your favorites filter.";wrapMode:Text.Wrap;elide:Text.ElideNone;font.pixelSize:12;color:Theme.subtext}
        Flow {
            Layout.fillWidth:true;spacing:6
            Repeater {id:formatOptions;model:[{key:"image",name:"Image"},{key:"ascii",name:"ASCII"}];ActionButton {required property var modelData;objectName:"custom-format-"+modelData.key;text:modelData.name;primary:Preferences.terminalArtFormat===modelData.key;onClicked:Preferences.set("terminalArtFormat",modelData.key)}}
            ActionButton {id:paletteButton;objectName:"custom-palette";enabled:Preferences.terminalArtFormat==="ascii";text:Preferences.terminalArtMode==="theme"?"Palette colors":"Character colors";onClicked:Preferences.set("terminalArtMode",Preferences.terminalArtMode==="theme"?"original":"theme")}
        }
        RowLayout {
            Layout.fillWidth:true;visible:Preferences.terminalArtFormat!=="ascii";spacing:8
            PanelText {Layout.fillWidth:true;text:"Choose ASCII to edit artwork palette.";font.pixelSize:12;color:Theme.subtext;wrapMode:Text.Wrap}
            ActionButton {text:"Go to Artwork format";onClicked:root.targetRequested("format")}
        }
        PreferenceSlider {id:artworkSize;Layout.fillWidth:true;label:"Artwork size";display:Preferences.terminalArtSize+" columns";from:24;to:60;stepSize:2;value:Preferences.terminalArtSize;onMoved:value=>Preferences.set("terminalArtSize",value)}
        PreferenceSwitch {id:favoritesOnly;Layout.fillWidth:true;label:"Favorites only";checked:Preferences.terminalArtFavoritesOnly;onToggled:checked=>{Preferences.set("terminalArtFavoritesOnly",checked);Preferences.set("terminalArtPinned","");}}
        PreferenceSwitch {id:minimalGreeting;Layout.fillWidth:true;label:"Minimal greeting";description:"Artwork and prompt";checked:Preferences.terminalArtMinimal;onToggled:checked=>Preferences.set("terminalArtMinimal",checked)}
        PanelText {text:"Applies to new terminals";font.pixelSize:11;color:Theme.subtext}
    }
}
