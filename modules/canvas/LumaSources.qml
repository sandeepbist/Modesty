import QtQuick
import QtQuick.Controls
import qs.components
import qs.theme

// A citation unfolds where it was selected; the original URL remains explicit.
Item {
    id:root
    property var sources:[]
    property bool animate:true
    property bool interactive:true
    property int selected:-1
    readonly property var source:sources[selected]??null
    readonly property real naturalHeight:links.height+(source?peek.naturalHeight+10:0)
    implicitHeight:naturalHeight;height:links.height+(peek.visible?peek.height+10:0)
    signal opened(string url)
    signal expanded()
    onSourcesChanged:selected=-1
    Flow {
        id:links;width:parent.width;spacing:6
        Repeater {model:root.sources
            AbstractButton {
                id:link;required property var modelData;required property int index
                readonly property string host:modelData.publisher||modelData.host||modelData.url.replace(/^https?:\/\//,"").split("/")[0].replace(/^www\./,"")
                implicitWidth:Math.min(root.width,Math.min(180,label.implicitWidth+24));height:28
                hoverEnabled:true;enabled:root.interactive;focusPolicy:Qt.NoFocus
                Accessible.name:"Preview source: "+modelData.title
                onClicked:{root.selected=root.selected===index?-1:index;if(root.selected>=0)root.expanded();}
                scale:link.pressed?.97:1
                Behavior on scale {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                background:Rectangle {radius:9;color:link.hovered?Theme.withAlpha(Theme.text,.04):"transparent";border.width:1;border.color:Theme.withAlpha(root.selected===link.index?Theme.accent:Theme.text,root.selected===link.index?.35:.09);Behavior on color {ColorAnimation {duration:Tokens.animFast}}Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}}
                contentItem:PanelText {id:label;text:link.host;font.pixelSize:11;color:root.selected===link.index?Theme.accent:Theme.subtext;leftPadding:12;rightPadding:12;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter}
            }
        }
    }
    LumaSection {
        id:peek;y:links.height+10;width:parent.width;expanded:!!root.source;animate:root.animate
        property var held:null
        onExpandedChanged:if(expanded)held=root.source
        Connections {target:root;function onSelectedChanged(){if(root.source)peek.held=root.source;}}
        Rectangle {
            width:parent.width;height:body.implicitHeight+32;radius:Tokens.surfaceRadius
            color:Theme.withAlpha(Theme.surfaceSolid,.65);border.width:1;border.color:Theme.withAlpha(Theme.text,Tokens.borderAlpha)
            SurfaceLighting {anchors.fill:parent;radius:parent.radius;focused:true;interactive:false}
            Column {
                id:body;x:16;y:16;width:parent.width-32;spacing:10
                PanelText {width:parent.width;text:peek.held?.title??"";font.pixelSize:13;font.weight:Font.DemiBold;wrapMode:Text.WordWrap;elide:Text.ElideNone}
                PanelText {visible:!!peek.held?.published;text:peek.held?.published?Qt.formatDateTime(new Date(peek.held.published),"d MMM yyyy")+(peek.held.headlineOnly?" · Headline evidence":""):"";font.pixelSize:11;color:Theme.subtext}
                PanelText {width:parent.width;visible:!!peek.held?.snippet;text:peek.held?.snippet??"";font.pixelSize:12;lineHeight:Tokens.readingLeading;wrapMode:Text.WordWrap;elide:Text.ElideNone;color:Theme.subtext}
                ActionButton {text:"Open original ↗";implicitHeight:28;enabled:root.interactive;onClicked:if(peek.held?.url)root.opened(peek.held.url)}
            }
        }
    }
}
