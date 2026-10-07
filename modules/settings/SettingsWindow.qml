import QtQuick
import QtQuick.Dialogs
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.services
import qs.components
import qs.theme
import "../island" as Island
import "SettingsCatalog.js" as Catalog

FloatingWindow {
    id:window
    title:"Modesty Settings"
    implicitWidth:960;implicitHeight:720
    minimumSize:Qt.size(760,560)
    color:Theme.bgSolid
    visible:IslandState.settingsOpen
    onVisibleChanged:if(!visible)IslandState.settingsOpen=false
    IpcHandler {
        target:"settings"
        function section(index:int):void {if(index>=0&&index<Catalog.legacy.length)root.navigate(Catalog.legacy[index]);}
        function page(name:string):void {if(Catalog.pages.some(p=>p.id===name))root.navigate(name);}
        function find(query:string):void {search.text=query;search.forceActiveFocus();}
        function reveal(page:string,block:string,key:string):void {if(Catalog.pages.some(p=>p.id===page))root.navigate(page,block,key);}
        function status():string {return JSON.stringify({page:root.pageId,query:search.text,results:root.results.map(r=>({label:r.label,page:r.page,block:r.block})),companionSide:Preferences.companionSide,companionInset:Preferences.companionInset});}
        function artwork():void {root.artworkRequested=true;root.navigate("terminal");IslandState.settingsOpen=true;}
        function capture(path:string):void {if(Preferences.preview)root.grabToImage(result=>result.saveToFile(path));}
    }
    FileDialog {id:avatarPicker;title:"Choose profile picture";nameFilters:["Images (*.png *.jpg *.jpeg *.webp)"];onAccepted:Preferences.set("profileImage",String(selectedFile))}
    Item {
        id:root;anchors.fill:parent;focus:true
        Rectangle {anchors.fill:parent;color:Theme.bgSolid;z:-1}
        property string pageId:IslandState.settingsPage
        onPageIdChanged:IslandState.settingsPage=pageId
        property var back:[]
        property var forward:[]
        property var groupPages:({})
        property string highlight:""
        property string targetBlock:""
        property bool artworkRequested:false
        readonly property var current:Catalog.page(pageId)
        readonly property var results:Catalog.search(search.text)
        readonly property bool searching:search.text.trim().length>0
        function navigate(id,block,key,history) {
            if(id!==pageId){if(history!==false){back=back.concat([pageId]).slice(-32);forward=[];}pageId=id;}
            groupPages=Object.assign({},groupPages,{[current.group]:id});
            highlight=key||"";targetBlock=block||"";
            search.clear();content.forceActiveFocus();
            Qt.callLater(()=>{scroll.contentY=0;revealTarget();if(!entrance.running){pageLoader.arrival=0;entrance.start();}});
            if(highlight)highlightEnd.restart();
        }
        function revealTarget() {
            if(!targetBlock||!pageLoader.item)return;
            const list=pageLoader.item.cards;
            for(let i=0;i<list.count;i++){
                const card=list.itemAt(i);
                if(card&&card.modelData.id===targetBlock){
                    const row=card.rows;
                    let y=card.y;
                    for(let j=0;j<row.count;j++)if(row.itemAt(j)?.modelData.key===highlight){y=row.itemAt(j).mapToItem(pageLoader.item,0,0).y-44;break;}
                    scroll.contentY=Math.max(0,Math.min(y,scroll.contentHeight-scroll.height));
                    break;
                }
            }
        }
        function act(name) {
            if(name==="locknow"){Session.lock(false);return;}
            if(name==="hello"){IslandState.settingsOpen=false;IslandState.closeMenu();Context.show("welcome","","",0);return;}
            if(name==="canvas"){IslandState.settingsOpen=false;CanvasState.show();return;}
            if(name==="searchReset"){
                for(const key of ["searchWidth","searchBarHeight","searchMaxHeight","searchRows","searchX","searchY","searchRadius","searchMotion","searchTravelDuration"])
                    Preferences.set(key,Preferences.defaults[key]);
                return;
            }
            IslandState.openMenu(name);
        }
        Timer {id:highlightEnd;interval:2400;onTriggered:root.highlight=""}
        Keys.onEscapePressed:{if(root.searching)search.clear();else IslandState.settingsOpen=false;}
        Shortcut {sequence:"Ctrl+F";onActivated:{search.forceActiveFocus();search.selectAll();}}
        RowLayout {
            anchors.fill:parent;spacing:0
            Rectangle {
                Layout.preferredWidth:224;Layout.fillHeight:true;color:Theme.withAlpha(Theme.text,.022)
                ColumnLayout {
                    anchors.fill:parent;anchors.margins:16;spacing:16
                    RowLayout {
                        Layout.fillWidth:true;spacing:10
                        ProfileAvatar {Layout.preferredWidth:36;Layout.preferredHeight:36;MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:root.navigate("lock","profile")}}
                        ColumnLayout {Layout.fillWidth:true;spacing:2
                            PanelText {text:"Settings";font.pixelSize:16;font.weight:Font.Medium}
                            PanelText {text:Quickshell.env("USER");font.pixelSize:11;color:Theme.subtext}
                        }
                    }
                    EntryField {
                        id:search;Layout.fillWidth:true;placeholderText:"Search settings";font.pixelSize:12
                        rightPadding:text?32:12
                        onTextChanged:resultList.currentIndex=0
                        Keys.onDownPressed:resultList.currentIndex=Math.min(root.results.length-1,resultList.currentIndex+1)
                        Keys.onUpPressed:resultList.currentIndex=Math.max(0,resultList.currentIndex-1)
                        onAccepted:{const r=root.results[resultList.currentIndex];if(r)root.navigate(r.page,r.block,r.key);}
                        IconButton {anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter;visible:!!search.text;implicitWidth:28;implicitHeight:28;icon:"close";size:12;label:"Clear search";onClicked:{search.clear();search.forceActiveFocus();}}
                    }
                    Flickable {
                        Layout.fillWidth:true;Layout.fillHeight:true;contentHeight:navigation.implicitHeight;clip:true;boundsBehavior:Flickable.StopAtBounds
                        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
                        ColumnLayout {
                            id:navigation;width:parent.width;spacing:10
                            Repeater {
                                model:Catalog.groups
                                ColumnLayout {
                                    id:group;required property var modelData
                                    Layout.fillWidth:true;spacing:4
                                    AbstractButton {
                                        id:groupButton;Layout.fillWidth:true;implicitHeight:34;hoverEnabled:true
                                        onClicked:root.navigate(root.groupPages[group.modelData.id]||Catalog.pages.find(p=>p.group===group.modelData.id).id)
                                        Accessible.name:group.modelData.title
                                        background:Rectangle {radius:9;color:groupButton.hovered?Theme.withAlpha(Theme.text,.04):"transparent";border.width:groupButton.activeFocus?1:0;border.color:Theme.accent}
                                        contentItem:RowLayout {spacing:9
                                            Icon {icon:group.modelData.icon;size:16;color:Theme.subtext}
                                            PanelText {Layout.fillWidth:true;text:group.modelData.title;font.pixelSize:12;font.weight:Font.Medium;color:Theme.subtext}
                                            Icon {icon:root.current.group===group.modelData.id?"expand_more":"chevron_right";size:12;color:Theme.subtext}
                                        }
                                    }
                                    Repeater {
                                        model:root.current.group===group.modelData.id?Catalog.pages.filter(p=>p.group===group.modelData.id):[]
                                        AbstractButton {
                                            id:nav;required property var modelData
                                            Layout.fillWidth:true;implicitHeight:35;leftPadding:24;rightPadding:9;hoverEnabled:true
                                            onClicked:root.navigate(modelData.id)
                                            Accessible.name:modelData.title
                                            background:Rectangle {radius:9;color:!root.searching&&root.pageId===nav.modelData.id?Theme.withAlpha(Theme.text,.09):nav.hovered?Theme.withAlpha(Theme.text,.045):"transparent";border.width:nav.activeFocus?1:0;border.color:Theme.accent;Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                                            contentItem:PanelText {text:nav.modelData.title;font.pixelSize:12;font.weight:root.pageId===nav.modelData.id?Font.DemiBold:Font.Normal;verticalAlignment:Text.AlignVCenter}
                                        }
                                    }
                                }
                            }
                        }
                    }
                    PanelText {Layout.fillWidth:true;visible:!!Preferences.saveError||!!ControlLayout.error;text:Preferences.saveError||ControlLayout.error;wrapMode:Text.Wrap;elide:Text.ElideNone;font.pixelSize:11;color:Theme.red}
                }
            }
            ColumnLayout {
                id:content;Layout.fillWidth:true;Layout.fillHeight:true;Layout.margins:24;spacing:18
                RowLayout {
                    Layout.fillWidth:true;spacing:10
                    IconButton {icon:"arrow_back";label:"Back";size:15;enabled:root.back.length>0;onClicked:{const id=root.back[root.back.length-1];root.back=root.back.slice(0,-1);root.forward=[root.pageId].concat(root.forward);root.navigate(id,"","",false);}}
                    PanelText {Layout.fillWidth:true;text:root.searching?"Search":root.current.title;font.pixelSize:23;font.weight:Font.DemiBold;font.letterSpacing:Tokens.titleTracking}
                    IconButton {icon:"arrow_forward";label:"Forward";size:15;enabled:root.forward.length>0;onClicked:{const id=root.forward[0];root.forward=root.forward.slice(1);root.back=root.back.concat([root.pageId]);root.navigate(id,"","",false);}}
                    IconButton {icon:"close";label:"Close settings";size:15;onClicked:IslandState.settingsOpen=false}
                }
                ListView {
                    id:resultList;visible:root.searching;Layout.fillWidth:true;Layout.fillHeight:true
                    model:root.results;clip:true;spacing:6;boundsBehavior:Flickable.StopAtBounds;keyNavigationEnabled:true
                    ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
                    delegate:AbstractButton {
                        id:result;required property var modelData;required property int index
                        width:resultList.width-8;height:68;hoverEnabled:true;leftPadding:16;rightPadding:16
                        onClicked:root.navigate(modelData.page,modelData.block,modelData.key)
                        Accessible.name:modelData.label+", "+modelData.path
                        background:Rectangle {radius:13;color:result.hovered?Theme.withAlpha(Theme.text,.065):Theme.surfaceSolid;border.width:resultList.currentIndex===result.index?1:0;border.color:Theme.withAlpha(Theme.accent,.65)}
                        contentItem:RowLayout {spacing:13
                            Icon {icon:result.modelData.icon;size:19;color:Theme.subtext}
                            ColumnLayout {Layout.fillWidth:true;spacing:4
                                PanelText {Layout.fillWidth:true;text:result.modelData.label;font.pixelSize:13;font.weight:Font.Medium}
                                PanelText {Layout.fillWidth:true;text:result.modelData.path;font.pixelSize:11;color:Theme.subtext}
                            }
                            Icon {icon:"chevron_right";size:14;color:Theme.subtext}
                        }
                    }
                    PanelText {anchors.centerIn:parent;visible:resultList.count===0;text:"No matching settings";font.pixelSize:14;color:Theme.subtext}
                }
                Flickable {
                    id:scroll;visible:!root.searching;Layout.fillWidth:true;Layout.fillHeight:true;clip:true
                    contentHeight:pageLoader.height;boundsBehavior:Flickable.StopAtBounds
                    ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
                    ViewportFade {view:scroll}
                    Loader {
                        id:pageLoader;width:scroll.width-10;active:window.visible&&!root.searching
                        property real arrival:1
                        transform:Translate {y:5*(1-pageLoader.arrival)}
                        NumberAnimation {id:entrance;target:pageLoader;property:"arrival";to:1;duration:Tokens.reducedMotion?0:180;easing.type:Easing.OutCubic}
                        onLoaded:Qt.callLater(root.revealTarget)
                        sourceComponent:ColumnLayout {
                            spacing:20
                            property alias cards:cards
                            Repeater {
                                id:cards;model:root.current.blocks
                                ColumnLayout {
                                    id:card;required property var modelData
                                    property alias rows:rows
                                    Layout.fillWidth:true;spacing:10
                                    PanelText {Layout.fillWidth:true;Layout.leftMargin:2;text:card.modelData.title;font.pixelSize:12;font.weight:Font.Medium;color:Theme.subtext}
                                    Rectangle {
                                        Layout.fillWidth:true;implicitHeight:body.implicitHeight+36;radius:Tokens.surfaceRadius;color:Theme.surfaceSolid
                                        border.width:1;border.color:Theme.withAlpha(Theme.text,Tokens.borderAlpha)
                                        gradient:Gradient {GradientStop {position:0;color:Qt.lighter(Theme.surfaceSolid,1.025)}GradientStop {position:1;color:Theme.surfaceSolid}}
                                        SurfaceLighting {anchors.fill:parent;radius:parent.radius}
                                        ColumnLayout {
                                            id:body;x:18;y:18;width:parent.width-36;spacing:14
                                            Repeater {
                                                id:rows;model:card.modelData.items
                                                ColumnLayout {
                                                    required property var modelData
                                                    required property int index
                                                    Layout.fillWidth:true;spacing:12
                                                    visible:!modelData.hideUnavailable||setting.available
                                                    Rectangle {Layout.fillWidth:true;height:1;color:Theme.withAlpha(Theme.text,.055);visible:parent.index>0}
                                                    SettingRow {id:setting;Layout.fillWidth:true;setting:parent.modelData;highlighted:root.highlight===parent.modelData.key;onAction:name=>root.act(name)}
                                                }
                                            }
                                            Loader {
                                                Layout.fillWidth:true;active:!!card.modelData.custom;visible:active
                                                sourceComponent:card.modelData.custom==="controls"?controlComponent:card.modelData.custom==="shortcuts"?shortcutsComponent:card.modelData.custom==="terminal"?terminalComponent:card.modelData.custom==="profile"?profileComponent:card.modelData.custom==="searchAi"?searchAiComponent:card.modelData.custom==="knowledge"?knowledgeComponent:null
                                            }
                                        }
                                    }
                                }
                            }
                            PanelText {Layout.fillWidth:true;visible:root.pageId==="appearance"&&!!Theme.syncError;text:Theme.syncError;font.pixelSize:12;color:Theme.red;wrapMode:Text.Wrap;elide:Text.ElideNone}
                            PanelText {Layout.fillWidth:true;visible:root.pageId==="lock";text:Session.authenticationVerified?"Password verified in this session.":"Verify your login password without locking the desktop.";font.pixelSize:12;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
                        }
                    }
                }
            }
        }
        Component {id:shortcutsComponent;ShortcutSettings {}}
        Component {id:searchAiComponent;SearchAiSettings {}}
        Component {id:knowledgeComponent;KnowledgeSettings {}}
        Component {id:controlComponent;Island.ControlEditor {}}
        Component {id:terminalComponent;TerminalArtSettings {Component.onCompleted:{if(root.artworkRequested){galleryOpen=true;root.artworkRequested=false;}}}}
        Component {id:profileComponent;RowLayout {spacing:16
            ProfileAvatar {Layout.preferredWidth:56;Layout.preferredHeight:56}
            ActionButton {text:"Choose image";onClicked:avatarPicker.open()}
            ActionButton {text:"Remove";onClicked:Preferences.set("profileImage","none")}
            Item {Layout.fillWidth:true}
        }}
        HintBubble {}
    }
}
