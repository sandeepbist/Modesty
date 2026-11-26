import QtQuick
import QtQuick.Dialogs
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Widgets
import qs.services
import qs.components
import qs.theme
import "../island" as Island
import "../lock" as Lock
import "SettingsCatalog.js" as Catalog

FloatingWindow {
    id:window
    title:"Modesty Settings"
    implicitWidth:920;implicitHeight:680
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
        readonly property alias lockPreviewPopup: lockPreview
        Rectangle {anchors.fill:parent;color:Theme.bgSolid;z:-1}
        property string pageId:(Catalog.resolve(IslandState.settingsPage)||{page:"layout"}).page
        onPageIdChanged:if(IslandState.settingsPage!==pageId)Qt.callLater(()=>IslandState.settingsPage=pageId)
        property var back:[]
        property var forward:[]
        readonly property int scrollGutter:18
        function keepPageVisible(item) {
            const top = item.mapToItem(navigation, 0, 0).y;
            const bottom = top + item.height;
            if (top < navigationView.contentY) navigationView.contentY = top;
            else if (bottom > navigationView.contentY + navigationView.height)
                navigationView.contentY = Math.min(bottom - navigationView.height, Math.max(0, navigationView.contentHeight - navigationView.height));
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
            const changingPage = target.page !== pageId;
            const wasSearching = searching;
            if(changingPage){if(history!==false){back=back.concat([pageId]).slice(-32);forward=[];}pageId=target.page;}
            highlight=target.key;
            search.clear();content.forceActiveFocus();
            Qt.callLater(()=>{
                scroll.contentY=0;
                if(changingPage&&!wasSearching)pageLoader.enter();
                revealTarget();
            });
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
            if(name==="lockpreview"){lockPreview.open();return;}
            if(name==="hello"){IslandState.settingsOpen=false;IslandState.closeMenu();Context.show("welcome","","",0);return;}
            if(name==="canvas"){IslandState.settingsOpen=false;CanvasState.show();return;}
            if(name==="searchReset"){
                for(const key of ["searchWidth","searchBarHeight","searchMaxHeight","searchRows","searchX","searchY","searchRadius","searchMotion","searchTravelDuration"])
                    Preferences.set(key,Preferences.defaults[key]);
                return;
            }
            IslandState.openMenu(name);
        }
        Popup {
            id: lockPreview
            objectName: "settings-lock-preview"
            parent: Overlay.overlay
            anchors.centerIn: parent
            width: Math.min(720, parent ? parent.width - 32 : 720)
            padding: 16
            modal: true
            focus: true
            closePolicy: Popup.CloseOnEscape
            function replay(): void {
                lockScene.active = false;
                lockScene.active = true;
            }
            onOpened: { replay(); replayButton.forceActiveFocus(); }
            onClosed: lockScene.active = false
            background: Rectangle {
                radius: Tokens.surfaceRadius
                color: Theme.surfaceSolid
                border.width: 1
                border.color: Theme.withAlpha(Theme.text, Tokens.borderAlpha)
            }
            contentItem: ColumnLayout {
                spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    PanelText {
                        Layout.fillWidth: true
                        text: "Lock screen preview"
                        font.pixelSize: Tokens.textSize(16)
                        font.weight: Font.DemiBold
                    }
                    ActionButton {
                        id: replayButton
                        objectName: "settings-replay-lock"
                        text: "Replay"
                        Keys.onReturnPressed: clicked()
                        Keys.onEnterPressed: clicked()
                        onClicked: lockPreview.replay()
                    }
                    IconButton { icon: "close"; label: "Close preview"; implicitWidth: 36; implicitHeight: 36; onClicked: lockPreview.close() }
                }
                ClippingRectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: width * 9 / 16
                    radius: Tokens.surfaceRadius
                    color: Theme.bgSolid
                    Loader {
                        id: lockScene
                        anchors.fill: parent
                        active: false
                        enabled: false
                        sourceComponent: Lock.LockContent { objectName: "settings-lock-scene"; preview: true }
                    }
                }
            }
            Timer {
                interval: 550
                running: lockPreview.opened && lockScene.item?.arrival === 1 && !lockScene.item?.previewDeparting
                onTriggered: lockScene.item.previewDeparting = true
            }
        }
        Timer {id:highlightEnd;interval:2400;onTriggered:root.highlight=""}
        Keys.onEscapePressed:{if(root.searching)search.clear();else IslandState.settingsOpen=false;}
        Shortcut {sequence:"Ctrl+F";onActivated:{search.forceActiveFocus();search.selectAll();}}
        RowLayout {
            anchors.fill:parent;spacing:0
            Rectangle {
                Layout.preferredWidth:window.width<840?208:224;Layout.fillHeight:true;color:Theme.withAlpha(Theme.text,.018)
                Rectangle {anchors.right:parent.right;width:1;height:parent.height;color:Theme.withAlpha(Theme.text,.055)}
                ColumnLayout {
                    anchors.fill:parent;anchors.margins:12;spacing:10
                    EntryField {
                        id:search;objectName:"settings-search";Layout.fillWidth:true;placeholderText:"Search settings";font.pixelSize:Tokens.textSize(13)
                        leftPadding:34;rightPadding:text?32:12
                        Icon {x:11;anchors.verticalCenter:parent.verticalCenter;icon:"search";size:15;color:Theme.subtext}
                        onTextChanged:{resultList.currentIndex=0;resultList.positionViewAtBeginning();}
                        Keys.onDownPressed:resultList.currentIndex=Math.max(0,Math.min(root.results.length-1,resultList.currentIndex+1))
                        Keys.onUpPressed:resultList.currentIndex=Math.max(0,resultList.currentIndex-1)
                        onAccepted:{const r=root.results[resultList.currentIndex];if(r)root.navigate(r.page,r.block,r.key);}
                        IconButton {anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter;visible:!!search.text;implicitWidth:28;implicitHeight:28;icon:"close";size:12;label:"Clear search";onClicked:{search.clear();search.forceActiveFocus();}}
                    }
                    Flickable {
                        id:navigationView;objectName:"settings-navigation";Layout.fillWidth:true;Layout.fillHeight:true;contentHeight:navigation.implicitHeight;clip:true;boundsBehavior:Flickable.StopAtBounds
                        ScrollBar.vertical:SettingsScrollBar {}
                        ColumnLayout {
                            id:navigation;objectName:"settings-navigation-content";width:navigationView.width-root.scrollGutter;spacing:14
                            Repeater {
                                model:Catalog.groups
                                ColumnLayout {
                                    id:category
                                    required property var modelData
                                    Layout.fillWidth:true;spacing:2
                                    PanelText {
                                        Layout.fillWidth:true;Layout.leftMargin:8;Layout.bottomMargin:3
                                        text:category.modelData.title;font.pixelSize:Tokens.textSize(11);font.weight:Font.Medium;color:Theme.subtext
                                    }
                                    Repeater {
                                        model:Catalog.pages.filter(p=>p.group===category.modelData.id)
                                        AbstractButton {
                                            id:pageButton
                                            required property var modelData
                                            readonly property bool selected:root.pageId===modelData.id
                                            objectName:"page-"+modelData.id
                                            Layout.fillWidth:true
                                            implicitHeight:Math.max(37,contentItem.implicitHeight+8)
                                            leftPadding:7;rightPadding:8;topPadding:4;bottomPadding:4
                                            hoverEnabled:true;focusPolicy:Qt.StrongFocus
                                            Accessible.name:modelData.title
                                            Accessible.role:Accessible.PageTab
                                            Accessible.selected:selected
                                            onClicked:root.navigate(modelData.id)
                                            onActiveFocusChanged:if(activeFocus)root.keepPageVisible(pageButton)
                                            onSelectedChanged:if(selected)Qt.callLater(root.keepPageVisible,pageButton)
                                            Component.onCompleted:if(selected)Qt.callLater(root.keepPageVisible,pageButton)
                                            background:Rectangle {
                                                radius:Tokens.fieldRadius
                                                color:pageButton.selected?Theme.accentLow:Theme.withAlpha(Theme.text,pageButton.pressed?.09:pageButton.hovered?.05:0)
                                                border.width:pageButton.activeFocus?1:0;border.color:Theme.accent
                                                Behavior on color { ColorAnimation {duration:Tokens.animFast} }
                                            }
                                            contentItem:RowLayout {
                                                spacing:8
                                                Rectangle {
                                                    Layout.preferredWidth:26;Layout.preferredHeight:26;radius:13
                                                    color:pageButton.selected?Theme.accent:Theme.withAlpha(Theme.accent,.13)
                                                    Behavior on color { ColorAnimation {duration:Tokens.animFast} }
                                                    Icon {anchors.centerIn:parent;icon:pageButton.modelData.icon;size:14;color:pageButton.selected?Theme.accentText:Theme.accent}
                                                }
                                                PanelText {
                                                    Layout.fillWidth:true;text:pageButton.modelData.title;font.pixelSize:Tokens.textSize(13)
                                                    font.weight:pageButton.selected?Font.DemiBold:Font.Normal
                                                    wrapMode:Text.Wrap;elide:Text.ElideNone
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    ActionButton {
                        objectName:"settings-profile"
                        Layout.fillWidth:true;implicitHeight:38
                        text:"Profile";Accessible.name:"Profile picture"
                        onClicked:root.navigate("lock","profile")
                        contentItem:RowLayout {
                            spacing:8
                            ProfileAvatar {Layout.preferredWidth:24;Layout.preferredHeight:24}
                            PanelText {Layout.fillWidth:true;text:"Profile";font.pixelSize:Tokens.textSize(12)}
                        }
                    }
                    PanelText {objectName:"preferences-save-error";Layout.fillWidth:true;visible:!!Preferences.saveError||!!ControlLayout.error;text:Preferences.saveError||ControlLayout.error;wrapMode:Text.Wrap;elide:Text.ElideNone;font.pixelSize:Tokens.textSize(11);color:Theme.red}
                }
            }
            ColumnLayout {
                id:content;Layout.fillWidth:true;Layout.fillHeight:true;Layout.margins:20;spacing:12
                RowLayout {
                    Layout.fillWidth:true;spacing:5
                    IconButton {objectName:"settings-back";implicitWidth:32;implicitHeight:32;icon:"arrow_back";label:"Back";size:15;enabled:root.back.length>0;onClicked:{const id=root.back[root.back.length-1];root.back=root.back.slice(0,-1);root.forward=[root.pageId].concat(root.forward);root.navigate(id,"","",false);}}
                    IconButton {objectName:"settings-forward";implicitWidth:32;implicitHeight:32;icon:"arrow_forward";label:"Forward";size:15;enabled:root.forward.length>0;onClicked:{const id=root.forward[0];root.forward=root.forward.slice(1);root.back=root.back.concat([root.pageId]);root.navigate(id,"","",false);}}
                    PanelText {
                        objectName:"settings-page-title";Layout.fillWidth:true;Layout.leftMargin:8
                        text:root.searching?"Search results":root.current.title
                        font.family:Tokens.clockFont;font.pixelSize:Tokens.textSize(19);font.weight:Font.DemiBold;font.letterSpacing:Tokens.titleTracking
                    }
                    IconButton {objectName:"settings-close";implicitWidth:32;implicitHeight:32;icon:"close";label:"Close settings";size:15;onClicked:IslandState.settingsOpen=false}
                }
                Rectangle {Layout.fillWidth:true;Layout.preferredHeight:1;color:Theme.withAlpha(Theme.text,.07)}
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
                                PanelText {Layout.fillWidth:true;text:result.modelData.label;font.pixelSize:Tokens.textSize(13);font.weight:Font.Medium;wrapMode:Text.Wrap;elide:Text.ElideNone}
                                PanelText {Layout.fillWidth:true;text:result.modelData.path;font.pixelSize:Tokens.textSize(12);color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
                            }
                            Icon {icon:"chevron_right";size:14;color:Theme.subtext}
                        }
                    }
                    PanelText {anchors.centerIn:parent;visible:resultList.count===0;text:"No matching settings";font.pixelSize:Tokens.textSize(14);color:Theme.subtext}
                }
                Flickable {
                    id:scroll;objectName:"settings-scroll";visible:!root.searching;Layout.fillWidth:true;Layout.fillHeight:true;clip:true
                    contentHeight:pageLoader.height+8;boundsBehavior:Flickable.StopAtBounds
                    ScrollBar.vertical:SettingsScrollBar {}
                    Loader {
                        id:pageLoader;objectName:"settings-page-content";width:scroll.width-root.scrollGutter;active:window.visible&&!root.searching
                        property real arrival:entrance.value
                        transform:Translate {y:9*(1-pageLoader.arrival)}
                        opacity:.8+.2*Math.max(0,Math.min(1,arrival))
                        function enter():void {entrance.reset(Tokens.reducedMotion?1:0);if(!Tokens.reducedMotion)entrance.start();}
                        FrameSpring {
                            id:entrance;owner:pageLoader;targetValue:1;positionTolerance:.002;enabled:entrance.available&&pageLoader.active
                            frequency:Tokens.panelSpringFrequency;dampingRatio:Tokens.panelSpringDamping
                        }
                        onLoaded:Qt.callLater(()=>{root.revealTarget();enter();})
                        sourceComponent:ColumnLayout {
                            spacing:4*Tokens.spacingUnit
                            property alias cards:cards
                            Repeater {
                                id:cards;model:root.current.blocks
                                ColumnLayout {
                                    id:card;required property var modelData
                                    property alias rows:rows
                                    property alias editor:editor
                                    Layout.fillWidth:true;spacing:8
                                    PanelText {Layout.fillWidth:true;Layout.leftMargin:2;text:card.modelData.title;font.pixelSize:Tokens.textSize(13);font.weight:Font.DemiBold;color:Theme.subtext}
                                    Rectangle {
                                        Layout.fillWidth:true;implicitHeight:body.implicitHeight+24;radius:Tokens.surfaceRadius;color:Theme.surfaceSolid
                                        border.width:1;border.color:Theme.withAlpha(Theme.text,Tokens.borderAlpha)
                                        ColumnLayout {
                                            id:body;x:16;y:12;width:parent.width-32;spacing:2*Tokens.spacingUnit
                                            Repeater {
                                                id:rows;model:card.modelData.items
                                                ColumnLayout {
                                                    required property var modelData
                                                    required property int index
                                                    Layout.fillWidth:true;spacing:7
                                                    property alias settingRow:setting
                                                    visible: root.pageId !== "lock" || setting.available || setting.highlighted || setting.prerequisiteFocused
                                                    Rectangle {Layout.fillWidth:true;height:1;color:Theme.withAlpha(Theme.text,.055);visible:parent.index>0&&root.pageId!=="lock"}
                                                    SettingRow {id:setting;Layout.fillWidth:true;setting:parent.modelData;highlighted:root.highlight===parent.modelData.key;onAction:name=>root.act(name);onPrerequisite:target=>root.navigate(target.page,target.block,target.key)}
                                                }
                                            }
                                            PanelText {
                                                Layout.fillWidth:true
                                                visible:card.modelData.id==="type"&&Tokens.missingFonts.length>0
                                                text:Tokens.missingFonts.join(", ")+" unavailable. Using bundled Inter."
                                                wrapMode:Text.Wrap
                                                color:Theme.subtext
                                            }
                                            Loader {
                                                id:editor
                                                onLoaded:Qt.callLater(root.revealTarget)
                                                Connections {
                                                    target:editor.item;ignoreUnknownSignals:true
                                                    function onTargetRequested(key){root.navigate(root.pageId,card.modelData.id,key);}
                                                }
                                                Layout.fillWidth:true;active:!!card.modelData.custom;visible:active
                                                sourceComponent:card.modelData.custom==="capture"?captureComponent:card.modelData.custom==="updates"?updatesComponent:card.modelData.custom==="controls"?controlComponent:card.modelData.custom==="shortcuts"?shortcutsComponent:card.modelData.custom==="terminalEffects"?terminalEffectsComponent:card.modelData.custom==="terminal"?terminalComponent:card.modelData.custom==="profile"?profileComponent:card.modelData.custom==="searchAi"?searchAiComponent:card.modelData.custom==="knowledge"?knowledgeComponent:card.modelData.custom==="voice"?voiceComponent:card.modelData.custom==="themes"?themesComponent:null
                                            }
                                        }
                                    }
                                }
                            }
                            PanelText {Layout.fillWidth:true;visible:["appearance","themes"].includes(root.pageId)&&!!Theme.syncError;text:Theme.syncError;font.pixelSize:Tokens.textSize(12);color:Theme.red;wrapMode:Text.Wrap;elide:Text.ElideNone}
                            PanelText {Layout.fillWidth:true;visible:root.pageId==="lock";text:Session.authenticationVerified?"Password verified in this session.":"Verify your login password without locking the desktop.";font.pixelSize:Tokens.textSize(12);color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
                        }
                    }
                }
            }
        }
        Component {id:shortcutsComponent;ShortcutSettings {}}
        Component {id:searchAiComponent;SearchAiSettings {drafts:editorDrafts}}
        Component {id:knowledgeComponent;KnowledgeSettings {}}
        Component {id:voiceComponent;VoiceSettings {}}
        Component {id:themesComponent;ThemeSettings {}}
        Component {id:captureComponent;CaptureSettings {}}
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
