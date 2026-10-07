import QtQuick
import QtQuick.Controls
import qs.services
import qs.components
import qs.theme

// Validated semantic data, rendered with native text and a bounded comparison.
Item {
    id:root
    property string text:""
    property var presentation:({})
    property bool animate:true
    property bool interactive:true
    readonly property bool structured:["explanation","comparison","decision"].includes(presentation?.layout)&&!!presentation?.lead&&((presentation.sections?.length??0)>0||(presentation.rows?.length??0)>0)
    property int revision:0
    readonly property real naturalHeight:{
        const changed=revision;
        const heights=[lead.implicitHeight];
        for(let i=0;i<sections.count;i++){const section=sections.itemAt(i);if(section)heights.push(section.expanded?32+section.bodyHeight:24);}
        if(comparison.visible)heights.push(board.height+8);
        if(recommendation.visible)heights.push(recommendation.implicitHeight);
        return heights.reduce((total,h)=>total+h,0)+Math.max(0,heights.length-1)*content.spacing;
    }
    implicitHeight:naturalHeight;height:implicitHeight
    Column {
        id:content;width:root.width;spacing:18
        ReadingText {id:lead;width:parent.width;plainText:root.structured?root.presentation.lead:root.text;font.pixelSize:Preferences.lumaTextSize}
        Repeater {
            id:sections;model:root.structured?root.presentation.sections??[]:[]
            onItemAdded:root.revision++
            onItemRemoved:root.revision++
            Column {
                id:section;required property var modelData
                property bool expanded:true
                readonly property real bodyHeight:paragraph.implicitHeight
                width:content.width;spacing:8
                AbstractButton {
                    id:heading;width:parent.width;height:24;hoverEnabled:true;enabled:root.interactive
                    Accessible.name:section.modelData.title;Accessible.description:section.expanded?"Collapse section":"Expand section"
                    onClicked:section.expanded=!section.expanded
                    background:Rectangle {radius:6;color:heading.hovered?Theme.withAlpha(Theme.text,.025):"transparent";Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                    contentItem:Item {
                        PanelText {anchors.verticalCenter:parent.verticalCenter;width:parent.width-24;text:section.modelData.title;font.pixelSize:14;font.weight:Font.DemiBold;font.letterSpacing:Tokens.titleTracking}
                        Icon {anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter;icon:"expand_more";size:12;color:Theme.subtext;rotation:section.expanded?0:-90;Behavior on rotation {NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutQuint}}}
                    }
                }
                LumaSection {
                    width:parent.width;expanded:section.expanded;animate:root.animate
                    ReadingText {id:paragraph;width:parent.width;plainText:section.modelData.body;font.pixelSize:Preferences.lumaTextSize;color:Theme.subtext}
                }
            }
        }
        Flickable {
            id:comparison;width:parent.width;height:board.height+8
            visible:root.structured&&(root.presentation.rows?.length??0)>0
            contentWidth:board.width;contentHeight:board.height
            clip:true;boundsBehavior:Flickable.StopAtBounds;flickableDirection:Flickable.HorizontalFlick
            readonly property int count:root.presentation.columns?.length??0
            readonly property real columnWidth:Math.max(136,(width-96)/Math.max(1,count))
            ScrollBar.horizontal:ScrollBar {policy:ScrollBar.AsNeeded}
            Column {
                id:board;width:96+comparison.count*comparison.columnWidth;spacing:0
                Row {
                    x:96;spacing:0
                    Repeater {model:root.presentation.columns??[]
                        Item {required property string modelData;width:comparison.columnWidth;height:Math.max(40,caption.implicitHeight+20)
                            PanelText {id:caption;x:12;y:8;width:parent.width-24;text:parent.modelData;font.pixelSize:13;font.weight:Font.DemiBold;wrapMode:Text.WordWrap;elide:Text.ElideNone}
                        }
                    }
                }
                Repeater {model:root.presentation.rows??[]
                    Item {
                        id:criterion;required property var modelData;required property int index
                        width:board.width;height:Math.max(label.implicitHeight+24,cells.height)
                        Rectangle {anchors.fill:parent;color:criterion.index%2===0?Theme.withAlpha(Theme.text,.025):"transparent";radius:8}
                        PanelText {id:label;x:8;y:12;width:80;text:criterion.modelData.label;font.pixelSize:11;font.weight:Font.Medium;color:Theme.subtext;wrapMode:Text.WordWrap;elide:Text.ElideNone}
                        Row {id:cells;x:96;height:childrenRect.height
                            Repeater {model:criterion.modelData.values
                                Item {required property string modelData;width:comparison.columnWidth;height:value.implicitHeight+24
                                    ReadingText {id:value;x:12;y:12;width:parent.width-24;plainText:parent.modelData;font.pixelSize:12}
                                }
                            }
                        }
                        Rectangle {y:parent.height-1;width:parent.width;height:1;color:Theme.withAlpha(Theme.text,.055)}
                    }
                }
            }
        }
        Column {
            id:recommendation;width:parent.width;spacing:8;visible:root.structured&&!!root.presentation.recommendation
            Rectangle {width:30;height:2;radius:1;color:Theme.accent}
            ReadingText {width:parent.width;plainText:root.presentation.recommendation??"";font.pixelSize:Preferences.lumaTextSize}
        }
    }
    component ReadingText:LumaRichText {interactive:root.interactive}
}
