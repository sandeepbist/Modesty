import QtQuick
import QtQuick.Layouts
import qs.services
import qs.components
import qs.theme
import "../../services/ModelDiff.js" as ModelDiff
FocusScope {
    id: root
    objectName: "themesPanel"
    readonly property int selectedIndex: carousel.currentIndex
    property string query: ""
    readonly property var names: ["midnight", "e-ink", "everblush", "everforest", "gruvbox", "nord", "rose", "dracula", "wallpaper"].filter(n => n.includes(query.toLowerCase()))
    ListModel {id:themeModel}
    function syncThemes(): void {ModelDiff.reconcile(themeModel,names.map(name=>({themeName:name})),"themeName");carousel.currentIndex=Math.max(0,Math.min(carousel.currentIndex,names.length-1));}
    onNamesChanged:Qt.callLater(syncThemes)
    Component.onCompleted:syncThemes()
    function apply(): void { if (names.length) Theme.setPalette(names[carousel.currentIndex]); }
    function diagnostics(): var { return {selected:carousel.currentIndex,scrollX:carousel.contentX,activeFocus:search.activeFocus,count:names.length,query}; }
    onActiveFocusChanged: if (activeFocus) search.forceActiveFocus()
    Keys.onLeftPressed: carousel.decrementCurrentIndex()
    Keys.onRightPressed: carousel.incrementCurrentIndex()
    Keys.onReturnPressed: apply()
    Keys.onEnterPressed: apply()
    ColumnLayout {
        anchors.fill: parent; spacing: 12
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 32; spacing: 10
            Icon { icon: "search"; size: 14; color: Theme.subtext }
            TextInput {
                id: search; objectName: "themeSearch"; Layout.fillWidth: true; color: Theme.text; font.family: Tokens.font; font.pixelSize: 13; selectByMouse: true; clip: true; focus: true
                onTextChanged: root.query = text
                Keys.onLeftPressed: carousel.decrementCurrentIndex()
                Keys.onRightPressed: carousel.incrementCurrentIndex()
                Keys.onReturnPressed: root.apply()
                Keys.onEnterPressed: root.apply()
                PanelText { anchors.fill: parent; visible: !search.text; text: "Themes…"; color: Theme.subtext; font.pixelSize: 13 }
            }
            IconButton { icon:"check"; label:"Apply theme"; size:16; color:Theme.accent; enabled:!!root.names.length&&root.names[carousel.currentIndex]!==Theme.paletteName; onClicked:root.apply() }
            IconButton { icon:Theme.light?"dark_mode":"light_mode";label:Theme.light?"Switch to dark":"Switch to light";size:16;onClicked:Theme.toggleMode() }
            IconButton { icon:"close"; label:"Close themes"; size:16; color:Theme.subtext; onClicked:IslandState.closeMenu() }
        }
        ListView {
            id: carousel
            Layout.fillWidth: true; Layout.fillHeight: true
            keyNavigationEnabled:false
            orientation: ListView.Horizontal; spacing: 8; clip: true
            model: themeModel
            add:Transition {NumberAnimation {property:"opacity";from:0;to:1;duration:Tokens.animFast}}
            displaced:Transition {NumberAnimation {properties:"x,y";duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
            preferredHighlightBegin: 0; preferredHighlightEnd: width - 142
            highlightRangeMode: ListView.ApplyRange
            highlightMoveVelocity:-1; highlightMoveDuration: Tokens.animMedium
            snapMode: ListView.SnapToItem
            currentIndex: Math.max(0, root.names.indexOf(Theme.paletteName))
            delegate: Item {
                id: card; required property string themeName; required property int index
                readonly property var palette: Theme.resolvePalette(themeName)
                width: 142; height: carousel.height
                Rectangle {
                    id: thumbnail
                    width: parent.width; height: parent.height - 29; radius: 13
                    color: card.palette.bgSolid
                    border.width: 1.5; border.color: card.ListView.isCurrentItem ? Theme.accent : Theme.withAlpha(Theme.text,.08)
                    Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}
                    Rectangle {
                        x:16;y:17;width:parent.width-32;height:parent.height-34;radius:8
                        color:card.palette.surfaceSolid
                        Rectangle {x:10;y:12;width:parent.width*.5;height:3;radius:1.5;color:card.palette.text}
                        Rectangle {x:10;y:22;width:parent.width*.68;height:3;radius:1.5;color:card.palette.subtext}
                        Rectangle {x:10;y:parent.height-15;width:parent.width*.38;height:5;radius:2.5;color:card.palette.accent}
                        Rectangle {anchors.right:parent.right;anchors.bottom:parent.bottom;anchors.margins:10;width:12;height:12;radius:6;color:card.palette.accent}
                    }
                    Rectangle {anchors.fill:parent;radius:parent.radius;color:Theme.withAlpha(card.palette.text,hover.hovered?.04:0);Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                }
                RowLayout {
                    x:3;y:thumbnail.height+9;width:parent.width-6;spacing:6
                    PanelText {Layout.fillWidth:true;text:card.themeName==="wallpaper"?"Wallpaper":card.themeName==="e-ink"?"E-Ink":card.themeName.charAt(0).toUpperCase()+card.themeName.slice(1);color:card.ListView.isCurrentItem?Theme.text:Theme.subtext;font.pixelSize:12;font.weight:Font.Medium;Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                    Icon {visible:Theme.paletteName===card.themeName;icon:"check";size:12;color:Theme.accent}
                }
                HoverHandler {id:hover;cursorShape:Qt.PointingHandCursor;blocking:false}
                MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:carousel.currentIndex=card.index;onDoubleClicked:{carousel.currentIndex=card.index;root.apply();}}
            }
            PanelText {parent:carousel;anchors.centerIn: parent;width:Math.max(0,parent.width-32);horizontalAlignment:Text.AlignHCenter;visible: !root.names.length; text: "No themes found"; color: Theme.subtext }
            WheelHandler { onWheel: event => { if (event.angleDelta.y < 0) carousel.incrementCurrentIndex(); else carousel.decrementCurrentIndex(); } }
            ViewportFade {view:carousel;horizontal:true;edge:16}
        }

    }
}
