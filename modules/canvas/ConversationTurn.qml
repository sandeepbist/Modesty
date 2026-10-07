import QtQuick
import qs.services
import qs.components
import qs.theme

Item {
    id:turn
    required property var model
    property bool animate:true
    property real arrival:1
    readonly property real naturalHeight:message.item?.naturalHeight??0
    height:naturalHeight*arrival
    clip:arrival<.999
    signal expanded()
    Component.onCompleted:if(model.fresh){arrival=0;entry.start();}
    NumberAnimation {id:entry;target:turn;property:"arrival";to:1;duration:Tokens.animSlow;easing.type:Easing.OutQuint}
    // A turn needs one view. Hidden rich text still parses and builds delegates.
    Loader {
        id:message;width:parent.width;height:turn.naturalHeight
        transform:Translate {y:5*(1-turn.arrival)}
        sourceComponent:turn.model.role==="user"?userMessage:assistantMessage
    }
    Component {
        id:userMessage
        Item {
            readonly property real naturalHeight:body.implicitHeight+26
            TextMetrics {id:userMeasure;font:body.font;text:turn.model.text}
            Rectangle {id:userBubble;x:parent.width-width-8;y:0;width:Math.min(parent.width-28,Math.max(80,userMeasure.boundingRect.width+28));height:turn.naturalHeight;radius:16;color:Theme.withAlpha(Theme.text,.04)}
            TextEdit {
                id:body;width:userBubble.width-28
                x:userBubble.x+14;y:13
                text:turn.model.text;readOnly:true;selectByMouse:true;wrapMode:TextEdit.Wrap;textFormat:TextEdit.PlainText
                color:Theme.text;selectionColor:Theme.accent;selectedTextColor:Theme.accentText
                font.family:Tokens.font;font.pixelSize:Preferences.lumaTextSize;font.weight:Font.Normal
                font.letterSpacing:-.1
                font.preferTypoLineMetrics:true;font.hintingPreference:Font.PreferVerticalHinting
                renderType:Tokens.textRenderType
                Accessible.name:"You: "+text
            }
        }
    }
    Component {
        id:assistantMessage
        Item {
            readonly property real naturalHeight:document.naturalHeight+(turnSources.visible?12+turnSources.height:0)+(turnActions.visible?10+turnActions.naturalHeight:0)+8
            LumaDocument {id:document;y:4;x:2;width:parent.width-10;text:turn.model.text;presentation:JSON.parse(turn.model.presentation);animate:turn.animate}
            LumaActions {id:turnActions;y:turnSources.visible?turnSources.y+turnSources.height+10:document.y+document.height+10;width:parent.width-8;entries:JSON.parse(turn.model.execution);visible:entries.length>0;animate:turn.animate}
            LumaSources {
                id:turnSources;y:document.y+document.height+12;width:parent.width
                sources:JSON.parse(turn.model.citations);visible:sources.length>0
                animate:turn.animate;onOpened:url=>Qt.openUrlExternally(url);onExpanded:turn.expanded()
            }
        }
    }
}
