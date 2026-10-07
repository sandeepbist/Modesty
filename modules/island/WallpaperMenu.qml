import QtQuick
import QtQuick.Layouts
import Quickshell.Widgets
import qs.services
import qs.components
import qs.theme
FocusScope {
    id: root
    objectName: "wallpapersPanel"
    readonly property int selectedIndex: carousel.currentIndex
    function diagnostics(): var { return {selected:carousel.currentIndex,offset:carousel.offset,activeFocus:root.activeFocus,count:SystemInfo.wallpapers.length,previewColors:!!Theme.previewWallpaperVariants,accent:String(Theme.accent)}; }
    focus: true
    function apply(): void { const wall = SystemInfo.wallpapers[carousel.currentIndex]; if (wall) SystemInfo.applyWallpaper(wall.path); }
    function restoreSelection(): void {
        const index = Math.max(0, SystemInfo.wallpapers.findIndex(w => w.path === SystemInfo.wallpaper));
        if (carousel.currentIndex !== index) carousel.currentIndex = index;
    }
    Component.onCompleted: { SystemInfo.scanWallpapers(); restoreSelection(); }
    Connections { target: SystemInfo; function onWallpapersChanged() { root.restoreSelection(); } function onWallpaperChanged() { root.restoreSelection(); } }
    Connections { target: IslandState; function onMenuChanged() { if (IslandState.menu === "wallpapers") SystemInfo.scanWallpapers(); else SystemInfo.clearWallpaperPreview(); } }
    Component.onDestruction: SystemInfo.clearWallpaperPreview()
    Keys.onLeftPressed: carousel.decrementCurrentIndex()
    Keys.onRightPressed: carousel.incrementCurrentIndex()
    Keys.onReturnPressed: apply()
    Keys.onEnterPressed: apply()
    ColumnLayout {
        anchors.fill: parent; spacing: 14
        RowLayout {
            Layout.fillWidth:true;Layout.preferredHeight:32;spacing:8
            PanelText {Layout.fillWidth:true;Layout.preferredHeight:32;text:SystemInfo.wallpapers[carousel.currentIndex]?.name?.replace(/\.[^.]+$/,"").replace(/[-_]+/g," ")||"Wallpapers";font.pixelSize:14;font.weight:Font.Medium;verticalAlignment:Text.AlignVCenter}
            Item {
                implicitWidth:32;implicitHeight:32
                IconButton {anchors.centerIn:parent;visible:!SystemInfo.busy;icon:"check";size:16;label:"Use wallpaper";color:Theme.accent;enabled:!!SystemInfo.wallpapers[carousel.currentIndex]&&SystemInfo.wallpapers[carousel.currentIndex].path!==SystemInfo.wallpaper;onClicked:root.apply()}
                ActivityPulse {anchors.centerIn:parent;running:SystemInfo.busy;visible:running}
            }
            IconButton {icon:"palette";size:16;label:Preferences.wallpaperColors?"Wallpaper colors on":"Wallpaper colors off";color:Preferences.wallpaperColors?Theme.accent:Theme.subtext;enabled:SystemInfo.matugenAvailable;onClicked:Preferences.set("wallpaperColors",!Preferences.wallpaperColors)}
            IconButton {icon:"close";size:16;label:"Close wallpapers";color:Theme.subtext;onClicked:IslandState.closeMenu()}
        }
        PathView {
            id: carousel
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true
            model: SystemInfo.wallpapers
            pathItemCount: Math.min(5, count)
            cacheItemCount: 4
            preferredHighlightBegin: .5; preferredHighlightEnd: .5
            highlightRangeMode: PathView.StrictlyEnforceRange
            highlightMoveDuration: Math.min(Tokens.animMedium, 130)
            snapMode: PathView.SnapToItem
            currentIndex: Math.max(0, SystemInfo.wallpapers.findIndex(w => w.path === SystemInfo.wallpaper))
            onCurrentIndexChanged: {
                if (IslandState.menu === "wallpapers") {
                    const wall = SystemInfo.wallpapers[currentIndex];
                    if (wall) SystemInfo.previewWallpaper(wall.path);
                }
            }
            path: Path {
                startX: (carousel.width - carousel.pathItemCount * 192) / 2; startY: carousel.height / 2
                PathLine { x: (carousel.width + carousel.pathItemCount * 192) / 2; y: carousel.height / 2 }
            }
            delegate: Rectangle {
                id: card; required property var modelData; required property int index
                width: 176; height: Math.min(100,carousel.height-4); radius: 13
                color: Theme.surfaceSolid; border.width: 1.5; border.color: PathView.isCurrentItem ? Theme.accent : "transparent"
                opacity: PathView.isCurrentItem ? 1 : 0.82
                Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}
                Behavior on opacity { NumberAnimation { duration: Tokens.animMedium } }
                ClippingRectangle { anchors.fill: parent; anchors.margins: 3; radius: 10
                    Image { anchors.fill: parent; source: card.modelData.thumbnailUrl || card.modelData.url; asynchronous: true; cache: true; sourceSize.width: 360; sourceSize.height: 220; fillMode: Image.PreserveAspectCrop }
                }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: carousel.currentIndex = card.index; onDoubleClicked: { carousel.currentIndex = card.index; root.apply(); } }
            }
            WheelHandler { onWheel: event => { if (event.angleDelta.y < 0) carousel.incrementCurrentIndex(); else carousel.decrementCurrentIndex(); } }
            Rectangle {
                anchors.left:parent.left;anchors.top:parent.top;anchors.bottom:parent.bottom;width:16;z:2
                gradient:Gradient {orientation:Gradient.Horizontal;GradientStop {position:0;color:Theme.bgSolid}GradientStop {position:1;color:Theme.withAlpha(Theme.bgSolid,0)}}
            }
            Rectangle {
                anchors.right:parent.right;anchors.top:parent.top;anchors.bottom:parent.bottom;width:16;z:2
                gradient:Gradient {orientation:Gradient.Horizontal;GradientStop {position:0;color:Theme.withAlpha(Theme.bgSolid,0)}GradientStop {position:1;color:Theme.bgSolid}}
            }
            PanelText { anchors.centerIn: parent; visible: !SystemInfo.wallpapers.length; text: "Add images to ~/Pictures/Wallpapers"; color: Theme.subtext }
        }
        RowLayout {
            Layout.fillWidth:true;visible:!!SystemInfo.error||!!SystemInfo.wallpaperWarning;spacing:8
            PanelText {Layout.fillWidth:true;text:SystemInfo.error||SystemInfo.wallpaperWarning;color:SystemInfo.error?Theme.red:Theme.subtext;font.pixelSize:12}
        }
    }
}
