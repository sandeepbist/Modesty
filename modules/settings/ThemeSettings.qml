import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.components
import qs.services
import qs.theme
import "../../theme/Palette.js" as Palette

ColumnLayout {
    id: root
    spacing: 12

    property var draft: null
    property var sample: null
    property bool confirmingDelete: false
    property string error: ""
    readonly property bool canGenerate: !!SystemInfo.wallpaper && SystemInfo.matugenAvailable
    readonly property var sources: [{value: "wallpaper", label: "Current wallpaper colors"}]
        .concat(Object.keys(Theme.palettes).filter(name => name !== "wallpaper").map(name => ({
            value: name, label: Theme.paletteLabel(name) + " · preset"
        })), Palette.schemeOptions.map(option => ({
            value: option.value, label: option.label + " · generate from wallpaper"
        })))
    readonly property var saved: Theme.customThemes.slice().sort((a, b) => a.label.localeCompare(b.label))
    readonly property bool needsSample: Theme.snapshotSource(sourcePicker.currentValue)
    readonly property var previewScheme: needsSample
        ? sample && Palette.refine(sample[Theme.mode])
        : sourcePicker.currentValue ? Theme.resolvePalette(sourcePicker.currentValue) : null

    function reveal(key) { return newTheme.enabled ? newTheme : loadStatus; }
    function begin(theme): void {
        draft = theme ?? {id: "", label: "", source: "wallpaper", variants: null};
        nameField.text = draft.label;
        sourcePicker.currentIndex = sourcePicker.indexOfValue(draft.source);
        sample = draft.variants;
        error = "";
        confirmingDelete = false;
        nameField.forceActiveFocus();
        nameField.selectAll();
    }
    function closeEditor(): void {
        draft = null;
        sample = null;
        error = "";
        confirmingDelete = false;
        Qt.callLater(() => newTheme.forceActiveFocus());
    }
    function save(): void {
        if (!draft || confirmingDelete || generation.running) return;
        error = Theme.themeNameError(draft.id, nameField.text);
        if (error) return;
        if (needsSample && !sample) { generate(true); return; }
        commit();
    }
    function commit(): void {
        error = Theme.saveCustomTheme(draft.id, nameField.text, sourcePicker.currentValue, needsSample ? sample : null);
        if (!error) closeEditor();
    }
    function generate(saveAfter: bool): void {
        if (!canGenerate || generation.running) return;
        const request = SystemInfo.paletteRequest(SystemInfo.wallpaper);
        const source = sourcePicker.currentValue;
        if (source !== "wallpaper") {
            request.automatic = false;
            request.scheme = source;
        }
        error = "";
        generation.saveAfter = saveAfter;
        generation.command = ["python3", SystemInfo.script, "palette", JSON.stringify(request)];
        generation.running = true;
    }

    Process {
        id: generation
        property bool saveAfter: false
        stdout: StdioCollector {
            onStreamFinished: {
                let result;
                try { result = JSON.parse(text); }
                catch (e) { root.error = "Couldn't read the generated colors."; return; }
                if (!result?.ok || !Theme.validVariants(result.palette)) {
                    root.error = result?.error || "Couldn't generate colors.";
                    return;
                }
                if (result.path !== SystemInfo.wallpaper) {
                    root.error = "The wallpaper changed. Generate colors again.";
                    return;
                }
                root.sample = result.palette;
                if (generation.saveAfter) root.commit();
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3
            PanelText { text: "Wallpaper colors"; font.pixelSize: Tokens.textSize(13); font.weight: Font.DemiBold }
            PanelText {
                Layout.fillWidth: true
                text: "Default · follows the current wallpaper"
                font.pixelSize: Tokens.textSize(12)
                color: Theme.subtext
                wrapMode: Text.Wrap
            }
        }
        ActionButton {
            objectName: "use-wallpaper-colors"
            text: Theme.paletteName === "wallpaper" && Preferences.wallpaperColors ? "In use" : "Use"
            Accessible.name: text === "Use" ? "Use wallpaper colors" : "Wallpaper colors in use"
            enabled: text === "Use"
            onClicked: Theme.useWallpaperColors()
        }
    }
    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.withAlpha(Theme.text, .08) }
    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        PanelText {
            id: loadStatus
            Layout.fillWidth: true
            visible: text.length > 0
            text: Theme.appearanceLoadError || (!Theme.appearanceReady ? "Loading themes…" :
                root.saved.length ? "" : "Save a palette to reuse with any wallpaper.")
            color: Theme.appearanceLoadError ? Theme.red : Theme.subtext
            font.pixelSize: Tokens.textSize(12)
            wrapMode: Text.Wrap
        }
        Item { Layout.fillWidth: true; visible: !loadStatus.visible }
        ActionButton {
            id: newTheme
            objectName: "custom-new-theme"
            text: "New theme"
            primary: !root.draft
            enabled: Theme.appearanceReady && !generation.running
            onClicked: root.begin(null)
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        visible: !!root.draft
        enabled: !generation.running
        spacing: 8
        PanelText { text: root.draft?.id ? "Edit theme" : "Create theme"; font.weight: Font.DemiBold }
        EntryField {
            id: nameField
            objectName: "custom-theme-name"
            Layout.fillWidth: true
            placeholderText: "Theme name"
            Accessible.name: placeholderText
            onAccepted: root.save()
        }
        ComboBox {
            id: sourcePicker
            objectName: "custom-theme-source"
            Layout.fillWidth: true
            implicitHeight: 36
            leftPadding: 12
            rightPadding: 32
            model: root.sources
            textRole: "label"
            valueRole: "value"
            Accessible.name: "Palette source"
            onActivated: {
                root.sample = root.draft?.source === currentValue ? root.draft.variants : null;
                root.error = "";
            }
            contentItem: PanelText { text: sourcePicker.displayText; font.pixelSize: Tokens.textSize(12); verticalAlignment: Text.AlignVCenter }
            indicator: Icon {
                x: sourcePicker.width - width - 10
                y: (sourcePicker.height - height) / 2
                icon: sourcePicker.popup.visible ? "expand_less" : "expand_more"
                size: 15
                color: Theme.subtext
            }
            background: Rectangle {
                radius: 8
                color: Theme.withAlpha(Theme.text, .045)
                border.width: 1
                border.color: sourcePicker.activeFocus ? Theme.accent : Theme.withAlpha(Theme.text, .08)
            }
            delegate: ItemDelegate {
                required property var modelData
                required property int index
                width: options.width
                highlighted: sourcePicker.highlightedIndex === index
                Accessible.name: modelData.label
                contentItem: PanelText { text: modelData.label; font.pixelSize: Tokens.textSize(12); verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 6; color: parent.highlighted || parent.hovered ? Theme.accentLow : "transparent" }
            }
            popup: Popup {
                y: sourcePicker.height + 6
                width: sourcePicker.width
                padding: 6
                margins: 8
                implicitHeight: Math.min(260, options.contentHeight + 12)
                background: Rectangle {
                    radius: 10
                    color: Theme.surfaceSolid
                    border.width: 1
                    border.color: Theme.withAlpha(Theme.text, .14)
                }
                contentItem: ListView {
                    id: options
                    clip: true
                    model: sourcePicker.popup.visible ? sourcePicker.delegateModel : null
                    currentIndex: sourcePicker.highlightedIndex
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: SettingsScrollBar {}
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: root.needsSample || !!root.previewScheme
            spacing: 8
            PaletteSwatches { visible: !!root.previewScheme; scheme: root.previewScheme; diameter: 10 }
            PanelText {
                Layout.fillWidth: true
                text: generation.running ? "Generating colors…" : root.needsSample && !root.canGenerate && !root.sample
                    ? "A wallpaper and Matugen are needed to generate colors." : ""
                color: Theme.subtext
                font.pixelSize: Tokens.textSize(12)
                wrapMode: Text.Wrap
            }
            ActionButton {
                objectName: "custom-theme-preview"
                visible: root.needsSample && root.canGenerate
                text: root.sample ? "Refresh colors" : "Preview colors"
                onClicked: root.generate(false)
            }
        }
        PanelText {
            objectName: "custom-theme-error"
            Layout.fillWidth: true
            visible: !!root.error
            text: root.error
            wrapMode: Text.Wrap
            color: Theme.red
            font.pixelSize: Tokens.textSize(12)
        }
        RowLayout {
            Layout.fillWidth: true
            visible: !root.confirmingDelete
            spacing: 8
            ActionButton {
                objectName: "custom-theme-delete"
                visible: !!root.draft?.id
                text: "Delete…"
                onClicked: { root.confirmingDelete = true; keepTheme.forceActiveFocus(); }
            }
            Item { Layout.fillWidth: true }
            ActionButton { text: "Cancel"; onClicked: root.closeEditor() }
            ActionButton {
                objectName: "custom-theme-save"
                primary: true
                text: "Save theme"
                enabled: !!nameField.text.trim() && (!root.needsSample || !!root.sample || root.canGenerate)
                onClicked: root.save()
            }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: root.confirmingDelete
            spacing: 8
            PanelText {
                Layout.fillWidth: true
                text: "Delete “" + (root.draft?.label ?? "") + "”?"
                color: Theme.red
                wrapMode: Text.Wrap
            }
            ActionButton { id: keepTheme; text: "Keep"; onClicked: { root.confirmingDelete = false; nameField.forceActiveFocus(); } }
            ActionButton {
                objectName: "custom-theme-confirm-delete"
                text: "Delete theme"
                onClicked: { Theme.deleteCustomTheme(root.draft.id); root.closeEditor(); }
            }
        }
    }

    Repeater {
        model: root.saved
        RowLayout {
            required property var modelData
            readonly property bool applied: Theme.paletteName === modelData.id
            Layout.fillWidth: true
            spacing: 8
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                PanelText {
                    Layout.fillWidth: true
                    text: modelData.label
                    font.pixelSize: Tokens.textSize(13)
                    font.weight: Font.Medium
                }
                PaletteSwatches { scheme: Theme.resolvePalette(modelData.id) }
            }
            ActionButton {
                objectName: "use-" + modelData.id
                text: parent.applied ? "In use" : "Use"
                Accessible.name: parent.applied ? modelData.label + " in use" : "Use " + modelData.label
                enabled: !parent.applied
                onClicked: Theme.setPalette(modelData.id)
            }
            ActionButton {
                objectName: "edit-" + modelData.id
                text: "Edit"
                Accessible.name: "Edit " + modelData.label
                enabled: !generation.running
                onClicked: root.begin(modelData)
            }
        }
    }
}
