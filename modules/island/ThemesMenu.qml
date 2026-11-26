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
    objectName: "themesPanel"
    property string selectedId: ""
    property bool requestedBundle: false
    property bool ready: false
    property bool followSelection: false
    readonly property int compactHeight: 47
    readonly property int expandedHeight: 108
    readonly property int rowGap: 5
    readonly property int rowInset: 20
    readonly property real compactTitleScale: .74
    readonly property var bundles: SystemInfo.wallpapers.filter(wall => wall.theme && !!Theme.palettes[wall.theme.palette]).map(wall => ({
        id: wall.theme.id, label: wall.theme.label, palette: wall.theme.palette, path: wall.path,
        image: wall.thumbnailUrl || wall.url, kind: "Wallpaper and palette"
    }))
    readonly property var choices: {
        const wallpaper = {id: "wallpaper", palette: "wallpaper", path: "", image: "",
            label: Theme.paletteLabel("wallpaper"), kind: "Default. Follows your wallpaper"};
        const saved = Theme.customThemes.map(theme => ({
            id: theme.id, palette: theme.id, path: "", image: "", label: theme.label, kind: "Saved theme"
        }));
        const presets = Object.keys(Theme.palettes).filter(name => name !== "wallpaper").map(name => ({
            id: name, palette: name, path: "", image: "",
            label: Theme.paletteLabel(name), kind: "Palette only. Keeps your wallpaper"
        }));
        const query = search.text.trim().toLowerCase();
        const byLabel = (a, b) => a.label.localeCompare(b.label);
        const entries = [wallpaper].concat(saved.sort(byLabel), bundles.concat(presets).sort(byLabel));
        return entries.filter(entry => (entry.label + " " + entry.kind).toLowerCase().includes(query));
    }
    readonly property string activeId: bundles.find(bundle => bundle.palette === Theme.paletteName && bundle.path === SystemInfo.wallpaper)?.id ?? Theme.paletteName
    readonly property int selectedIndex: {
        const index = choices.findIndex(choice => choice.id === selectedId);
        return index >= 0 ? index : choices.length ? Math.max(0, choices.findIndex(choice => choice.id === activeId)) : -1;
    }
    readonly property var selected: choices[selectedIndex] ?? null

    function mix(from, to, progress): real { return from + (to - from) * progress; }

    function syncRows(): void {
        ModelDiff.reconcile(themeModel, choices.map(choice => ({
            themeId: choice.id, title: choice.label, paletteName: choice.palette,
            artwork: choice.image, description: choice.kind
        })), "themeId");
        Qt.callLater(root.reveal, false);
    }
    function reveal(animated: bool): void {
        const top = Math.max(0, selectedIndex) * (compactHeight + rowGap);
        const fullHeight = choices.length ? (choices.length - 1) * (compactHeight + rowGap) + expandedHeight : 0;
        const maxY = Math.max(0, fullHeight - list.height);
        const nextY = Math.max(0, Math.min(maxY, top + (expandedHeight - list.height) / 2));
        followSelection = true;
        if (animated) {
            if (!scroll.running) scroll.reset(list.contentY);
            scroll.targetValue = nextY;
            scroll.start();
        } else {
            scroll.targetValue = nextY;
            scroll.reset(nextY);
            applyScroll();
        }
    }
    function applyScroll(): void {
        if (followSelection && !list.moving)
            list.contentY = Math.max(0, Math.min(scroll.value, list.contentHeight - list.height));
    }
    function step(delta: int): void {
        if (!choices.length) return;
        const index = Math.max(0, Math.min(choices.length - 1, selectedIndex + delta));
        selectedId = choices[index].id;
        list.cancelFlick();
        reveal(true);
    }
    function apply(choice): void {
        if (!choice || SystemInfo.busy) return;
        selectedId = choice.id;
        if (choice.id === "wallpaper") { Theme.useWallpaperColors(); return; }
        if (choice.id === activeId) return;
        requestedBundle = !!choice.path;
        if (requestedBundle) SystemInfo.applyWallpaper(choice.path, choice.palette);
        else Theme.setPalette(choice.palette);
    }
    function diagnostics(): var {
        return {selected: selectedIndex, scrollX: list.contentX, scrollY: list.contentY,
                activeFocus: search.editor.activeFocus, count: choices.length, query: search.text};
    }

    onActiveFocusChanged: if (activeFocus) search.editor.forceActiveFocus()
    onChoicesChanged: if (ready) syncRows()
    onActiveIdChanged: if (ready && !selectedId) Qt.callLater(root.reveal, false)
    Component.onCompleted: {
        ready = true;
        syncRows();
        SystemInfo.scanWallpapers();
    }
    ListModel { id: themeModel }
    FrameSpring {
        id: scroll
        owner: list
        positionTolerance: .3
        onValueChanged: root.applyScroll()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 9
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            PickerSearch {
                id: search
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                textSize: 15
                placeholderText: "Search themes…"
                editor.objectName: "themeSearch"
                onTextChanged: {
                    root.selectedId = "";
                    root.reveal(false);
                }
                onStep: delta => root.step(delta)
                onSubmit: root.apply(root.selected)
            }
            ActivityPulse {
                running: root.requestedBundle && SystemInfo.busy
                visible: running
            }
            PanelText {
                objectName: "themePosition"
                Layout.preferredWidth: 44
                Layout.preferredHeight: 22
                visible: !!root.selected
                text: (root.selectedIndex + 1) + "/" + root.choices.length
                color: Theme.subtext
                font.pixelSize: Tokens.textSize(12)
                font.features: ({tnum: 1})
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
            }
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.withAlpha(Theme.text, .08) }

        Flickable {
            id: list
            objectName: "themeList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: rows.height
            flickableDirection: Flickable.VerticalFlick
            boundsBehavior: Flickable.StopAtBounds
            clip: true
            onMovementStarted: {
                root.followSelection = false;
                scroll.reset(scroll.value);
            }
            onHeightChanged: if (root.ready) Qt.callLater(root.reveal, false)
            onContentHeightChanged: if (root.followSelection) Qt.callLater(root.applyScroll)

            HoverHandler {
                id: pointer
                cursorShape: Qt.PointingHandCursor
                blocking: false
                property point lastPosition: Qt.point(-1, -1)
                onPointChanged: {
                    const position = point.position;
                    if (position === lastPosition) return;
                    lastPosition = position;
                    if (!hovered || list.moving || scroll.running) return;
                    const row = rows.childAt(position.x, position.y + list.contentY);
                    if (row?.themeId && row.themeId !== root.selected?.id) {
                        root.followSelection = false;
                        root.selectedId = row.themeId;
                    }
                }
            }
            Column {
                id: rows
                width: list.width
                spacing: root.rowGap

                Repeater {
                    model: themeModel
                    AbstractButton {
                        id: row
                        required property string themeId
                        required property string title
                        required property string paletteName
                        required property string artwork
                        required property string description
                        objectName: "themeRow-" + themeId
                        readonly property var scheme: Theme.resolvePalette(paletteName)
                        readonly property color previewSurface: Qt.tint(Theme.surfaceSolid, Theme.withAlpha(scheme.accent, .11))
                        readonly property bool current: root.selected?.id === themeId
                        readonly property bool applied: root.activeId === themeId
                        readonly property real expansion: Math.max(0, Math.min(1, motion.value))
                        readonly property bool showArtwork: !!artwork && width >= 225
                        width: rows.width
                        height: root.mix(root.compactHeight, root.expandedHeight, expansion)
                        padding: 0
                        text: title
                        focusPolicy: Qt.NoFocus
                        Accessible.name: text
                        Accessible.description: description + (applied ? ". Applied" : ". Apply theme")
                        onClicked: root.apply(root.choices.find(choice => choice.id === themeId))

                        FrameSpring {
                            id: motion
                            owner: row
                            targetValue: row.current ? 1 : 0
                            minimumValue: 0
                            maximumValue: 1
                            positionTolerance: .001
                        }

                        background: Rectangle {
                            radius: root.mix(Tokens.fieldRadius, Tokens.surfaceRadius + 4, row.expansion)
                            color: Theme.withAlpha(row.previewSurface, row.expansion)
                            ClippingRectangle {
                                anchors.fill: parent
                                radius: parent.radius
                                color: "transparent"
                                opacity: row.expansion * row.expansion
                                visible: row.showArtwork && opacity > 0
                                Image {
                                    width: parent.width * .53
                                    height: root.expandedHeight
                                    x: parent.width - width + root.rowInset * (1 - row.expansion)
                                    y: (row.height - height) / 2
                                    source: row.showArtwork ? row.artwork : ""
                                    opacity: status === Image.Ready ? 1 : 0
                                    asynchronous: true
                                    fillMode: Image.PreserveAspectCrop
                                    sourceSize: Qt.size(400, 260)
                                    Behavior on opacity { NumberAnimation { duration: Tokens.animFast } }
                                    Rectangle {
                                        anchors.fill: parent
                                        gradient: Gradient {
                                            orientation: Gradient.Horizontal
                                            GradientStop { position: 0; color: row.previewSurface }
                                            GradientStop { position: .7; color: Theme.withAlpha(row.previewSurface, .12) }
                                            GradientStop { position: 1; color: Theme.withAlpha(row.previewSurface, 0) }
                                        }
                                    }
                                }
                            }
                            Rectangle {
                                anchors.fill: parent
                                radius: parent.radius
                                color: Theme.text
                                opacity: row.pressed ? .06 : 0
                                Behavior on opacity { NumberAnimation { duration: Tokens.animFast } }
                            }
                        }
                        contentItem: Item {
                            Rectangle {
                                id: marker
                                x: root.rowInset
                                y: titleText.y + (titleText.height * titleText.scale - height) / 2
                                width: 7
                                height: width
                                radius: width / 2
                                color: row.scheme.accent
                                opacity: row.applied ? 1 : 0
                                Behavior on opacity { NumberAnimation { duration: Tokens.animFast } }
                            }
                            PanelText {
                                id: titleText
                                x: root.rowInset + 14 * marker.opacity
                                y: root.mix((root.compactHeight - height * scale) / 2, 22, row.expansion)
                                width: Math.max(0, root.mix((swatches.restX - x - 12) / root.compactTitleScale,
                                    row.width * (row.showArtwork ? .49 : .95) - x, row.expansion))
                                text: row.text
                                font.pixelSize: 22
                                font.weight: Font.DemiBold
                                transformOrigin: Item.TopLeft
                                scale: root.mix(root.compactTitleScale, 1, row.expansion)
                                color: Theme.withAlpha(Theme.text, .84 + .16 * row.expansion)
                            }
                            PaletteSwatches {
                                id: swatches
                                objectName: "themeSwatches"
                                readonly property real restX: Math.max(root.rowInset, row.width - implicitWidth - root.rowInset)
                                scheme: row.scheme
                                diameter: root.mix(8, 12, row.expansion)
                                spacing: root.mix(4, 7, row.expansion)
                                x: root.mix(restX, root.rowInset, row.expansion)
                                y: root.mix((root.compactHeight - height) / 2, 65, row.expansion)
                            }
                        }
                    }
                }
            }
            PanelText { parent: list; anchors.centerIn: parent; visible: !root.selected; text: "No themes found"; color: Theme.subtext }
            ViewportFade { view: list; edge: 12 }
        }
        PanelText {
            Layout.fillWidth: true
            visible: root.requestedBundle && !!SystemInfo.error
            text: SystemInfo.error
            color: Theme.red
            font.pixelSize: Tokens.captionSize
        }
    }
}
