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
    QtObject {
        id:editorDrafts
        property bool hasNotes:false
        property string notes:""
        property string gemini:""
        property string jev:""
    }
    IpcHandler {
        objectName:"settings-ipc";target:"settings"
        function section(index:int):void {if(index>=0&&index<Catalog.legacy.length)root.navigate(Catalog.legacy[index]);}
        function page(name:string):void {root.navigate(name);}
        function find(query:string):void {search.text=query;search.forceActiveFocus();}
        function reveal(page:string,block:string,key:string):void {root.navigate(page,block,key);}
        function status():string {return JSON.stringify({page:root.pageId,query:search.text,results:root.results.map(r=>({label:r.label,page:r.page,block:r.block})),companionSide:Preferences.companionSide,companionInset:Preferences.companionInset});}
        function artwork():void {root.navigate("terminal","artwork","gallery");IslandState.settingsOpen=true;}
        function capture(path:string):void {if(Preferences.preview)root.grabToImage(result=>result.saveToFile(path));}
    }
    FileDialog {id:avatarPicker;title:"Choose profile picture";nameFilters:["Images (*.png *.jpg *.jpeg *.webp)"];onAccepted:Preferences.set("profileImage",String(selectedFile))}
    Item {
        id:root;objectName:"settings-root";anchors.fill:parent;focus:true
        Rectangle {anchors.fill:parent;color:Theme.bgSolid;z:-1}
        property string pageId:(Catalog.resolve(IslandState.settingsPage)||{page:"layout"}).page
        onPageIdChanged:if(IslandState.settingsPage!==pageId)Qt.callLater(()=>IslandState.settingsPage=pageId)
        property var back:[]
        property var forward:[]
        property var lastPages:({})
        readonly property int scrollGutter:18
        Component.onCompleted:rememberPage()
        function rememberPage() {lastPages=Object.assign({},lastPages,{[current.group]:pageId});}
        function navigateCategory(group) {
            const remembered=Catalog.page(lastPages[group]);
            navigate(remembered&&remembered.group===group?remembered.id:Catalog.pages.find(p=>p.group===group).id);
        }
        property var pendingTarget:null
        property string highlight:""
        readonly property var current:Catalog.page(pageId)
        readonly property var results:Catalog.search(search.text)
        readonly property bool searching:search.text.trim().length>0
        function navigate(id,block,key,history) {
            const target=Catalog.resolve(id,block,key);
            if(!target)return;
            pendingTarget=target;
            if(target.page!==pageId){if(history!==false){back=back.concat([pageId]).slice(-32);forward=[];}pageId=target.page;}
            rememberPage();
            highlight=target.key;
            search.clear();content.forceActiveFocus();
            Qt.callLater(()=>{scroll.contentY=0;revealTarget();pageLoader.enter();});
            if(highlight)highlightEnd.restart();
        }
        function keepVisible(item) {
            if(!item||!pageLoader.item||searching)return;
            let visibleItem=item,ancestor=item;
            while(ancestor&&ancestor!==pageLoader){if(ancestor.clip&&ancestor.height<visibleItem.height)visibleItem=ancestor;ancestor=ancestor.parent;}
            if(!ancestor)return;
            const y=visibleItem.mapToItem(pageLoader,0,0).y;
            const height=Math.min(visibleItem.height,scroll.height-16);
            const top=scroll.contentY+8,bottom=scroll.contentY+scroll.height-8;
            if(y<top||y+height>bottom)
                scroll.contentY=Math.max(0,Math.min(y<top?y-8:y+height-scroll.height+8,Math.max(0,scroll.contentHeight-scroll.height)));
        }
        readonly property var focusedItem:Window.window?Window.window.activeFocusItem:null
        onFocusedItemChanged:{focusScroll.target=focusedItem;focusScroll.restart();}
        Timer {id:focusScroll;interval:16;property var target:null;onTriggered:root.keepVisible(target)}
        function focusTarget(item) {
            if(!item)return;
            item.forceActiveFocus(Qt.OtherFocusReason);
            focusScroll.target=item;focusScroll.restart();
            pendingTarget=null;
        }
        function revealTarget() {
            const target=pendingTarget;
            if(!target||!pageLoader.item)return;
            if(!target.block){pendingTarget=null;return;}
            const list=pageLoader.item.cards;
            for(let i=0;i<list.count;i++){
                const card=list.itemAt(i);
                if(!card||card.modelData.id!==target.block)continue;
                if(card.modelData.custom){
                    if(card.editor.status!==Loader.Ready)return;
                    focusTarget(card.editor.item.reveal(target.key||card.modelData.targets[0]?.id));
                }else{
                    for(let j=0;j<card.rows.count;j++){
                        const row=card.rows.itemAt(j);
                        if(row&&(row.modelData.key===target.key||!target.key)){focusTarget(row.settingRow.reveal());return;}
                    }
                }
                return;
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
                Layout.preferredWidth:window.width<840?216:232;Layout.fillHeight:true;color:Theme.withAlpha(Theme.text,.022)
                ColumnLayout {
                    anchors.fill:parent;anchors.margins:16;spacing:16
                    RowLayout {
                        Layout.fillWidth:true;spacing:10
                        AbstractButton {objectName:"settings-profile";Layout.preferredWidth:36;Layout.preferredHeight:36;Accessible.name:"Profile picture";onClicked:root.navigate("lock","profile");background:Rectangle {radius:18;color:"transparent";border.width:parent.activeFocus?1:0;border.color:Theme.accent}contentItem:ProfileAvatar {}}
                        ColumnLayout {Layout.fillWidth:true;spacing:2
                            PanelText {text:"Settings";font.pixelSize:16;font.weight:Font.Medium}
                            PanelText {text:Quickshell.env("USER");font.pixelSize:11;color:Theme.subtext}
                        }
                    }
                    EntryField {
                        id:search;objectName:"settings-search";Layout.fillWidth:true;placeholderText:"Search settings";font.pixelSize:12
                        rightPadding:text?32:12
                        onTextChanged:{resultList.currentIndex=0;resultList.positionViewAtBeginning();}
                        Keys.onDownPressed:resultList.currentIndex=Math.max(0,Math.min(root.results.length-1,resultList.currentIndex+1))
                        Keys.onUpPressed:resultList.currentIndex=Math.max(0,resultList.currentIndex-1)
                        onAccepted:{const r=root.results[resultList.currentIndex];if(r)root.navigate(r.page,r.block,r.key);}
                        IconButton {anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter;visible:!!search.text;implicitWidth:28;implicitHeight:28;icon:"close";size:12;label:"Clear search";onClicked:{search.clear();search.forceActiveFocus();}}
                    }
                    Flickable {
                        objectName:"settings-navigation";Layout.fillWidth:true;Layout.fillHeight:true;contentHeight:navigation.implicitHeight;clip:true;boundsBehavior:Flickable.StopAtBounds
                        ScrollBar.vertical:SettingsScrollBar {}
                        ColumnLayout {
                            id:navigation;objectName:"settings-navigation-content";width:parent.width-root.scrollGutter;spacing:6
                            Repeater {
                                model:Catalog.groups
                                AbstractButton {
                                    id:category;required property var modelData
                                    objectName:"category-"+modelData.id
                                    Layout.fillWidth:true;implicitHeight:42;leftPadding:12;rightPadding:12;hoverEnabled:true
                                    onClicked:root.navigateCategory(modelData.id)
                                    Accessible.name:modelData.title
                                    Accessible.role:Accessible.PageTab
                                    Accessible.selected:root.current.group===modelData.id
                                    background:Rectangle {radius:9;color:root.current.group===category.modelData.id?Theme.accentLow:category.pressed?Theme.withAlpha(Theme.text,.09):category.hovered?Theme.withAlpha(Theme.text,.045):"transparent";border.width:category.activeFocus?1:0;border.color:Theme.accent}
                                    contentItem:RowLayout {spacing:10
                                        Icon {icon:category.modelData.icon;size:18;color:root.current.group===category.modelData.id?Theme.accent:Theme.subtext}
                                        PanelText {Layout.fillWidth:true;text:category.modelData.title;font.pixelSize:13;font.weight:Font.Medium}
                                    }
                                }
                            }
                        }
                    }
                    PanelText {objectName:"preferences-save-error";Layout.fillWidth:true;visible:!!Preferences.saveError||!!ControlLayout.error;text:Preferences.saveError||ControlLayout.error;wrapMode:Text.Wrap;elide:Text.ElideNone;font.pixelSize:11;color:Theme.red}
                }
            }
            ColumnLayout {
                id:content;Layout.fillWidth:true;Layout.fillHeight:true;Layout.margins:24;spacing:16
                RowLayout {
                    Layout.fillWidth:true;spacing:8
                    ColumnLayout {
                        Layout.fillWidth:true;spacing:5
                        PanelText {Layout.fillWidth:true;text:root.searching?"Settings":Catalog.groups.find(g=>g.id===root.current.group).title;font.pixelSize:12;color:Theme.subtext}
                        PanelText {objectName:"settings-page-title";Layout.fillWidth:true;text:root.searching?"Search results":root.current.title;font.pixelSize:22;font.weight:Font.DemiBold;font.letterSpacing:Tokens.titleTracking}
                    }
                    IconButton {objectName:"settings-back";implicitWidth:36;implicitHeight:36;icon:"arrow_back";label:"Back";size:16;enabled:root.back.length>0;onClicked:{const id=root.back[root.back.length-1];root.back=root.back.slice(0,-1);root.forward=[root.pageId].concat(root.forward);root.navigate(id,"","",false);}}
                    IconButton {objectName:"settings-forward";implicitWidth:36;implicitHeight:36;icon:"arrow_forward";label:"Forward";size:16;enabled:root.forward.length>0;onClicked:{const id=root.forward[0];root.forward=root.forward.slice(1);root.back=root.back.concat([root.pageId]);root.navigate(id,"","",false);}}
                    IconButton {objectName:"settings-close";implicitWidth:36;implicitHeight:36;icon:"close";label:"Close settings";size:16;onClicked:IslandState.settingsOpen=false}
                }
                Flow {
                    objectName:"settings-page-tabs";Layout.fillWidth:true;visible:!root.searching;spacing:6
                    Repeater {
                        model:Catalog.pages.filter(p=>p.group===root.current.group)
                        ActionButton {
                            id:pageTab;required property var modelData
                            objectName:"page-"+modelData.id
                            text:modelData.title;implicitHeight:36;onClicked:root.navigate(modelData.id)
                            Accessible.role:Accessible.PageTab;Accessible.selected:root.pageId===modelData.id
                            contentItem:PanelText {text:pageTab.text;font.pixelSize:12;font.weight:root.pageId===pageTab.modelData.id?Font.DemiBold:Font.Normal;color:root.pageId===pageTab.modelData.id?Theme.text:Theme.subtext;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
                            background:Rectangle {radius:8;color:root.pageId===pageTab.modelData.id?Theme.accentLow:pageTab.pressed?Theme.withAlpha(Theme.text,.09):pageTab.hovered?Theme.withAlpha(Theme.text,.045):"transparent";border.width:pageTab.activeFocus?1:0;border.color:Theme.accent}
                        }
                    }
                }
                ListView {
                    id:resultList;objectName:"settings-results";visible:root.searching;Layout.fillWidth:true;Layout.fillHeight:true
                    model:root.results;clip:true;spacing:6;boundsBehavior:Flickable.StopAtBounds;keyNavigationEnabled:true
                    ScrollBar.vertical:SettingsScrollBar {}
                    delegate:AbstractButton {
                        id:result;required property var modelData;required property int index
                        objectName:"settings-result-"+index;width:resultList.width-root.scrollGutter;height:Math.max(72,resultBody.implicitHeight+24);hoverEnabled:true;leftPadding:16;rightPadding:16
                        onClicked:root.navigate(modelData.page,modelData.block,modelData.key)
                        Accessible.name:modelData.label+", "+modelData.path
                        background:Rectangle {radius:13;color:result.hovered?Theme.withAlpha(Theme.text,.065):Theme.surfaceSolid;border.width:resultList.currentIndex===result.index?1:0;border.color:Theme.withAlpha(Theme.accent,.65)}
                        contentItem:RowLayout {id:resultBody;spacing:13
                            Icon {icon:result.modelData.icon;size:19;color:Theme.subtext}
                            ColumnLayout {Layout.fillWidth:true;spacing:4
                                PanelText {Layout.fillWidth:true;text:result.modelData.label;font.pixelSize:13;font.weight:Font.Medium;wrapMode:Text.Wrap;elide:Text.ElideNone}
                                PanelText {Layout.fillWidth:true;text:result.modelData.path;font.pixelSize:12;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
                            }
                            Icon {icon:"chevron_right";size:14;color:Theme.subtext}
                        }
                    }
                    PanelText {anchors.centerIn:parent;visible:resultList.count===0;text:"No matching settings";font.pixelSize:14;color:Theme.subtext}
                }
                Flickable {
                    id:scroll;objectName:"settings-scroll";visible:!root.searching;Layout.fillWidth:true;Layout.fillHeight:true;clip:true
                    contentHeight:pageLoader.height+8;boundsBehavior:Flickable.StopAtBounds
                    ScrollBar.vertical:SettingsScrollBar {}
                    Loader {
                        id:pageLoader;objectName:"settings-page-content";width:scroll.width-root.scrollGutter;active:window.visible&&!root.searching
                        property real arrival:1
                        transform:Translate {y:14*(1-pageLoader.arrival)}
                        function enter():void {entrance.stop();arrival=Tokens.reducedMotion?1:0;if(!Tokens.reducedMotion)entrance.start();}
                        SpringMotion {id:entrance;target:pageLoader;property:"arrival";to:1;epsilon:.002}
                        Connections {target:Tokens;function onReducedMotionChanged(){if(Tokens.reducedMotion){entrance.stop();pageLoader.arrival=1;}}}
                        onLoaded:Qt.callLater(()=>{root.revealTarget();enter();})
                        sourceComponent:ColumnLayout {
                            spacing:20
                            property alias cards:cards
                            Repeater {
                                id:cards;model:root.current.blocks
                                ColumnLayout {
                                    id:card;required property var modelData
                                    property alias rows:rows
                                    property alias editor:editor
                                    Layout.fillWidth:true;spacing:10
                                    PanelText {Layout.fillWidth:true;Layout.leftMargin:2;text:card.modelData.title;font.pixelSize:13;font.weight:Font.DemiBold;color:Theme.subtext}
                                    Rectangle {
                                        Layout.fillWidth:true;implicitHeight:body.implicitHeight+28;radius:12;color:Theme.surfaceSolid
                                        border.width:1;border.color:Theme.withAlpha(Theme.text,Tokens.borderAlpha)
                                        ColumnLayout {
                                            id:body;x:16;y:14;width:parent.width-32;spacing:12
                                            Repeater {
                                                id:rows;model:card.modelData.items
                                                ColumnLayout {
                                                    required property var modelData
                                                    required property int index
                                                    Layout.fillWidth:true;spacing:12
                                                    property alias settingRow:setting
                                                    Rectangle {Layout.fillWidth:true;height:1;color:Theme.withAlpha(Theme.text,.055);visible:parent.index>0}
                                                    SettingRow {id:setting;Layout.fillWidth:true;setting:parent.modelData;highlighted:root.highlight===parent.modelData.key;onAction:name=>root.act(name);onPrerequisite:target=>root.navigate(target.page,target.block,target.key)}
                                                }
                                            }
                                            Loader {
                                                id:editor
                                                onLoaded:Qt.callLater(root.revealTarget)
                                                Connections {
                                                    target:editor.item;ignoreUnknownSignals:true
                                                    function onTargetRequested(key){root.navigate(root.pageId,card.modelData.id,key);}
                                                }
                                                Layout.fillWidth:true;active:!!card.modelData.custom;visible:active
                                                sourceComponent:card.modelData.custom==="updates"?updatesComponent:card.modelData.custom==="controls"?controlComponent:card.modelData.custom==="shortcuts"?shortcutsComponent:card.modelData.custom==="terminalEffects"?terminalEffectsComponent:card.modelData.custom==="terminal"?terminalComponent:card.modelData.custom==="profile"?profileComponent:card.modelData.custom==="searchAi"?searchAiComponent:card.modelData.custom==="knowledge"?knowledgeComponent:card.modelData.custom==="voice"?voiceComponent:null
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
        Component {id:searchAiComponent;SearchAiSettings {drafts:editorDrafts}}
        Component {id:knowledgeComponent;KnowledgeSettings {}}
        Component {id:voiceComponent;VoiceSettings {}}
        Component {id:updatesComponent;UpdateSettings {}}
        Component {id:controlComponent;Island.ControlEditor {}}
        Component {id:terminalEffectsComponent;TerminalEffectsSettings {}}
        Component {id:terminalComponent;TerminalArtSettings {}}
        Component {id:profileComponent;RowLayout {spacing:16
            function reveal(key){return key==="remove-image"?removeImage:chooseImage;}
            ProfileAvatar {Layout.preferredWidth:56;Layout.preferredHeight:56}
            ActionButton {id:chooseImage;objectName:"custom-choose-image";text:"Choose image";onClicked:avatarPicker.open()}
            ActionButton {id:removeImage;objectName:"custom-remove-image";text:"Remove";onClicked:Preferences.set("profileImage","none")}
            Item {Layout.fillWidth:true}
        }}
        HintBubble {}
    }
}
