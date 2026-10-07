import QtQuick
import QtQuick.Controls
import Quickshell
import qs.components
import qs.theme

// One persistent reading surface. Refinement keeps the last answer readable.
Rectangle {
    id:root
    property var answer:null
    property bool pending:false
    property bool working:pending
    property string status:"Understanding"
    property string error:""
    property real retryAt:0
    property bool expanded:false
    property bool animate:true
    property real availableHeight:300
    property real now:Date.now()
    property real reveal:1
    property bool textPresented:false
    property real scrollTarget:0
    readonly property bool filled:!!answer?.text
    readonly property bool general:answer?.label==="General answer"&&!answer?.citations?.length
    readonly property int retrySeconds:Math.max(0,Math.ceil(retryAt-now/1000))
    readonly property real chrome:general?80:64
    readonly property real bodyNaturalHeight:filled?document.naturalHeight+(answer?.citations?.length?14+sources.naturalHeight:0)+(nextSteps.visible?14+nextSteps.implicitHeight:0):errorBody.implicitHeight
    readonly property real preferredHeight:Math.min(availableHeight,pending&&!filled?112:filled?chrome+Math.min(bodyNaturalHeight,expanded?availableHeight-chrome:document.structured?180:104):Math.max(118,80+bodyNaturalHeight))
    readonly property real readingHeight:Math.max(24,height-chrome)
    signal toggleExpanded()
    signal continueConversation()
    signal retry()
    signal webResults()
    signal sourceRequested(string url)
    signal followupRequested(string query)
    function scroll(amount:real):void {scrollTarget=Math.max(0,Math.min(Math.max(0,reader.contentHeight-reader.height),reader.contentY+amount));}
    onScrollTargetChanged:reader.contentY=scrollTarget
    Behavior on scrollTarget {enabled:root.animate&&!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}}
    implicitHeight:preferredHeight;height:preferredHeight
    Behavior on height {enabled:root.animate&&root.visible&&!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}}
    radius:Tokens.surfaceRadius;antialiasing:true
    gradient:Gradient {
        GradientStop {position:0;color:Theme.withAlpha(Theme.surfaceSolid,.68)}
        GradientStop {position:1;color:Theme.withAlpha(Theme.surfaceSolid,.32)}
    }
    border.width:1;border.color:Theme.withAlpha(Theme.text,Tokens.borderAlpha)
    SurfaceLighting {anchors.fill:parent;radius:root.radius;working:root.working;focused:root.expanded;interactive:true}
    Timer {interval:1000;repeat:true;running:root.visible&&root.retryAt*1000>root.now;onTriggered:root.now=Date.now()}
    onRetryAtChanged:now=Date.now()
    function present():void {
        if(!filled){arrival.stop();textPresented=false;reveal=pending?0:1;return;}
        if(textPresented){if(!arrival.running)reveal=1;return;}
        textPresented=true;
        if(!pending&&animate&&!Tokens.reducedMotion){reveal=0;arrival.restart();}else{arrival.stop();reveal=1;}
    }
    onAnswerChanged:{if(!pending&&!answer?.streaming&&!textPresented){reader.contentY=0;scrollTarget=0;}Qt.callLater(present);}
    onPendingChanged:Qt.callLater(present)
    NumberAnimation {id:arrival;target:root;property:"reveal";to:1;duration:Tokens.animMedium;easing.type:Easing.OutQuint}
    LumaActivity {id:work;x:16;y:13;width:22;height:18;active:root.working&&root.visible}
    PanelText {x:46;y:13;height:20;text:"Luma";font.pixelSize:12;font.weight:Font.DemiBold;font.letterSpacing:-.15;verticalAlignment:Text.AlignVCenter}
    RollingText {
        x:92;y:13;width:Math.max(0,parent.width-200);height:20
        text:root.pending?({Understanding:"Thinking it through…",Refining:"A closer look…",Writing:"Putting it together…",Thinking:"Thinking it through…"})[root.status]||root.status:root.filled?(root.answer.cached?"From a moment ago":root.answer.presentation?.layout==="decision"?"Let’s weigh it up":root.answer.presentation?.layout==="comparison"?"Side by side":root.answer.label||"Answer"):root.retrySeconds?"A little breather":"Couldn’t finish"
        font.pixelSize:11;color:Theme.subtext;horizontalAlignment:Text.AlignLeft;verticalAlignment:Text.AlignVCenter
    }
    Row {
        anchors.right:parent.right;anchors.rightMargin:9;y:7;spacing:0
        IconButton {icon:"content_copy";label:"Copy complete answer";size:14;visible:root.filled;enabled:!root.pending;onClicked:Quickshell.clipboardText=root.answer.text}
        IconButton {icon:"expand_more";label:root.expanded?"Collapse answer":"Expand answer";size:14;visible:root.filled;enabled:!root.pending;onClicked:root.toggleExpanded();rotation:root.expanded?180:0;Behavior on rotation {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutQuint}}}
        IconButton {icon:"arrow_upward";label:"Continue with Luma";size:14;visible:root.filled;enabled:!root.pending;onClicked:root.continueConversation()}
    }
    Item {
        x:16;y:46;width:parent.width-32;height:root.readingHeight;clip:true
        Column {width:parent.width;y:8;spacing:18;visible:root.pending&&!root.filled
            Repeater {model:[.92,.65]
                Rectangle {required property real modelData;width:parent.width*modelData;height:4;radius:2;color:Theme.withAlpha(Theme.subtext,.16+.04*Math.sin(work.phase))}
            }
        }
        Item {
            width:parent.width;height:parent.height*(root.filled?root.reveal:1);clip:true;visible:root.filled||!root.pending
            Flickable {
                id:reader;width:parent.width;height:root.readingHeight;clip:true
                contentWidth:width;contentHeight:reading.height
                boundsBehavior:Flickable.StopAtBounds;flickableDirection:Flickable.VerticalFlick
                Column {
                    id:reading;width:reader.width-6;spacing:14
                    transform:Translate {y:root.filled?6*(1-root.reveal):0}
                    LumaDocument {id:document;width:parent.width;visible:root.filled;text:root.answer?.text??"";presentation:root.answer?.presentation??({});animate:root.animate;interactive:!root.pending}
                    PanelText {id:errorBody;width:parent.width;visible:!root.filled;text:root.error||"No answer returned. Try again when ready.";font.pixelSize:Tokens.readingSize;color:Theme.subtext;wrapMode:Text.WordWrap;elide:Text.ElideNone;lineHeight:Tokens.readingLeading}
                    LumaSources {id:sources;width:parent.width;visible:root.filled&&!!root.answer?.citations?.length;sources:root.answer?.citations??[];animate:root.animate;interactive:!root.pending;onOpened:url=>root.sourceRequested(url);onExpanded:if(!root.expanded)root.toggleExpanded()}
                    Flow {
                        id:nextSteps;width:parent.width;spacing:6;visible:root.filled&&root.expanded&&!root.pending&&!!root.answer?.presentation?.followups?.length
                        Repeater {model:root.answer?.presentation?.followups??[]
                            ActionButton {required property var modelData;text:modelData.label;implicitHeight:29;implicitWidth:Math.min(nextSteps.width,Math.max(64,text.length*7+24));onClicked:root.followupRequested(modelData.query)
                                background:Rectangle {radius:9;color:parent.hovered?Theme.withAlpha(Theme.text,.04):"transparent";border.width:1;border.color:Theme.withAlpha(Theme.text,.1)}
                            }
                        }
                    }
                }
                ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
            }
        }
    }
    PanelText {x:16;y:parent.height-27;visible:root.filled&&root.general;text:"General knowledge · no live citations";font.pixelSize:10;color:Theme.subtext}
    Row {
        x:12;y:parent.height-33;spacing:4;visible:!root.pending&&!root.filled
        ActionButton {text:root.retrySeconds?"Retry in "+root.retrySeconds+"s":"Retry";enabled:!root.retrySeconds;implicitHeight:26;onClicked:root.retry()}
        ActionButton {text:"Web results";implicitHeight:26;onClicked:root.webResults()}
    }
}
