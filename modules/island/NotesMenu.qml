import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.services
import qs.theme
import qs.components

FocusScope {
    id: root
    objectName: "notesPanel"
    visible: !Session.isLocked()
    readonly property bool interactive: enabled && visible && !Session.isLocked()
    readonly property real viewportHeight:Math.min(height,parent?.viewportHeight??height)
    readonly property bool shortViewport:viewportHeight<240
    readonly property bool compact: width + Preferences.innerPadding * 2 < 580
    readonly property bool listVisible: Notes.libraryOpen && (!compact || !showEditor)
    readonly property bool editorVisible: !Notes.libraryOpen || !compact || showEditor
    property bool showEditor: false
    property bool syncing: false
    property bool initialized: false
    property string category: "active"
    property string query: ""
    property string deleteId: ""
    property string copied: ""
    readonly property var active: Notes.items.find(note => note.id === Notes.activeId) || null
    property var libraryOrder: []
    readonly property var results: {
        const values = Notes.search(query, category);
        if (!bodyField.activeFocus && !titleField.activeFocus) return values;
        return values.sort((a, b) => {
            const first = libraryOrder.indexOf(a.id), second = libraryOrder.indexOf(b.id);
            return (first < 0 ? values.length : first) - (second < 0 ? values.length : second);
        });
    }
    readonly property bool editable: Notes.loaded && (!active || active.status !== "trash")
    readonly property Item popupInputRegion: overflow.visible && interactive ? overflow.contentItem.parent : null
    property string editorId: ""

    function libraryTitle(note): string {
        if (note.title) return note.title;
        const body = Notes.read(note.id).note?.body || "";
        return body.split(/\r?\n/).find(line => !!line.trim())?.trim().slice(0, 90) || "Untitled note";
    }
    function libraryPreview(note): string {
        if (note.title) return note.preview || "Empty note";
        const lines = (Notes.read(note.id).note?.body || "").split(/\r?\n/).filter(line => !!line.trim());
        return lines.slice(1).join(" ").trim() || "";
    }
    function markedText(text: string): string {
        const escape = value => value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        const match = query.trim(), index = text.toLocaleLowerCase().indexOf(match.toLocaleLowerCase());
        if (!match || index < 0) return escape(text);
        return escape(text.slice(0, index)) + '<font color="' + Theme.accent + '"><b>' + escape(text.slice(index, index + match.length)) + '</b></font>' + escape(text.slice(index + match.length));
    }
    function refreshOrder(): void { libraryOrder = Notes.search("", category).map(note => note.id); }
    function talk(): void {
        if (!interactive || Preferences.preview || !Preferences.lumaVoice || Luma.busy) return;
        remember(); Notes.flush("voice"); Voice.begin();
    }
    function insertText(text: string): void {
        if (!interactive || !editable || !editorVisible) return;
        bodyField.insert(bodyField.cursorPosition, text); focusEditor();
    }

    function remember(): void {
        if (!initialized || !interactive || syncing || !Notes.loaded) return;
        Notes.edit({title: titleField.text, body: bodyField.text}, bodyField.cursorPosition, bodyScroll.contentY);
    }
    function syncDraft(): void {
        if (!Notes.loaded) return;
        const draft = Notes.draft;
        if (!draft) return;
        const changedNote = editorId !== Notes.activeId && (!!editorId || titleField.text !== (draft.title || "") || bodyField.text !== (draft.body || ""));
        syncing = true;
        if (titleField.text !== draft.title) titleField.text = draft.title || "";
        if (bodyField.text !== draft.body) bodyField.text = draft.body || "";
        if (changedNote) {
            bodyField.cursorPosition = Math.min(bodyField.length, Math.max(0, draft.cursor || 0));
            Qt.callLater(() => {
                root.syncing = true;
                bodyScroll.contentY = Math.min(Math.max(0, bodyScroll.contentHeight - bodyScroll.height), Math.max(0, Notes.draft.scroll || 0));
                root.syncing = false;
            });
        }
        editorId = Notes.activeId;
        syncing = false;
    }
    function focusEditor(): void { if (interactive && editorVisible && editable) bodyField.forceActiveFocus(); }
    function newNote(): void {
        if (!interactive || !Notes.loaded) return;
        remember();
        if (Notes.newNote()) { showEditor = true; syncDraft(); Qt.callLater(focusEditor); }
    }
    function selectNote(id: string): void {
        if (!interactive) return;
        remember();
        if (Notes.select(id)) { showEditor = true; syncDraft(); Qt.callLater(focusEditor); }
    }
    function library(): void {
        if (!interactive) return;
        remember(); Notes.libraryOpen = !Notes.libraryOpen; showEditor = false;
        Qt.callLater(() => { if (root.listVisible) searchField.forceActiveFocus(); else root.focusEditor(); });
    }
    function find(): void {
        if (!interactive) return;
        remember(); Notes.libraryOpen = true; showEditor = false;
        Qt.callLater(() => searchField.forceActiveFocus());
    }
    function copyNote(): void {
        if (!interactive) return;
        Quickshell.clipboardText = bodyField.text;
        copied = "Copied"; copiedTimer.restart();
    }
    function diagnostics(): var {
        const origin = popupInputRegion?.mapToItem(null, 0, 0);
        const corner = popupInputRegion?.mapToItem(null, popupInputRegion.width, popupInputRegion.height);
        const menuItems = [];
        if (overflow.visible) for (let i = 0; i < overflow.count; i++) {
            const row = overflow.itemAt(i);
            if (!row.text) continue;
            const start = row.mapToItem(null, 0, 0), end = row.mapToItem(null, row.width, row.height);
            menuItems.push({text:row.text, enabled:row.enabled, hovered:row.hovered, highlighted:row.highlighted,
                            x:start.x, y:start.y, width:end.x-start.x, height:end.y-start.y});
        }
        return {compact, listVisible, editorVisible, category, count: results.length, activeId: Notes.activeId,
                focused: bodyField.activeFocus ? "body" : titleField.activeFocus ? "title" : searchField.activeFocus ? "search" : "other",
                cursor: bodyField.cursorPosition, scroll: bodyScroll.contentY, interactive, menuOpen: overflow.opened, deleteOpen: !!deleteId,
                menuRect:origin ? {x:origin.x, y:origin.y, width:corner.x-origin.x, height:corner.y-origin.y} : null, menuItems};
    }
    Component.onCompleted: { syncDraft(); initialized = true; Qt.callLater(focusEditor); }
    onActiveFocusChanged: if (activeFocus) Qt.callLater(() => { if (root.Window.window?.activeFocusItem === root) root.focusEditor(); })
    onInteractiveChanged: if (!interactive) { overflow.close(); deleteId = ""; } else Qt.callLater(focusEditor)
    onCategoryChanged: refreshOrder()
    Connections {
        target: Notes
        function onDraftChanged() { root.syncDraft(); }
        function onLoadedChanged() { root.syncDraft(); Qt.callLater(root.focusEditor); }
        function onLibraryOpenChanged() { if (Notes.libraryOpen) root.refreshOrder(); }
    }
    Timer {id: copiedTimer; interval: 1800; onTriggered: root.copied = ""}
    Keys.priority: Keys.BeforeItem
    Keys.onPressed: event => {
        if (!interactive) return;
        if (deleteId && event.key !== Qt.Key_Escape) return;
        if (event.modifiers & Qt.ControlModifier) {
            if (event.key === Qt.Key_N) { newNote(); event.accepted = true; }
            else if (event.key === Qt.Key_F) { find(); event.accepted = true; }
            else if (event.key === Qt.Key_S) { remember(); Notes.flush("keyboard"); event.accepted = true; }
        } else if (event.key === Qt.Key_Escape) {
            if (deleteId) { deleteId = ""; focusEditor(); event.accepted = true; }
            else if (overflow.opened) { overflow.close(); event.accepted = true; }
            else if (query) { query = ""; searchField.clear(); event.accepted = true; }
            else if (Notes.libraryOpen && compact && showEditor) { showEditor = false; searchField.forceActiveFocus(); event.accepted = true; }
        }
    }

    component HeaderButton: IconButton {
        size: 16
        implicitWidth: 32; implicitHeight: 32
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Math.max(0, (root.shortViewport?12:24) - Preferences.innerPadding)
        anchors.bottomMargin:root.height-root.viewportHeight+anchors.margins
        enabled: !root.deleteId
        spacing: root.shortViewport?8:16
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            PanelText {Layout.fillWidth: true; text: Notes.libraryOpen ? "Notes library" : "Quick Notes"; font.pixelSize: 15; font.weight: Font.DemiBold}
            HeaderButton {
                icon: root.compact && Notes.libraryOpen && root.showEditor ? "arrow_back" : Notes.libraryOpen ? "close_fullscreen" : "library_books"
                label: root.compact && Notes.libraryOpen && root.showEditor ? "Back to library" : Notes.libraryOpen ? "Close library" : "Open library"
                onClicked: { if (root.compact && Notes.libraryOpen && root.showEditor) {root.remember(); root.showEditor = false; searchField.forceActiveFocus();} else root.library(); }
            }
            HeaderButton {objectName: "notesVoice"; icon: "mic"; label: "Talk to Luma"; enabled: !Preferences.preview && Preferences.lumaVoice && !Luma.busy && !Voice.active; onClicked: root.talk()}
            HeaderButton {icon: "add"; label: "New note · Ctrl+N"; color: Theme.accent; background: Theme.withAlpha(Theme.accent, .1); enabled: Notes.loaded; onClicked: root.newNote()}
            HeaderButton {id: menuButton; objectName: "notesActions"; icon: "more_horiz"; label: "Note actions"; onClicked: overflow.open()}
        }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: errorRow.implicitHeight + 16
            visible: !!Notes.error; radius: 10; color: Theme.withAlpha(Theme.red, .07)
            RowLayout {id: errorRow; anchors.fill: parent; anchors.margins: 8; spacing: 8
                PanelText {Layout.fillWidth: true; text: Notes.error; font.pixelSize: 12; color: Theme.red; wrapMode: Text.Wrap; elide: Text.ElideNone; maximumLineCount: 3}
                ChoiceButton {objectName: "notesRetry"; text: "Retry"; implicitHeight: 28; onClicked: Notes.retry()}
                ChoiceButton {objectName: "notesRecover"; text: "Recover"; implicitHeight: 28; visible: !Notes.loaded && !!Notes.error; onClicked: Notes.recover()}
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            ColumnLayout {
                id: libraryPane
                Layout.fillHeight: true; Layout.fillWidth: root.compact; Layout.preferredWidth: root.compact ? root.width : 240
                Layout.maximumWidth: root.compact ? Infinity : 240
                visible: root.listVisible; enabled: visible && root.interactive; spacing: 8
                TextField {
                    id: searchField; objectName: "notesSearch"
                    cursorDelegate:InputCaret {editor:searchField}
                    Layout.fillWidth: true; implicitHeight: 36; placeholderText: "Search notes"; selectByMouse: true
                    font.family: Tokens.font; font.pixelSize: 13; color: Theme.text; placeholderTextColor: Theme.subtext; selectionColor: Theme.accent; selectedTextColor: Theme.accentText
                    leftPadding: 12; rightPadding: clearSearch.visible ? 36 : 12
                    onTextEdited: { root.query = text; }
                    background: Rectangle {radius: 10; color: Theme.surfaceSolid; border.width: 1; border.color: searchField.activeFocus ? Theme.accent : Theme.withAlpha(Theme.text, .07)}
                    IconButton {id: clearSearch; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; size: 12; icon: "close"; label: "Clear search"; visible: !!searchField.text; onClicked: {searchField.clear(); root.query = ""; searchField.forceActiveFocus();}}
                    Accessible.name: "Search notes"
                    Keys.onDownPressed: {if (noteList.count) {noteList.currentIndex = 0; noteList.forceActiveFocus();}}
                }
                RowLayout {Layout.fillWidth: true; spacing: 0
                    Repeater {model: [{id: "active", label: "All"}, {id: "pinned", label: "Pinned"}, {id: "archived", label: "Archive"}, {id: "trash", label: "Trash"}]
                        AbstractButton {
                            id: categoryTab; required property var modelData
                            Layout.fillWidth: true; implicitWidth: 40; implicitHeight: 32
                            text: modelData.label; hoverEnabled: true
                            onClicked: root.category = modelData.id
                            Accessible.name: text
                            contentItem: PanelText {text: categoryTab.text; font.pixelSize: 12; font.weight: root.category === categoryTab.modelData.id ? Font.DemiBold : Font.Normal; color: root.category === categoryTab.modelData.id ? Theme.text : Theme.subtext; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter}
                            background: Rectangle {
                                radius: 6; color: Theme.withAlpha(Theme.text, categoryTab.pressed ? .06 : categoryTab.hovered ? .03 : 0)
                                border.width: categoryTab.activeFocus ? 1 : 0; border.color: Theme.accent
                                Rectangle {anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; width: categoryTab.contentItem.implicitWidth; height: 2; radius: 1; color: Theme.accent; visible: root.category === categoryTab.modelData.id}
                            }
                            HoverHandler {cursorShape: Qt.PointingHandCursor}
                        }
                    }
                }
                ListView {
                    id: noteList; objectName: "notesList"
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4; model: root.results
                    boundsBehavior: Flickable.StopAtBounds
                    currentIndex: -1
                    ScrollBar.vertical: ScrollBar {policy: ScrollBar.AsNeeded}
                    Keys.onReturnPressed: if (currentIndex >= 0) root.selectNote(root.results[currentIndex].id)
                    Keys.onEnterPressed: if (currentIndex >= 0) root.selectNote(root.results[currentIndex].id)
                    delegate: AbstractButton {
                        id: row; required property var modelData; required property int index
                        readonly property bool dense: noteList.height < 164
                        readonly property bool showsPreview: noteList.height >= 48
                        width: noteList.width - 4; height: showsPreview ? dense ? 48 : 80 : Math.max(0, noteList.height); hoverEnabled: true
                        leftPadding: 12; rightPadding: 12; topPadding: dense ? 6 : 12; bottomPadding: dense ? 6 : 12
                        onClicked: root.selectNote(modelData.id)
                        Accessible.name: root.libraryTitle(modelData) + (modelData.pinned ? ", pinned" : "")
                        Accessible.description: root.libraryPreview(modelData)
                        background: Rectangle {
                            radius: 10; color: row.modelData.id === Notes.activeId ? Theme.withAlpha(Theme.accent, .09) : row.hovered ? Theme.withAlpha(Theme.text, .04) : "transparent"
                            border.width: row.activeFocus || noteList.activeFocus && noteList.currentIndex === row.index ? 1 : 0; border.color: Theme.accent
                        }
                        contentItem: Column {
                            spacing: row.dense ? 4 : 8
                            RowLayout {width: parent.width; spacing: 8
                                Icon {icon: "push_pin"; size: 13; color: Theme.accent; visible: row.modelData.pinned; Layout.alignment: Qt.AlignVCenter}
                                PanelText {Layout.fillWidth: true; text: root.markedText(root.libraryTitle(row.modelData)); textFormat: Text.StyledText; font.pixelSize: 13; font.weight: Font.Medium; Layout.alignment: Qt.AlignVCenter}
                                PanelText {text: row.modelData.updatedAt ? Qt.formatDateTime(new Date(row.modelData.updatedAt), "d MMM") : ""; font.pixelSize: 11; color: Theme.subtext; Layout.alignment: Qt.AlignVCenter}
                            }
                            PanelText {width: parent.width; text: root.markedText(root.libraryPreview(row.modelData).replace(/\s+/g, " ")); textFormat: Text.StyledText; visible: !!text && row.showsPreview; font.pixelSize: 12; color: Theme.subtext; wrapMode: row.dense ? Text.NoWrap : Text.Wrap; maximumLineCount: row.dense ? 1 : 2}
                        }
                    }
                    Column {anchors.centerIn: parent; width: parent.width - 20; spacing: 8; visible: noteList.count === 0
                        Icon {anchors.horizontalCenter: parent.horizontalCenter; icon: root.query ? "search" : root.category === "trash" ? "delete_outline" : "edit_note"; size: 25; color: Theme.withAlpha(Theme.accent, .6)}
                        PanelText {width: parent.width; horizontalAlignment: Text.AlignHCenter; text: !Notes.loaded ? "Loading notes…" : root.query ? "No matching notes" : root.category === "trash" ? "Trash is empty" : root.category === "archived" ? "No archived notes" : root.category === "pinned" ? "Pin a note to keep it here" : "Your next thought starts here"; font.pixelSize: 11; color: Theme.subtext; wrapMode: Text.Wrap; elide: Text.ElideNone}
                        ChoiceButton {anchors.horizontalCenter: parent.horizontalCenter; text: "New note"; visible: !root.query && root.category === "active"; enabled: Notes.loaded; onClicked: root.newNote()}
                    }
                }
            }
            Item {
                Layout.fillHeight: true; Layout.preferredWidth: 24; visible: root.listVisible && root.editorVisible
                Rectangle {anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 1; color: Theme.withAlpha(Theme.text, .065)}
            }
            Item {
                id: editorPane
                Layout.fillWidth: true; Layout.fillHeight: true; visible: root.editorVisible; enabled: visible && root.interactive && !root.deleteId
                ColumnLayout {anchors.fill: parent; spacing: root.shortViewport?8:16
                    TextField {
                        id: titleField; objectName: "notesTitle"; Layout.fillWidth: true; implicitHeight: 32
                        cursorDelegate:InputCaret {editor:titleField}
                        maximumLength: 300
                        placeholderText: "Title, if you like"; readOnly: !root.editable; selectByMouse: true
                        padding: 0; font.family: Tokens.font; font.pixelSize: 20; font.weight: Font.Medium
                        color: Theme.text; placeholderTextColor: Theme.withAlpha(Theme.subtext, .62); selectionColor: Theme.accent; selectedTextColor: Theme.accentText
                        background: Item {}
                        onTextEdited: root.remember()
                        Accessible.name: "Optional note title"
                        Keys.onReturnPressed: bodyField.forceActiveFocus()
                    }
                    Flickable {
                        id: bodyScroll; objectName: "notesScroll"; Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true; boundsBehavior: Flickable.StopAtBounds; contentWidth: width
                        onContentYChanged: if (!root.syncing) root.remember()
                        ScrollBar.vertical: ScrollBar {policy: ScrollBar.AsNeeded}
                        TextArea.flickable: TextArea {
                            id: bodyField; objectName: "notesBody"
                            cursorDelegate:InputCaret {editor:bodyField;viewport:bodyScroll}
                            placeholderText: "Write something to remember…"; readOnly: !root.editable; selectByMouse: true
                            wrapMode: TextEdit.Wrap; textFormat: TextEdit.PlainText
                            padding: 0; leftPadding: 0; rightPadding: 0; bottomPadding: 8
                            font.family: Tokens.font; font.pixelSize: 15; font.weight: Font.Normal
                            color: Theme.text; placeholderTextColor: Theme.withAlpha(Theme.subtext, .65)
                            selectionColor: Theme.withAlpha(Theme.accent, .65); selectedTextColor: Theme.accentText
                            background: Item {}
                            Keys.onTabPressed: event => { bodyField.nextItemInFocusChain().forceActiveFocus(Qt.TabFocusReason); event.accepted = true; }
                            Keys.onBacktabPressed: event => { bodyField.nextItemInFocusChain(false).forceActiveFocus(Qt.BacktabFocusReason); event.accepted = true; }
                            onTextChanged: if (!root.syncing) root.remember()
                            onCursorPositionChanged: if (!root.syncing) root.remember()
                            Accessible.name: "Note body"
                        }
                    }
                    RowLayout {Layout.fillWidth: true; visible: !!root.active && root.active.status !== "active"
                        PanelText {Layout.fillWidth: true; text: root.active?.status === "trash" ? "This note is in Trash" : "Archived note"; color: Theme.subtext; font.pixelSize: 11}
                        ChoiceButton {text: "Restore"; implicitHeight: 28; onClicked: Notes.setStatus(Notes.activeId, "active")}
                    }
                }
            }
        }
        RowLayout {Layout.fillWidth: true; spacing: 8
            Rectangle {width: 5; height: 5; radius: 2.5; color: Notes.error ? Theme.red : Notes.dirty || Notes.saving ? Theme.accent : Theme.withAlpha(Theme.subtext, .6)}
            PanelText {Layout.fillWidth: true; text: root.copied || (Notes.exportPath ? "Exported to " + Notes.exportPath : Notes.saveState === "Failed" ? "Save failed" : Notes.saveState); font.pixelSize: 11; color: Notes.error ? Theme.red : Theme.subtext; Accessible.role: Accessible.StaticText; Accessible.name: text}
            ChoiceButton {text: "Undo Trash"; visible: !!Notes.undo; implicitHeight: 26; onClicked: Notes.undoTrash()}
            PanelText {text: "Ctrl+N · Ctrl+F"; visible: !Notes.undo && root.width > 330; color: Theme.subtext; font.pixelSize: 11}
        }
    }
    component NoteAction: MenuItem {
        id: actionItem
        implicitHeight: 31; font.family: Tokens.font; font.pixelSize: 11; hoverEnabled: true
        contentItem: PanelText {text: actionItem.text; color: actionItem.enabled ? Theme.text : Theme.subtext; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11}
        background: Rectangle {radius: 7; color: actionItem.highlighted ? Theme.withAlpha(Theme.accent, .12) : "transparent"; border.width: actionItem.activeFocus ? 1 : 0; border.color: Theme.accent}
        HoverHandler {cursorShape: Qt.PointingHandCursor}
    }
    Menu {
        id: overflow; objectName: "notesOverflow"
        popupType: Popup.Item
        scale: Preferences.uiScale
        x: Math.max(0, root.width - Math.max(0, 24 - Preferences.innerPadding) - width); y: Math.max(0, 24 - Preferences.innerPadding) + 40; width: Math.min(210, root.width)
        height: Math.min(implicitHeight, Math.max(64, root.viewportHeight - y))
        modal: true; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {radius: 12; color: Theme.surfaceSolid; border.width: 1; border.color: Theme.withAlpha(Theme.text, .1)}
        NoteAction {text: root.active?.pinned ? "Unpin note" : "Pin note"; enabled: !!root.active && root.active.status === "active"; onTriggered: Notes.setPinned(Notes.activeId, !root.active.pinned)}
        NoteAction {text: root.active?.status === "archived" || root.active?.status === "trash" ? "Restore note" : "Archive note"; enabled: !!root.active; onTriggered: Notes.setStatus(Notes.activeId, root.active.status === "active" ? "archived" : "active")}
        NoteAction {text: root.active?.status === "trash" ? "Delete permanently…" : "Move to Trash"; enabled: !!root.active; onTriggered: {if (root.active.status === "trash") root.deleteId = Notes.activeId; else Notes.setStatus(Notes.activeId, "trash");}}
        MenuSeparator {contentItem: Rectangle {implicitHeight: 1; color: Theme.withAlpha(Theme.text, .08)}}
        NoteAction {text: "Copy note body"; enabled: !!bodyField.text; onTriggered: root.copyNote()}
        NoteAction {text: "Export note"; enabled: !!root.active; onTriggered: Notes.exportNotes([Notes.activeId], "")}
        NoteAction {text: "Export this collection"; enabled: root.results.length > 0; onTriggered: Notes.exportNotes(root.results.map(note => note.id), "")}
        MenuSeparator {contentItem: Rectangle {implicitHeight: 1; color: Theme.withAlpha(Theme.text, .08)}}
        NoteAction {text: "Insert bullet"; enabled: root.editable && root.editorVisible; onTriggered: root.insertText("- ")}
        NoteAction {text: "Insert task"; enabled: root.editable && root.editorVisible; onTriggered: root.insertText("- [ ] ")}
        NoteAction {text: "Insert code block"; enabled: root.editable && root.editorVisible; onTriggered: root.insertText("```\n\n```\n")}
        MenuSeparator {contentItem: Rectangle {implicitHeight: 1; color: Theme.withAlpha(Theme.text, .08)}}
        NoteAction {text: "Talk to Luma"; enabled: !Preferences.preview && Preferences.lumaVoice && !Luma.busy && !Voice.active; onTriggered: root.talk()}
    }
    Rectangle {
        anchors.fill: parent; z: 10; visible: !!root.deleteId; enabled: visible && root.interactive
        radius: 12; color: Theme.bgSolid; border.width: 1; border.color: Theme.withAlpha(Theme.red, .35)
        MouseArea {anchors.fill: parent; acceptedButtons: Qt.AllButtons; onWheel: event => event.accepted = true}
        ColumnLayout {anchors.centerIn: parent; width: Math.min(320, parent.width - 32); spacing: 14
            PanelText {Layout.fillWidth: true; text: "Delete this note permanently?"; font.pixelSize: 15; font.weight: Font.Medium; wrapMode: Text.Wrap; elide: Text.ElideNone}
            PanelText {Layout.fillWidth: true; text: "This cannot be undone. Restore the note to keep it."; font.pixelSize: 12; color: Theme.subtext; wrapMode: Text.Wrap; elide: Text.ElideNone}
            RowLayout {Layout.fillWidth: true; spacing: 8
                ChoiceButton {id: deleteCancel; Layout.fillWidth: true; objectName: "notesDeleteCancel"; text: "Cancel"; onClicked: {root.deleteId = ""; root.focusEditor();}}
                ChoiceButton {Layout.fillWidth: true; objectName: "notesDeleteConfirm"; text: "Delete permanently"; onClicked: {Notes.deleteNote(root.deleteId); root.deleteId = "";}}
            }
        }
        onVisibleChanged: if (visible) deleteCancel.forceActiveFocus()
    }
}
