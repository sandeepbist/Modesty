import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.services
import qs.components
import qs.theme
import "../../services/ModelDiff.js" as ModelDiff

Item {
    id: root
    signal focusInput()
    signal webRequested(string query)
    signal followupRequested(string query)
    property int turnRevision: 0
    readonly property real settledHeight: {
        const revision=turnRevision;
        const heights=[];
        for(let i=0;i<turnRepeater.count;i++){
            const item=turnRepeater.itemAt(i);
            if(item)heights.push(item.naturalHeight);
        }
        for(const section of [sourceSection,fileSection,metricsSection,executionSection,proposalSection,nextSection,pendingSection,errorSection])
            if(section.expanded&&section.naturalHeight>0)heights.push(section.naturalHeight);
        return heights.reduce((sum,height)=>sum+height,0)+Math.max(0,heights.length-1)*flow.spacing;
    }
    readonly property real preferredHeight: pickerOpen ? 340 : historyOpen ? Math.min(360,Math.max(160,Luma.conversations.length*54+64)) : Math.min(400, Math.max(76, settledHeight+32+(attachmentSection.expanded?attachmentSection.naturalHeight+8:0)+24))
    readonly property bool working: Luma.busy && !Luma.received && ["routing","reading","acting","composing"].includes(Luma.phase)
    property bool initialized: false
    property bool historyOpen: false
    property bool pickerOpen: false
    property real pickerAmount: pickerOpen ? 1 : 0
    property url lastFolder: ""
    Behavior on pickerAmount {NumberAnimation {duration:Tokens.reducedMotion?0:Tokens.animMedium;easing.type:Easing.InOutCubic}}
    function openAttachments():void {if(!Luma.busy&&Luma.attachments.length<3){historyOpen=false;pickerOpen=true;}}
    function closeAttachments():void {pickerOpen=false;focusInput();}
    property string deleteArmed: ""
    property bool following: true
    property real followPosition: 0
    property string followKey: ""
    property string pendingStatus: "Understanding"
    property string displayedError: ""
    property var displayedCitations: []
    property var displayedFiles: []
    property var displayedFollowups:[]
    readonly property var lastTurn:Luma.messages.filter(m=>!m.hidden).slice(-1)[0]
    readonly property var followups:lastTurn?.role==="assistant"?lastTurn.presentation?.followups??[]:[]
    onFollowupsChanged:{if(followups.length)displayedFollowups=followups;retire.restart();}
    ListModel {id:attachments}
    ListModel {id:conversationRows}
    function syncConversations():void {ModelDiff.reconcile(conversationRows,Luma.conversations.slice().reverse().map(t=>({key:t.id,title:t.title,updatedAt:t.updatedAt})),"key");}
    function syncAttachments(): void {
        if(Luma.attachments.length)ModelDiff.reconcile(attachments,Luma.attachments.map(path=>({path,name:path.split("/").pop()})),"path");
        else retire.restart();
    }
    readonly property real scrollTarget: {
        const bottom=Math.max(0,transcript.contentHeight-transcript.height);
        const latest=turnRepeater.itemAt(turnRepeater.count-1);
        if(Luma.liveMetrics&&Luma.messages.slice(-1)[0]?.hidden)
            return Math.max(0,Math.min(bottom,metricsSection.y));
        return followKey&&latest&&latest.model.key===followKey ? Math.max(0,Math.min(bottom,latest.y-4)) : bottom;
    }
    function stopFollowing(): void {following=false;followScroll.stop();followPosition=transcript.contentY;}
    function followTarget(): void {
        if(!following||!visible||transcript.dragging||transcript.flicking)return;
        if(Tokens.reducedMotion)transcript.contentY=scrollTarget;
        else {
            followPosition=scrollTarget;
            if(!followScroll.running)transcript.contentY=scrollTarget;
        }
    }
    onScrollTargetChanged:Qt.callLater(followTarget)
    onFollowPositionChanged:if(following)transcript.contentY=Math.max(0,Math.min(Math.max(0,transcript.contentHeight-transcript.height),followPosition))
    Behavior on followPosition {
        enabled:root.visible&&root.following&&!Tokens.reducedMotion
        SmoothedAnimation {id:followScroll;velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}
    }
    function scroll(amount: real): void {
        if(historyOpen){history.currentIndex=Math.max(0,Math.min(history.count-1,history.currentIndex+(amount>0?1:-1)));history.positionViewAtIndex(history.currentIndex,ListView.Contain);return;}
        stopFollowing();
        manualScroll.to=Math.max(0,Math.min(Math.max(0,transcript.contentHeight-transcript.height),transcript.contentY+amount));
        manualScroll.restart();
    }
    function openSelectedConversation():void {if(history.currentIndex>=0&&history.currentIndex<conversationRows.count){Luma.selectConversation(conversationRows.get(history.currentIndex).key);historyOpen=false;focusInput();}}
    function sync(): void {
        const keys=new Set(Array.from({length:turns.count},(_,i)=>turns.get(i).key));
        const next=Luma.messages.filter((m,i)=>!m.hidden&&!(m.failed&&m.text===Luma.error&&i===Luma.messages.length-1)).map((m,i)=>{
            const key=m.id||String(i)+m.role+m.text.slice(0,80);
            return {key,role:m.role,text:m.text,presentation:JSON.stringify(m.presentation||{}),citations:JSON.stringify(m.citations||[]),execution:JSON.stringify(m.execution||[]),fresh:initialized&&visible&&!Tokens.reducedMotion&&!keys.has(key)};
        });
        const last=next[next.length-1];
        const isNew=last&&(!turns.count||turns.get(turns.count-1).key!==last.key);
        if(isNew&&last.role==="user"){if(!following)followPosition=transcript.contentY;following=true;followKey="";manualScroll.stop();}
        else if(isNew&&following)followKey=last.key;
        ModelDiff.reconcile(turns,next,"key");
        initialized=true;
        if(!turns.count){following=true;followKey="";transcript.contentY=0;}
    }
    function syncProposals(): void {
        if(Luma.proposals.length)ModelDiff.reconcile(proposals,Luma.proposals.map((p,i)=>({key:String(i)+p.name,label:p.label,name:p.name,detail:p.args?.detail||"",amount:p.args?.minutes??p.args?.level??0,status:p.status,deadline:p.expectedUntil||0,position:i})),"key");
        else retire.restart();
    }
    function syncExtras(): void {
        if(Luma.citations.length)displayedCitations=Luma.citations;
        if(Luma.fileResults.length)displayedFiles=Luma.fileResults;
        if(Luma.error)displayedError=Luma.error;
        retire.restart();
    }
    Component.onCompleted:{sync();syncProposals();syncExtras();syncAttachments();syncConversations();}
    onVisibleChanged:if(!visible){manualScroll.stop();followScroll.stop();pickerOpen=false;}else Qt.callLater(followTarget)
    onWorkingChanged:if(working){pendingStatus=Luma.status||"Understanding";}
    Connections {
        target:Luma
        function onConversationIdChanged(){root.pickerOpen=false;root.initialized=false;root.historyOpen=false;root.deleteArmed="";}
        function onConversationsChanged(){root.syncConversations();}
        function onMessagesChanged(){root.sync()}
        function onProposalsChanged(){root.syncProposals()}
        function onCitationsChanged(){root.syncExtras()}
        function onFileResultsChanged(){root.syncExtras()}
        function onErrorChanged(){root.syncExtras()}
        function onAttachmentsChanged(){root.syncAttachments()}
        function onStatusChanged(){if(root.working&&Luma.status)root.pendingStatus=Luma.status}
    }
    // Retain outgoing text until its section has collapsed; never erase mid-frame.
    Timer {id:retire;interval:Tokens.animMedium+20;onTriggered:{
        if(!Luma.proposals.length)proposals.clear();
        if(!Luma.citations.length)root.displayedCitations=[];
        if(!Luma.fileResults.length)root.displayedFiles=[];
        if(!Luma.error)root.displayedError="";
        if(!Luma.attachments.length)attachments.clear();
        if(!root.followups.length)root.displayedFollowups=[];
    }}
    ListModel {id:turns}
    ListModel {id:proposals}
    NumberAnimation {id:manualScroll;target:transcript;property:"contentY";duration:Tokens.animFast;easing.type:Easing.OutCubic}
    Flickable {
        id:transcript;x:0;y:0;width:parent.width;height:Math.max(0,parent.height-tools.height-16)
        visible:!root.historyOpen&&opacity>.001;opacity:1-root.pickerAmount;enabled:!root.pickerOpen
        contentWidth:width;contentHeight:flow.height;clip:true;boundsBehavior:Flickable.StopAtBounds
        onHeightChanged:if(root.following)Qt.callLater(root.followTarget)
        flickableDirection:Flickable.VerticalFlick
        onDraggingChanged:if(dragging)root.stopFollowing()
        onFlickingChanged:if(flicking)root.stopFollowing()
        WheelHandler {target:null;onWheel:event=>{root.stopFollowing();event.accepted=false;}}
        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded;onPressedChanged:if(pressed)root.stopFollowing()}
        Column {
            id:flow;width:transcript.width-8;spacing:26
            Repeater {id:turnRepeater;model:turns
                onItemAdded:root.turnRevision++
                onItemRemoved:root.turnRevision++
                Item {
                    id:turn;required property var model
                    property real arrival:1
                    readonly property real naturalHeight:(model.role==="user"?body.implicitHeight:document.naturalHeight+(turnSources.visible?12+turnSources.height:0)+(turnActions.visible?10+turnActions.naturalHeight:0))+(model.role==="user"?26:8)
                    width:flow.width;height:naturalHeight*arrival;clip:arrival<.999
                    Component.onCompleted:if(model.fresh){arrival=0;entry.start();}
                    NumberAnimation {id:entry;target:turn;property:"arrival";to:1;duration:Tokens.animSlow;easing.type:Easing.OutQuint}
                    Item {
                        width:parent.width;height:turn.naturalHeight
                        transform:Translate {y:5*(1-turn.arrival)}
                        TextMetrics {id:userMeasure;font:body.font;text:turn.model.text}
                        Rectangle {id:userBubble;x:parent.width-width-8;y:0;width:Math.min(parent.width-28,Math.max(80,userMeasure.boundingRect.width+28));height:turn.naturalHeight;radius:16;color:Theme.withAlpha(Theme.text,.04);visible:turn.model.role==="user"}
                        TextEdit {
                            id:body;width:userBubble.width-28
                            visible:turn.model.role==="user"
                            x:userBubble.x+14;y:turn.model.role==="user"?13:4
                            text:turn.model.text;readOnly:true;selectByMouse:true;wrapMode:TextEdit.Wrap;textFormat:TextEdit.PlainText
                            color:Theme.text;selectionColor:Theme.accent;selectedTextColor:Theme.accentText
                            font.family:Tokens.font;font.pixelSize:Preferences.lumaTextSize;font.weight:Font.Normal
                            font.letterSpacing:-.1
                            font.preferTypoLineMetrics:true;font.hintingPreference:Font.PreferVerticalHinting
                            renderType:Tokens.textRenderType
                            Accessible.name:(turn.model.role==="user"?"You: ":"Luma: ")+text
                        }
                        LumaDocument {id:document;y:4;x:2;width:parent.width-10;visible:turn.model.role==="assistant";text:turn.model.text;presentation:JSON.parse(turn.model.presentation);animate:root.visible}
                        LumaActions {id:turnActions;y:turnSources.visible?turnSources.y+turnSources.height+10:document.y+document.height+10;width:parent.width-8;entries:JSON.parse(turn.model.execution);visible:turn.model.role==="assistant"&&entries.length>0;animate:root.visible}
                        LumaSources {
                            id:turnSources;y:document.y+document.height+12;width:parent.width
                            sources:JSON.parse(turn.model.citations);visible:turn.model.role==="assistant"&&sources.length>0
                            animate:root.visible;onOpened:url=>Qt.openUrlExternally(url);onExpanded:root.stopFollowing()
                        }
                    }
                }
            }
            LumaSection {
                id:sourceSection
                width:parent.width;expanded:Luma.citations.length>0&&!(root.lastTurn?.citations?.length);animate:root.visible
                targetHeight:sourceLinks.naturalHeight
                LumaSources {id:sourceLinks;width:parent.width;sources:root.displayedCitations;animate:root.visible;onOpened:url=>Qt.openUrlExternally(url);onExpanded:root.stopFollowing()}
            }
            LumaSection {
                id:fileSection
                width:parent.width;expanded:Luma.fileResults.length>0;animate:root.visible
                Column {width:parent.width;spacing:8
                    Repeater {model:root.displayedFiles
                        Rectangle {
                            id:file;required property var modelData
                            property bool excerptExpanded:false
                            width:parent.width;height:64+(excerpt.visible?excerpt.implicitHeight+18:0);radius:12;color:Theme.withAlpha(Theme.text,.025)
                            border.width:1;border.color:Theme.withAlpha(Theme.text,.065);clip:true
                            Behavior on height {enabled:root.visible&&!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}}
                            Icon {x:14;y:22;icon:file.modelData.kind==="folder"?"folder":"draft";size:20;color:Theme.subtext}
                            PanelText {x:46;y:14;width:parent.width-(file.modelData.kind==="folder"?88:154);text:file.modelData.title;font.pixelSize:13;font.weight:Font.Medium;elide:Text.ElideRight}
                            PanelText {x:46;y:35;width:parent.width-(file.modelData.kind==="folder"?88:154);text:(file.modelData.page?"Page "+file.modelData.page+" · ":"")+file.modelData.path.replace(Quickshell.env("HOME"),"~");font.pixelSize:10;color:Theme.subtext;elide:Text.ElideMiddle}
                            PanelText {
                                id:excerpt;x:14;y:64;width:parent.width-60;visible:!!file.modelData.excerpt
                                text:file.modelData.excerpt?(file.excerptExpanded?file.modelData.excerpt:(file.modelData.match||file.modelData.excerpt.slice(0,240))):""
                                maximumLineCount:file.excerptExpanded?2147483647:3
                                font.pixelSize:12;color:Theme.subtext;wrapMode:Text.WordWrap;elide:Text.ElideRight
                                Accessible.name:"Matching document passage"
                            }
                            IconButton {x:parent.width-38;y:62;visible:!!file.modelData.excerpt;icon:file.excerptExpanded?"expand_less":"expand_more";size:14;color:Theme.subtext;label:file.excerptExpanded?"Collapse passage":"Read passage";onClicked:{root.stopFollowing();file.excerptExpanded=!file.excerptExpanded}}
                            Row {anchors.right:parent.right;anchors.rightMargin:8;y:17;spacing:2
                                IconButton {icon:"more_horiz";size:16;label:"File actions";visible:file.modelData.kind!=="folder";onClicked:IslandDrop.accept([file.modelData.path])}
                                IconButton {icon:"attach_file";size:16;label:"Share file with Luma";visible:file.modelData.kind!=="folder";enabled:!Luma.busy&&Luma.attachments.length<3;onClicked:Luma.attach(file.modelData.path)}
                                IconButton {icon:"open_in_new";size:16;label:"Open file";onClicked:Quickshell.execDetached(["xdg-open",file.modelData.url||file.modelData.path])}
                            }
                        }
                    }
                }
            }
            LumaSection {
                id:metricsSection
                width:parent.width;expanded:Luma.liveMetrics;animate:root.visible
                targetHeight:livePerformance.implicitHeight
                LumaPerformance {id:livePerformance;width:parent.width;observing:Luma.liveMetrics&&root.visible&&!root.historyOpen&&CanvasState.opened;onExplainRequested:root.followupRequested("Explain my current system performance and the heaviest processes. Use measured activity; suggest safe next steps.")}
            }
            LumaSection {
                id:executionSection
                width:parent.width;expanded:Luma.execution.length>0&&(Luma.busy||!root.lastTurn?.execution?.length);animate:root.visible
                LumaActions {width:parent.width;entries:Luma.receipts(Luma.execution);animate:root.visible}
            }

            LumaSection {
                id:proposalSection
                width:parent.width;expanded:Luma.proposals.length>0;animate:root.visible
                Column {width:parent.width;spacing:10
                    Repeater {model:proposals
                        Rectangle {
                            id:proposal;required property var model
                            property real controls:model.status==="pending"&&!Luma.autoLocal?1:0
                            property real borderEmphasis:model.status==="pending"?.32:.1
                            readonly property bool adjustable:["focus","volume","brightness"].includes(model.name)
                            property bool detailsOpen:false
                            readonly property real detailsHeight:detailsOpen?Math.min(170,stepDetailsText.implicitHeight+16):0
                            width:parent.width;height:proposalLabel.implicitHeight+(adjustable?114:66)+detailsHeight;radius:Tokens.surfaceRadius;color:"transparent"
                            border.width:1;border.color:Theme.withAlpha(Theme.accent,borderEmphasis)
                            SurfaceLighting {anchors.fill:parent;radius:parent.radius;focused:proposal.model.status==="pending"}
                            Behavior on borderEmphasis {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
                            Behavior on controls {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutQuint}}
                            PanelText {id:proposalLabel;x:16;y:14;width:parent.width-32;text:proposal.model.label;font.pixelSize:13;font.weight:Font.Medium;wrapMode:Text.WordWrap}
                            Flickable {x:16;y:proposalLabel.implicitHeight+23;width:parent.width-32;height:proposal.detailsHeight;visible:proposal.detailsOpen;clip:true;contentWidth:width;contentHeight:stepDetailsText.implicitHeight+16;boundsBehavior:Flickable.StopAtBounds
                                PanelText {id:stepDetailsText;width:parent.width-10;text:proposal.model.detail;font.pixelSize:11;font.family:"monospace";color:Theme.subtext;wrapMode:Text.WrapAnywhere}
                                ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
                            }
                            Slider {
                                id:adjuster;x:16;y:proposalLabel.implicitHeight+28;width:parent.width-32;height:26
                                visible:proposal.adjustable;enabled:proposal.model.status==="pending"&&!Luma.busy
                                from:proposal.model.name==="focus"?1:0;to:proposal.model.name==="focus"?120:100;stepSize:1;wheelEnabled:true
                                Binding {target:adjuster;property:"value";value:proposal.model.amount;when:!adjuster.pressed;restoreMode:Binding.RestoreNone}
                                onMoved:Luma.adjust(proposal.model.position,value)
                                Accessible.name:"Adjust proposed "+proposal.model.name
                                background:Rectangle {x:adjuster.leftPadding;y:(adjuster.height-height)/2;width:adjuster.availableWidth;height:4;radius:2;color:Theme.withAlpha(Theme.text,.1)
                                    Rectangle {width:parent.width*adjuster.visualPosition;height:4;radius:2;color:Theme.accent}
                                }
                                handle:Rectangle {x:adjuster.leftPadding+adjuster.visualPosition*(adjuster.availableWidth-width);y:(adjuster.height-height)/2;width:14;height:14;radius:7;color:Theme.accent;scale:adjuster.pressed?1.14:1;Behavior on scale {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutQuint}}}
                            }
                            Item {x:16;y:parent.height-40;width:parent.width-32;height:30;clip:true
                                Row {spacing:6;opacity:proposal.controls;visible:opacity>.001;enabled:proposal.model.status==="pending"&&Luma.proposals[proposal.model.position]?.label===proposal.model.label;transform:Translate {y:-8*(1-proposal.controls)}
                                    ReviewButton {text:proposal.model.name==="system_step"?"Continue":"Apply";enabled:!Luma.busy;accented:true;onClicked:Luma.apply(proposal.model.position)}
                                    ReviewButton {text:proposal.detailsOpen?"Hide details":"Details";visible:!!proposal.model.detail;onClicked:proposal.detailsOpen=!proposal.detailsOpen}
                                    ReviewButton {text:"Dismiss";onClicked:Luma.dismiss(proposal.model.position)}
                                }
                                Row {x:4;spacing:6;height:28;opacity:1-proposal.controls;visible:opacity>.001;transform:Translate {y:8*proposal.controls}
                                    Icon {anchors.verticalCenter:parent.verticalCenter;icon:["requested","done","scheduled"].includes(proposal.model.status)?"check":proposal.model.status==="failed"?"error":"close";size:14;color:proposal.model.status==="failed"?Theme.red:Theme.accent}
                                    PanelText {anchors.verticalCenter:parent.verticalCenter;text:proposal.model.status==="done"&&proposal.model.name==="awake"&&proposal.model.deadline>0?(KeepAwake.active&&KeepAwake.until===proposal.model.deadline?KeepAwake.remaining+" min left":KeepAwake.now>=proposal.model.deadline?"Ended":"Stopped"):({requested:"Requested",done:"Done",scheduled:"Reminder set",dismissed:"Removed",undone:"Undone",pending:"Working"})[proposal.model.status]||"Unavailable";font.pixelSize:11;color:Theme.subtext}
                                    ReviewButton {text:"Undo";visible:Luma.canUndo(proposal.model.position);enabled:!Luma.busy;onClicked:Luma.undoAction(proposal.model.position)}
                                }
                            }
                        }
                    }
                }
            }
            LumaSection {
                id:nextSection;width:parent.width;expanded:root.followups.length>0&&!root.working;animate:root.visible
                Flow {width:parent.width;spacing:6
                    Repeater {model:root.displayedFollowups
                        ActionButton {required property var modelData;text:modelData.label;implicitHeight:29;implicitWidth:Math.min(root.width,Math.max(64,text.length*7+24));enabled:!Luma.busy;onClicked:root.followupRequested(modelData.query)
                            background:Rectangle {radius:9;color:parent.hovered?Theme.withAlpha(Theme.text,.04):"transparent";border.width:1;border.color:Theme.withAlpha(Theme.text,.1)}
                        }
                    }
                }
            }
            LumaSection {
                id:pendingSection
                width:parent.width;expanded:root.working;animate:root.visible
                Row {width:parent.width;height:30;spacing:10
                    LumaVoiceLight {width:48;height:26;activity:"thinking";active:root.working&&root.visible}
                    RollingText {width:parent.width-100;height:26;text:root.pendingStatus;font.pixelSize:12;color:Theme.subtext;horizontalAlignment:Text.AlignLeft;verticalAlignment:Text.AlignVCenter}
                    IconButton {icon:"close";size:14;label:"Stop answer";enabled:root.working;onClicked:Luma.cancel()}
                }
            }
            LumaSection {
                id:errorSection
                width:parent.width;expanded:!!Luma.error;animate:root.visible
                Column {width:parent.width;spacing:12
                    PanelText {width:parent.width;text:root.displayedError;wrapMode:Text.WordWrap;font.pixelSize:13;color:Theme.subtext}
                    Row {spacing:8
                        ActionButton {text:Luma.retrySeconds?"Retry in "+Luma.retrySeconds+"s":"Retry";enabled:!Luma.busy&&!Luma.retrySeconds;onClicked:Luma.retry()}
                        ActionButton {text:"Web results";enabled:!Luma.busy;onClicked:{const last=Luma.messages.slice().reverse().find(turn=>turn.role==="user");if(last)root.webRequested(last.text);}}
                    }
                }
            }
        }
    }
    Column {
        id:tools;anchors.bottom:parent.bottom;width:parent.width;spacing:8
        opacity:1-root.pickerAmount;visible:opacity>.001;enabled:!root.pickerOpen
        LumaSection {
            id:attachmentSection
            width:parent.width;expanded:Luma.attachments.length>0||!!Luma.sharedText;animate:root.visible
            Flow {
                width:parent.width;spacing:6
                move:Transition {NumberAnimation {properties:"x,y";duration:Tokens.animMedium;easing.type:Easing.OutQuint}}
                Repeater {model:attachments
                    ActionButton {required property var model;text:model.name+" ×";implicitWidth:Math.min(root.width,Math.max(72,text.length*7+24));implicitHeight:28;onClicked:{const index=Luma.attachments.indexOf(model.path);if(index>=0)Luma.detach(index);}}
                }
                ActionButton {visible:!!Luma.sharedText;text:"Shared text ×";implicitHeight:28;onClicked:Luma.sharedText=""}
            }
        }
        Row {
            width:parent.width;height:32;spacing:6
            IconButton {icon:"attach_file";size:16;color:Theme.subtext;label:"Attach file · sent to answer provider";enabled:!Luma.busy&&Luma.attachments.length<3;onClicked:root.openAttachments()}
            IconButton {icon:"content_paste";size:16;color:Theme.subtext;label:"Share clipboard text · sent to answer provider";enabled:!Luma.busy;onClicked:Luma.shareClipboard()}
            IconButton {icon:"history";size:16;color:root.historyOpen?Theme.accent:Theme.subtext;label:"Conversations";enabled:!Luma.busy;onClicked:{root.historyOpen=!root.historyOpen;root.deleteArmed="";}}
            IconButton {icon:"add";size:16;color:Theme.subtext;label:"New conversation";enabled:!Luma.busy;onClicked:{Luma.newConversation();root.historyOpen=false;root.focusInput();}}
            PanelText {width:Math.max(0,parent.width-152);height:32;verticalAlignment:Text.AlignVCenter;visible:!!Luma.currentWindow;text:Luma.currentWindow?.app??"";font.pixelSize:11;color:Theme.subtext}
        }
    }
    ListView {
        id:history
        x:0;y:0;width:parent.width;height:Math.max(0,parent.height-tools.height-16)
        visible:root.historyOpen&&!root.pickerOpen;clip:true;spacing:6
        model:conversationRows
        currentIndex:0
        highlightMoveDuration:Tokens.animFast
        highlight:Rectangle {radius:Tokens.fieldRadius;color:Theme.withAlpha(Theme.text,.035)}
        remove:Transition {NumberAnimation {properties:"opacity";to:0;duration:Tokens.animFast;easing.type:Easing.OutCubic}}
        displaced:Transition {NumberAnimation {properties:"y";duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
        boundsBehavior:Flickable.StopAtBounds
        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
        delegate:Rectangle {
            id:thread;required property var model
            width:ListView.view.width-8;height:52;radius:Tokens.fieldRadius
            color:threadHover.hovered?Theme.withAlpha(Theme.text,.045):"transparent"
            border.width:model.key===Luma.conversationId?1:0;border.color:Theme.withAlpha(Theme.accent,.5)
            Behavior on color {ColorAnimation {duration:Tokens.animFast}}
            HoverHandler {id:threadHover;cursorShape:Qt.PointingHandCursor}
            MouseArea {x:0;y:0;width:parent.width-48;height:parent.height;cursorShape:Qt.PointingHandCursor;onClicked:{Luma.selectConversation(thread.model.key);root.historyOpen=false;root.focusInput();}}
            PanelText {x:16;y:9;width:parent.width-66;text:thread.model.title;font.pixelSize:13;font.weight:Font.Medium;elide:Text.ElideRight}
            PanelText {x:16;y:29;width:parent.width-66;text:Qt.formatDateTime(new Date(thread.model.updatedAt),"MMM d · HH:mm");font.pixelSize:10;color:Theme.subtext}
            IconButton {anchors.right:parent.right;anchors.rightMargin:8;anchors.verticalCenter:parent.verticalCenter;icon:root.deleteArmed===thread.model.key?"check":"delete";size:16;color:root.deleteArmed===thread.model.key?Theme.accent:Theme.subtext;label:root.deleteArmed===thread.model.key?"Confirm deletion":"Delete conversation";onClicked:{if(root.deleteArmed===thread.model.key){Luma.deleteConversation(thread.model.key);root.historyOpen=true;root.deleteArmed="";}else root.deleteArmed=thread.model.key;}}
        }
        PanelText {parent:history;anchors.centerIn:parent;width:Math.max(0,parent.width-32);horizontalAlignment:Text.AlignHCenter;visible:history.count===0;text:"Your conversations will appear here";font.pixelSize:12;color:Theme.subtext;wrapMode:Text.WordWrap}
    }
    component ReviewButton:AbstractButton {
        id:button
        property bool accented:false
        implicitWidth:Math.max(60,label.implicitWidth+24);implicitHeight:29
        hoverEnabled:true;focusPolicy:Qt.NoFocus
        Accessible.name:text
        opacity:enabled?1:.4;scale:pressed?.97:1
        Behavior on scale {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
        background:Rectangle {radius:8;color:Theme.withAlpha(button.accented?Theme.accent:Theme.text,button.pressed?.08:button.hovered?.04:0);border.width:1;border.color:Theme.withAlpha(button.accented?Theme.accent:Theme.text,button.accented?.4:.1);Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
        contentItem:PanelText {id:label;text:button.text;color:button.accented?Theme.accent:Theme.subtext;font.pixelSize:11;font.weight:Font.Medium;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
    }
    Loader {
        id:fileBrowser;anchors.fill:parent;active:root.pickerOpen||root.pickerAmount>.001
        visible:opacity>.001;opacity:root.pickerAmount;enabled:root.pickerOpen
        transform:Translate {y:6*(1-root.pickerAmount)}
        source:"LumaFilePicker.qml"
        onLoaded:{if(root.lastFolder.toString())item.folder=root.lastFolder;Qt.callLater(()=>{if(root.pickerOpen)item.focusFilter();});}
    }
    Connections {
        target:fileBrowser.item
        function onFolderChanged(){root.lastFolder=fileBrowser.item.folder;}
        function onCancelled(){root.closeAttachments();}
        function onAccepted(paths){for(const path of paths)Luma.attach(path);root.closeAttachments();}
    }
}
