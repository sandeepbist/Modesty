import QtQuick
import QtQuick.Controls
import Quickshell
import qs.services
import qs.components
import qs.theme

Column {
    id:root
    property var entries:[]
    property bool expanded:Preferences.lumaActionDetails
    property bool animate:true
    readonly property real naturalHeight:entries.length?toggle.height+details.height+spacing:0
    height:naturalHeight
    spacing:6
    AbstractButton {
        id:toggle;width:parent.width;height:32;hoverEnabled:true
        Accessible.name:root.entries.length+" action steps"
        Accessible.description:root.expanded?"Collapse details":"Expand details"
        onClicked:root.expanded=!root.expanded
        background:Rectangle {radius:9;color:toggle.hovered?Theme.withAlpha(Theme.text,.035):"transparent";Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
        contentItem:Item {
            Icon {x:6;anchors.verticalCenter:parent.verticalCenter;icon:"expand_more";size:13;color:Theme.subtext;rotation:root.expanded?0:-90;Behavior on rotation {NumberAnimation {duration:Tokens.animMedium}}}
            PanelText {x:28;anchors.verticalCenter:parent.verticalCenter;text:root.entries.length+(root.entries.length===1?" step":" steps");font.pixelSize:11;color:Theme.subtext}
            PanelText {anchors.right:parent.right;anchors.rightMargin:8;anchors.verticalCenter:parent.verticalCenter;text:root.entries.some(e=>!e.result?.ok)?"Needs attention":"";font.pixelSize:11;color:Theme.subtext}
        }
    }
    LumaSection {
        id:details;width:parent.width;expanded:root.expanded&&root.entries.length>0;animate:root.animate
        Column {width:parent.width;spacing:8
            Repeater {model:root.entries
                Column {
                    id:step;required property var modelData
                    property bool open:false
                    width:parent.width;spacing:6
                    readonly property string detail:{const t=modelData.tool||{},r=modelData.result||{};return [t.argv?.length?t.argv.join(" "):t.path||t.uri||t.action_name||"",[t.id||"",t.operation||""].filter(Boolean).join(" · "),t.action_args||"",r.error||"",r.stdout||"",r.stderr||"",r.note||""].filter(Boolean).join("\n\n");}
                    AbstractButton {
                        id:stepButton;width:parent.width;height:Math.max(42,title.implicitHeight+20);hoverEnabled:true
                        onClicked:step.open=!step.open
                        Accessible.name:title.text
                        background:Rectangle {radius:10;color:Theme.withAlpha(Theme.text,stepButton.hovered?.04:.018)}
                        contentItem:Item {
                            Icon {x:10;anchors.verticalCenter:parent.verticalCenter;icon:step.modelData.result?.ok?"check":"error";size:14;color:step.modelData.result?.ok?Theme.accent:Theme.red}
                            PanelText {id:title;x:34;y:10;width:parent.width-122;text:step.modelData.tool?.purpose||step.modelData.tool?.name||"Action";font.pixelSize:12;wrapMode:Text.WordWrap;elide:Text.ElideNone}
                            PanelText {anchors.right:parent.right;anchors.rightMargin:12;anchors.verticalCenter:parent.verticalCenter;width:76;horizontalAlignment:Text.AlignRight;elide:Text.ElideRight;text:step.modelData.result?.status|| (step.modelData.result?.ok?"Observed":"Failed");font.pixelSize:10;color:Theme.subtext}
                        }
                    }
                    LumaSection {width:parent.width;expanded:step.open;animate:root.animate
                        Column {width:parent.width;spacing:6
                            Flickable {width:parent.width;height:Math.min(160,detailText.implicitHeight+20);contentWidth:width;contentHeight:detailText.implicitHeight+20;clip:true;boundsBehavior:Flickable.StopAtBounds
                                TextEdit {id:detailText;x:12;y:10;width:parent.width-24;text:step.detail||"No additional output";readOnly:true;selectByMouse:true;wrapMode:TextEdit.WrapAnywhere;textFormat:TextEdit.PlainText;color:Theme.subtext;font.family:Tokens.font;font.pixelSize:11;renderType:Tokens.textRenderType;selectionColor:Theme.accent;selectedTextColor:Theme.accentText}
                                ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
                            }
                            Row {spacing:4
                                IconButton {icon:"content_copy";size:13;label:"Copy action details";onClicked:Quickshell.clipboardText=step.detail}
                                IconButton {visible:!!step.modelData.result?.path;icon:"open_in_new";size:13;label:"Open file";onClicked:Quickshell.execDetached(["xdg-open",step.modelData.result.path])}
                            }
                        }
                    }
                }
            }
        }
    }
}
