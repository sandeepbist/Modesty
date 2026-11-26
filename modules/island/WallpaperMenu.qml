import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Widgets
import qs.services
import qs.components
import qs.theme
import "../../services/ModelDiff.js" as ModelDiff

FocusScope {
    id: root
    objectName: "wallpapersPanel"
    property real carouselLayoutWidth: width
    readonly property var matches: {
        const query = search.text.trim().toLowerCase();
        return SystemInfo.wallpapers.filter(wall => (wall.name + " " + (wall.theme?.label ?? "")).toLowerCase().includes(query));
    }
    readonly property int selectedIndex: !carousel.count ? -1 : travel.running
        ? wrapIndex(-travel.targetValue) : carousel.currentIndex
    readonly property var selected: matches[selectedIndex] ?? null
    property bool updating: false
    property bool ready: false
    property bool requestedApply: false

    function wrapIndex(index): int {
        return ((index % carousel.count) + carousel.count) % carousel.count;
    }

    function syncSelection(): void {
        const chosen = wallModel.get(selectedIndex)?.path || SystemInfo.wallpaper;
        updating = true;
        travel.reset(carousel.offset);
        ModelDiff.reconcile(wallModel, matches.map(wall => ({
            path: wall.path, name: wall.name, thumbnail: wall.thumbnailUrl || wall.url
        })), "path");
        const index = matches.findIndex(wall => wall.path === chosen);
        carousel.currentIndex = index >= 0 ? index : Math.max(0, matches.findIndex(wall => wall.path === SystemInfo.wallpaper));
        updating = false;
        updatePreview();
    }
    function updatePreview(): void {
        if (!ready || updating || IslandState.menu !== "wallpapers") return;
        const path = Preferences.wallpaperLivePreview ? selected?.path : "";
        if (!path || path === SystemInfo.wallpaper) {
            if (SystemInfo.previewWallpaperPath) SystemInfo.clearWallpaperPreview();
        } else if (!travel.running && !carousel.moving && path !== SystemInfo.previewWallpaperPath)
            SystemInfo.previewWallpaper(path);
    }
    function select(index: int, delta): void {
        if (index === selectedIndex || carousel.dragging) return;
        if (carousel.moving || Tokens.reducedMotion) {
            carousel.currentIndex = index;
            return;
        }
        const position = travel.running ? travel.value : carousel.offset;
        const destination = travel.running ? travel.targetValue : Math.round(position);
        if (!travel.running) travel.reset(position);
        travel.targetValue = delta ? destination - delta
            : carousel.count * Math.round((position + index) / carousel.count) - index;
        travel.start();
    }
    function step(delta: int): void {
        if (carousel.count > 1) select(wrapIndex(selectedIndex + delta), delta);
    }
    function apply(): void {
        if (!updating && selected && selected.path !== SystemInfo.wallpaper && !SystemInfo.busy) {
            requestedApply = true;
            SystemInfo.applyWallpaper(selected.path);
        }
    }
    function diagnostics(): var {
        return {selected: selectedIndex, offset: carousel.offset, activeFocus: search.editor.activeFocus, count: matches.length,
                query: search.text, previewColors: !!Theme.previewWallpaperVariants, accent: String(Theme.accent)};
    }

    onMatchesChanged: if (ready) syncSelection()
    onSelectedChanged: updatePreview()
    onActiveFocusChanged: if (activeFocus) search.editor.forceActiveFocus()
    Component.onCompleted: { ready = true; SystemInfo.scanWallpapers(); syncSelection(); }
    Component.onDestruction: SystemInfo.clearWallpaperPreview()
    Connections {
        target: IslandState
        function onMenuChanged() {
            if (IslandState.menu === "wallpapers") {
                root.requestedApply = false;
                SystemInfo.scanWallpapers();
                root.syncSelection();
            } else SystemInfo.clearWallpaperPreview();
        }
    }
    Connections { target: Preferences; function onWallpaperLivePreviewChanged() { root.updatePreview(); } }
    ListModel { id: wallModel }
    FrameSpring {
        id: travel
        owner: carousel
        positionTolerance: .002
        onValueChanged: if (root.ready && !root.updating && !carousel.dragging && carousel.count) carousel.offset = value
        onRunningChanged: if (!running) Qt.callLater(root.updatePreview)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 9
        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            PickerSearch {
                id: search
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                textSize: 15
                horizontal: true
                placeholderText: "Search wallpapers…"
                editor.objectName: "wallpaperSearch"
                onStep: delta => root.step(delta)
                onSubmit: root.apply()
            }
            PanelText {
                visible: !!text && parent.width >= 270
                text: root.selected?.theme?.label ?? ""
                Layout.maximumWidth: parent.width / 3
                color: Theme.subtext
                font.pixelSize: Tokens.captionSize
            }
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.withAlpha(Theme.text, .09) }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            PathView {
                id: carousel
                objectName: "wallpaperCarousel"
                anchors.fill: parent
                readonly property real cardWidth: Math.min(255, root.carouselLayoutWidth * .23)
                readonly property real gap: Math.min(18, cardWidth * .074)
                readonly property real nearScale: .70
                readonly property real farScale: .62
                readonly property int slots: Math.max(3, pathItemCount)
                readonly property real nearOpacity: .68
                readonly property real farOpacity: slots > 4 ? .44 : .2
                readonly property real sideStep: 1 / slots
                readonly property real farStep: Math.min(2 * sideStep, .48)
                readonly property real nearX: cardWidth * (1 + nearScale) / 2 + gap
                readonly property real farX: nearX + (cardWidth * (nearScale + farScale) / 2 + gap) * (farStep / sideStep - 1)
                readonly property real endX: farX + (cardWidth * farScale + gap) * (.5 - farStep) / sideStep
                model: wallModel
                pathItemCount: Math.min(7, count)
                cacheItemCount: 2
                clip: true
                preferredHighlightBegin: .5
                preferredHighlightEnd: .5
                highlightRangeMode: PathView.StrictlyEnforceRange
                highlightMoveDuration: root.updating ? 0 : Tokens.animMedium
                snapMode: PathView.SnapToItem
                interactive: count > 1
                onDragStarted: travel.reset(travel.value)
                onMovementEnded: root.updatePreview()
                path: Path {
                    startX: carousel.width / 2 - carousel.endX
                    startY: carousel.height / 2
                    PathAttribute { name: "sizeOnPath"; value: .6 }
                    PathAttribute { name: "visibilityOnPath"; value: 0 }
                    PathLine { x: carousel.width / 2 - carousel.farX; y: carousel.height / 2 }
                    PathAttribute { name: "sizeOnPath"; value: carousel.farScale }
                    PathAttribute { name: "visibilityOnPath"; value: carousel.farOpacity }
                    PathPercent { value: .5 - carousel.farStep }
                    PathLine { x: carousel.width / 2 - carousel.nearX; y: carousel.height / 2 }
                    PathAttribute { name: "sizeOnPath"; value: carousel.nearScale }
                    PathAttribute { name: "visibilityOnPath"; value: carousel.nearOpacity }
                    PathPercent { value: .5 - carousel.sideStep }
                    PathLine { x: carousel.width / 2; y: carousel.height / 2 }
                    PathAttribute { name: "sizeOnPath"; value: 1 }
                    PathAttribute { name: "visibilityOnPath"; value: 1 }
                    PathPercent { value: .5 }
                    PathLine { x: carousel.width / 2 + carousel.nearX; y: carousel.height / 2 }
                    PathAttribute { name: "sizeOnPath"; value: carousel.nearScale }
                    PathAttribute { name: "visibilityOnPath"; value: carousel.nearOpacity }
                    PathPercent { value: .5 + carousel.sideStep }
                    PathLine { x: carousel.width / 2 + carousel.farX; y: carousel.height / 2 }
                    PathAttribute { name: "sizeOnPath"; value: carousel.farScale }
                    PathAttribute { name: "visibilityOnPath"; value: carousel.farOpacity }
                    PathPercent { value: .5 + carousel.farStep }
                    PathLine { x: carousel.width / 2 + carousel.endX; y: carousel.height / 2 }
                    PathAttribute { name: "sizeOnPath"; value: .6 }
                    PathAttribute { name: "visibilityOnPath"; value: 0 }
                }
                delegate: AbstractButton {
                    id: card
                    required property int index
                    required property string name
                    required property string path
                    required property string thumbnail
                    width: carousel.cardWidth
                    height: Math.max(1, Math.min(carousel.height - 8, width * .61))
                    scale: PathView.sizeOnPath ?? carousel.farScale
                    opacity: PathView.visibilityOnPath ?? 0
                    visible: PathView.onPath && opacity > .01
                    z: scale
                    focusPolicy: Qt.NoFocus
                    text: name
                    Accessible.name: name
                    Accessible.description: path === SystemInfo.wallpaper ? "Applied wallpaper"
                        : index === root.selectedIndex ? "Use wallpaper" : "Preview wallpaper"
                    onClicked: {
                        if (index === root.selectedIndex && !travel.running && !carousel.moving) root.apply();
                        else root.select(index);
                    }
                    HoverHandler { cursorShape: Qt.PointingHandCursor }

                    background: ClippingRectangle {
                        id: artworkClip
                        radius: Math.min(Tokens.surfaceRadius + 7, width / 2, height / 2)
                        color: Theme.surfaceSolid
                        Image {
                            anchors.fill: parent
                            source: card.thumbnail
                            asynchronous: true
                            sourceSize: Qt.size(400, 260)
                            fillMode: Image.PreserveAspectCrop
                        }
                        Rectangle {
                            objectName: "wallpaperAppliedMarker"
                            visible: card.path === SystemInfo.wallpaper
                            anchors.top: parent.top
                            anchors.right: parent.right
                            anchors.margins: Math.max(width, artworkClip.radius * .48)
                            width: Math.min(7, artworkClip.height * .14)
                            height: width
                            radius: width / 2
                            color: Theme.text
                            border.width: 1
                            border.color: Theme.withAlpha(Theme.bgSolid, .7)
                            antialiasing: true
                        }
                    }
                    contentItem: Item {}
                }
                WheelHandler {
                    property real remainder: 0
                    onActiveChanged: if (!active) remainder = 0
                    onWheel: event => {
                        const delta = event.angleDelta.x || event.angleDelta.y;
                        if (!delta) return;
                        if (delta * remainder < 0) remainder = 0;
                        remainder += delta;
                        const steps = Math.trunc(remainder / 120);
                        if (steps) {
                            remainder -= 120 * steps;
                            root.step(-steps);
                        }
                    }
                }
            }
            Repeater {
                model: 2
                Rectangle {
                    id: edgeShade
                    required property int index
                    anchors.left: index === 0 ? parent.left : undefined
                    anchors.right: index === 1 ? parent.right : undefined
                    height: parent.height
                    width: Math.min(carousel.cardWidth * .84, parent.width * .19)
                    visible: carousel.count > 5
                    transform: Scale { origin.x: edgeShade.width / 2; xScale: edgeShade.index === 0 ? 1 : -1 }
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: Theme.bgSolid }
                        GradientStop { position: .38; color: Theme.withAlpha(Theme.bgSolid, .52) }
                        GradientStop { position: .55; color: Theme.withAlpha(Theme.bgSolid, .30) }
                        GradientStop { position: .74; color: Theme.withAlpha(Theme.bgSolid, .08) }
                        GradientStop { position: 1; color: Theme.withAlpha(Theme.bgSolid, 0) }
                    }
                }
            }
            PanelText {
                anchors.centerIn: parent
                width: parent.width
                visible: !carousel.count
                text: search.text.trim() ? "No wallpapers found" : "Add images to your Wallpapers folder"
                color: Theme.subtext
                horizontalAlignment: Text.AlignHCenter
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 26
            spacing: 8
            RollingText {
                objectName: "wallpaperName"
                Layout.fillWidth: true
                Layout.preferredHeight: 22
                text: (root.requestedApply ? SystemInfo.error || SystemInfo.wallpaperWarning : "") || root.selected?.name || ""
                color: root.requestedApply && SystemInfo.error ? Theme.red : Theme.subtext
                font.pixelSize: Tokens.captionSize
                font.weight: Font.Normal
                horizontalAlignment: Text.AlignLeft
            }
            ActivityPulse { running: SystemInfo.busy; visible: running }
            PanelText {
                objectName: "wallpaperPosition"
                visible: !!root.selected
                Layout.preferredWidth: 44
                Layout.preferredHeight: 22
                text: (root.selectedIndex + 1) + "/" + carousel.count
                color: Theme.subtext
                font.pixelSize: Tokens.captionSize
                font.features: ({tnum: 1})
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
