import QtQuick
import QtQuick.Controls
import Quickshell
import qs.components
import qs.theme
import "AnswerFormat.js" as Format
import "../../services/ModelDiff.js" as ModelDiff

Item {
    id:root
    property string plainText:""
    property bool interactive:true
    property font font:Qt.font({family:Tokens.font,pixelSize:Tokens.readingSize,preferTypoLineMetrics:true,hintingPreference:Font.PreferVerticalHinting})
    property color color:Theme.text
    implicitHeight:flow.implicitHeight
    height:implicitHeight
    function sync():void {ModelDiff.reconcile(blocks,Format.blocks(plainText),"key");}
    onPlainTextChanged:sync()
    Component.onCompleted:sync()
    ListModel {id:blocks}
    Column {
        id:flow;width:root.width;spacing:12
        Repeater {
            model:blocks
            delegate:Item {
                id:block;required property var model
                width:flow.width;height:model.kind==="code"?codeSurface.height:paragraph.implicitHeight
                TextEdit {
                    id:paragraph;width:parent.width;visible:block.model.kind==="prose"
                    // Use the palette target so a color animation cannot reparse
                    // the entire document on every frame.
                    text:block.model.kind==="prose"?Format.prose(block.model.body,String(Theme.pal.accent),Math.round(Tokens.readingLeading*100)):""
                    readOnly:true;selectByMouse:root.interactive;wrapMode:TextEdit.Wrap;textFormat:TextEdit.RichText
                    color:root.color;selectionColor:Theme.accent;selectedTextColor:Theme.accentText
                    font:root.font
                    renderType:Tokens.textRenderType;Accessible.name:block.model.body
                    onLinkActivated:link=>{if(root.interactive&&Format.safeLink(link))Qt.openUrlExternally(link);}
                }
                Rectangle {
                    id:codeSurface;width:parent.width;height:Math.min(250,Math.max(80,code.implicitHeight+56))
                    visible:block.model.kind==="code";radius:Tokens.fieldRadius;color:Theme.withAlpha(Theme.text,.035)
                    border.width:1;border.color:Theme.withAlpha(Theme.text,Tokens.borderAlpha)
                    PanelText {x:14;y:10;width:parent.width-60;height:22;verticalAlignment:Text.AlignVCenter;text:block.model.language||"Code";font.pixelSize:Tokens.captionSize;color:Theme.subtext}
                    IconButton {anchors.right:parent.right;anchors.rightMargin:7;y:5;icon:"content_copy";size:14;label:"Copy code";enabled:root.interactive;onClicked:Quickshell.clipboardText=block.model.body}
                    Flickable {
                        id:codeView;x:14;y:39;width:parent.width-28;height:parent.height-y-14
                        clip:true;contentWidth:Math.max(width,code.contentWidth);contentHeight:code.implicitHeight
                        boundsBehavior:Flickable.StopAtBounds;flickableDirection:Flickable.AutoFlickIfNeeded
                        TextEdit {
                            id:code;width:codeView.width;text:block.model.kind==="code"?block.model.body:""
                            textFormat:TextEdit.PlainText;wrapMode:TextEdit.NoWrap;readOnly:true;selectByMouse:root.interactive
                            color:Theme.text;selectionColor:Theme.accent;selectedTextColor:Theme.accentText
                            font.family:"monospace";font.pixelSize:12;renderType:Tokens.textRenderType
                            Accessible.name:block.model.body
                        }
                        ScrollBar.horizontal:ScrollBar {policy:ScrollBar.AsNeeded}
                        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
                    }
                }
            }
        }
    }
}
