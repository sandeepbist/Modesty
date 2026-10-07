import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.components
import qs.services
import qs.theme

ColumnLayout {
    id: root
    spacing: 0
    property int outputWidth: 1920
    property string outputFormat: "PNG"
    property string renamePrefix:""

    function measure(): void { IslandDrop.contentHeight = implicitHeight + Preferences.innerPadding * 2; }
    function draft(text: string): void {
        question.text = text;
        question.cursorPosition = question.length;
        question.forceActiveFocus();
    }
    function diagnostics(): var {
        return {files: IslandDrop.files.length, busy: IslandDrop.busy, exportOpen: IslandDrop.exportOpen,
                error: IslandDrop.error, contentHeight: implicitHeight, bodyHeight: body.implicitHeight,
                viewportHeight: fileScroll.height, composerHeight: composer.height, question: question.text};
    }
    onImplicitHeightChanged: measure()
    onActiveFocusChanged: if (activeFocus && IslandDrop.askable) question.forceActiveFocus()
    Component.onCompleted: Qt.callLater(measure)
    Connections {
        target: IslandDrop
        function onFilesChanged() { if (IslandDrop.images) root.outputWidth = Math.min(8192, IslandDrop.files[0].width); }
    }

    Flickable {
        id: fileScroll
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        implicitHeight: body.implicitHeight + 8
        contentHeight: implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        ColumnLayout {
            id: body
            x: 4; y: 4; width: parent.width - 8
            spacing: 0

            Repeater {
                model: IslandDrop.files
                Item {
                    id: file
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    Layout.bottomMargin: 12
                    implicitHeight: 58
                    Rectangle {
                        id: preview
                        width: file.modelData.kind === "image" ? 48 : 36
                        height: file.modelData.kind === "image" ? 48 : 44
                        anchors.verticalCenter: parent.verticalCenter
                        radius: file.modelData.kind === "image" ? 10 : 5
                        color: Theme.withAlpha(Theme.text, .065)
                        border.width: file.modelData.kind === "image" ? 0 : 1
                        border.color: Theme.withAlpha(Theme.text, .09)
                        clip: true
                        Image {
                            anchors.fill: parent
                            visible: file.modelData.kind === "image"
                            source: visible ? file.modelData.url : ""
                            sourceSize.width: 144; sourceSize.height: 144
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                        }
                        Icon {
                            anchors.centerIn: parent
                            visible: file.modelData.kind !== "image"
                            icon: file.modelData.kind === "pdf" ? "picture_as_pdf" : file.modelData.kind==="archive"?"folder_zip":"description"
                            size: 20; color: Theme.withAlpha(Theme.text, .78)
                        }
                    }
                    Column {
                        x: 62
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - (file.index === 0 ? 96 : 66)
                        spacing: 5
                        PanelText {
                            width: parent.width; text: file.modelData.name
                            font.pixelSize: 14; font.weight: Font.Medium; font.letterSpacing: -.15
                        }
                        PanelText {
                            width: parent.width
                            text: (file.modelData.kind === "image" ? file.modelData.width + " × " + file.modelData.height : file.modelData.kind === "pdf" ? "PDF" : file.modelData.kind==="archive"?"Archive":file.modelData.kind==="text"?"Text":"File")
                                  + " · " + (file.modelData.size >= 1048576 ? (file.modelData.size / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(file.modelData.size / 1024)) + " KB")
                            font.pixelSize: 11; color: Theme.subtext
                        }
                    }
                    IconButton {
                        anchors.right: parent.right; anchors.top: parent.top; anchors.topMargin: 2
                        visible: file.index === 0; icon: "close"; size: 14
                        color: Theme.subtext; label: "Close attachments"
                        onClicked: IslandState.closeMenu()
                    }
                    Rectangle {
                        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                        visible: file.index < IslandDrop.files.length - 1
                        height: 1; color: Theme.withAlpha(Theme.text, .055)
                    }
                }
            }

            Rectangle {
                id: composer
                Layout.fillWidth: true
                implicitHeight: Math.max(46, Math.min(134, question.contentHeight + 26))
                visible: IslandDrop.askable
                radius: 13
                color: Theme.withAlpha(Theme.text, question.activeFocus ? .045 : .025)
                border.width: 1
                border.color: Theme.withAlpha(question.activeFocus ? Theme.accent : Theme.text, question.activeFocus ? .3 : .065)
                Behavior on color { ColorAnimation { duration: Tokens.animFast } }
                Behavior on border.color { ColorAnimation { duration: Tokens.animFast } }
                // The island animates its outer height; this field follows the same content measure.
                SurfaceLighting { anchors.fill: parent; radius: parent.radius; focused: question.activeFocus; interactive: false }
                ScrollView {
                    x: 14; y: 13; width: parent.width - 60; height: parent.height - 26
                    contentWidth: availableWidth
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                    TextArea {
                        id: question
                        padding: 0; wrapMode: TextEdit.Wrap; selectByMouse: true; textFormat: TextEdit.PlainText
                        text: IslandDrop.question; placeholderText: "Ask Luma…"
                        color: Theme.text; placeholderTextColor: Theme.subtext
                        selectionColor: Theme.accent; selectedTextColor: Theme.bgSolid
                        font.family: Tokens.font; font.pixelSize: 13
                        font.kerning: true; font.preferTypoLineMetrics: true
                        renderType: Tokens.textRenderType; background: null
                        Accessible.name: "Question about attached files"
                        onTextChanged: if (IslandDrop.question !== text) IslandDrop.question = text
                        Connections {
                            target: IslandDrop
                            function onQuestionChanged() { if (question.text !== IslandDrop.question) question.text = IslandDrop.question; }
                        }
                        Keys.priority: Keys.BeforeItem
                        Keys.onPressed: event => {
                            if ([Qt.Key_Return, Qt.Key_Enter].includes(event.key) && !(event.modifiers & Qt.ShiftModifier) && !inputMethodComposing) {
                                event.accepted = true;
                                if (send.enabled) IslandDrop.ask(text);
                            }
                        }
                    }
                }
                IconButton {
                    id: send
                    anchors.right: parent.right; anchors.rightMargin: 8
                    anchors.bottom: parent.bottom; anchors.bottomMargin: 8
                    size: 14; icon: "arrow_upward"; label: "Ask Luma"
                    color: Theme.accent
                    background: enabled ? Theme.withAlpha(Theme.accent, .1) : "transparent"
                    enabled: !!question.text.trim() && !IslandDrop.busy && !Luma.busy && Preferences.searchAiEnabled
                    onClicked: IslandDrop.ask(question.text)
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 4
                Layout.topMargin: 12
                visible: IslandDrop.files.length > 0
                QuietAction {
                    text: "Summarize"; glyph: "auto_awesome"; visible:IslandDrop.askable
                    onClicked: root.draft(IslandDrop.files.length > 1 ? "Summarize these files and their main points." : "Summarize this file and its main points.")
                }
                QuietAction {
                    text: "Compare"; visible: IslandDrop.askable&&IslandDrop.files.length > 1
                    onClicked: root.draft("Compare these files. Explain their main differences and cite the relevant file names.")
                }
                Item { Layout.fillWidth: true }
                IconButton { icon: "content_copy"; size: 16; label: "Copy text"; color: Theme.subtext; enabled: !IslandDrop.busy; visible: IslandDrop.readable; onClicked: IslandDrop.run("extract", {}) }
                IconButton {icon:"more_horiz";size:16;label:"File actions";color:IslandDrop.toolsOpen?Theme.accent:Theme.subtext;enabled:!IslandDrop.busy;onClicked:IslandDrop.toolsOpen=!IslandDrop.toolsOpen}
                IconButton { icon: "download"; size: 16; label: "Export image"; color: IslandDrop.exportOpen ? Theme.accent : Theme.subtext; enabled: !IslandDrop.busy; visible: IslandDrop.images; onClicked: IslandDrop.exportOpen = !IslandDrop.exportOpen }
            }

            Reveal {
                Layout.fillWidth:true;open:IslandDrop.toolsOpen;enabled:open&&!IslandDrop.busy
                implicitHeight:toolsBody.implicitHeight
                ColumnLayout {
                    id:toolsBody;width:parent.width;spacing:12
                    Rectangle {Layout.fillWidth:true;height:1;color:Theme.withAlpha(Theme.text,.065)}
                    RowLayout {
                        Layout.fillWidth:true;spacing:8
                        IconButton {icon:"folder_zip";size:18;label:"Compress · saves a new copy in Documents/Luma";onClicked:IslandDrop.run("compress",{})}
                        IconButton {icon:"unarchive";size:18;label:"Extract · creates a new folder in Documents/Luma";visible:IslandDrop.archive;onClicked:IslandDrop.run("unpack",{})}
                        IconButton {icon:"merge";size:18;label:"Merge PDFs · saves a new copy in Documents/Luma";visible:IslandDrop.pdfs;onClicked:IslandDrop.run("merge",{})}
                        IconButton {icon:"edit";size:18;label:"Rename";color:IslandDrop.renameOpen?Theme.accent:Theme.subtext;onClicked:{IslandDrop.renameOpen=!IslandDrop.renameOpen;IslandDrop.renamePlan=[];}}
                        Item {Layout.fillWidth:true}
                    }
                    Reveal {
                        Layout.fillWidth:true;open:IslandDrop.renameOpen;enabled:open;implicitHeight:renameBody.implicitHeight
                        ColumnLayout {
                            id:renameBody;width:parent.width;spacing:12
                            RowLayout {
                                Layout.fillWidth:true;spacing:8
                                EntryField {id:renameField;Layout.fillWidth:true;text:root.renamePrefix;placeholderText:"New name";Accessible.name:"New file name or batch prefix";onTextEdited:{root.renamePrefix=text;IslandDrop.renamePlan=[];}onAccepted:IslandDrop.run("rename-preview",{prefix:text})}
                                QuietAction {text:"Preview";enabled:!!renameField.text.trim();onClicked:IslandDrop.run("rename-preview",{prefix:renameField.text})}
                            }
                            Repeater {
                                model:IslandDrop.renamePlan
                                RowLayout {required property var modelData;Layout.fillWidth:true;spacing:10
                                    Icon {icon:"draft";size:15;color:Theme.subtext}
                                    PanelText {Layout.fillWidth:true;text:modelData.name;font.pixelSize:12;font.weight:Font.Medium}
                                    IconButton {icon:"info";size:12;label:modelData.path.split("/").pop()+" becomes "+modelData.name;color:Theme.subtext}
                                }
                            }
                            QuietAction {text:"Rename";glyph:"check";selected:true;visible:IslandDrop.renamePlan.length>0;onClicked:IslandDrop.run("rename",{prefix:renameField.text,plan:IslandDrop.renamePlan})}
                        }
                    }
                }
            }

            Reveal {
                id: exportOptions
                Layout.fillWidth: true
                open: IslandDrop.exportOpen
                enabled: open && !IslandDrop.busy
                ColumnLayout {
                    id: exportBody
                    width: parent.width
                    spacing: 12
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.withAlpha(Theme.text, .065) }
                    Item {
                        id: formats
                        Layout.fillWidth: true; implicitHeight: 34
                        readonly property var names: ["PNG", "JPEG", "WEBP"]
                        Rectangle { anchors.fill: parent; radius: 10; color: Theme.withAlpha(Theme.text, .035) }
                        Rectangle {
                            x: 4 + formats.names.indexOf(root.outputFormat) * (formats.width - 8) / 3
                            y: 4; width: (formats.width - 8) / 3; height: 26; radius: 7
                            color: Theme.withAlpha(Theme.accent, .08)
                            border.width: 1; border.color: Theme.withAlpha(Theme.accent, .25)
                            Behavior on x { NumberAnimation { duration: Tokens.animMedium; easing.type: Easing.OutCubic } }
                        }
                        Row {
                            x: 4; y: 4; width: parent.width - 8; height: 26
                            Repeater {
                                model: formats.names
                                AbstractButton {
                                    required property string modelData
                                    width: formats.width / 3 - 8 / 3; height: 26
                                    text: modelData === "WEBP" ? "WebP" : modelData
                                    Accessible.name: text + " image format"
                                    onClicked: root.outputFormat = modelData
                                    background: Rectangle { color: "transparent"; radius: 7; border.width: parent.activeFocus ? 1 : 0; border.color: Theme.accent }
                                    contentItem: PanelText { text: parent.text; font.pixelSize: 12; font.weight: Font.Medium; color: root.outputFormat === parent.modelData ? Theme.text : Theme.subtext; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                    Keys.onPressed: event => {
                                        if ([Qt.Key_Left, Qt.Key_Right].includes(event.key)) {
                                            root.outputFormat = formats.names[Math.max(0, Math.min(2, formats.names.indexOf(root.outputFormat) + (event.key === Qt.Key_Right ? 1 : -1)))];
                                            event.accepted = true;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        EntryField {
                            id: widthField
                            Layout.fillWidth: true; implicitHeight: 36; rightPadding: 34
                            text: String(root.outputWidth); placeholderText: "Width"
                            Accessible.name: "Image width in pixels"
                            validator: IntValidator { bottom: 1; top: 8192 }
                            onTextEdited: if (acceptableInput) root.outputWidth = Number(text)
                            onAccepted: if (acceptableInput) IslandDrop.run("export", {width: root.outputWidth, format: root.outputFormat})
                            PanelText { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: "px"; font.pixelSize: 11; color: Theme.subtext }
                        }
                        QuietAction { text: "Save copy"; glyph: "check"; selected: true; enabled: widthField.acceptableInput && !IslandDrop.busy; onClicked: IslandDrop.run("export", {width: root.outputWidth, format: root.outputFormat}) }
                    }
                }
                implicitHeight: exportBody.implicitHeight
            }

            Reveal {
                Layout.fillWidth: true
                open: IslandDrop.busy || !!IslandDrop.status || !!IslandDrop.error
                implicitHeight: statusRow.implicitHeight
                RowLayout {
                    id: statusRow
                    width: parent.width; spacing: 8
                    ActivityPulse { running: IslandDrop.busy; visible: running }
                    Icon { visible: !IslandDrop.busy; size: 14; icon: IslandDrop.error ? "error" : "check"; color: IslandDrop.error ? Theme.red : Theme.accent }
                    PanelText {
                        Layout.fillWidth: true
                        text: IslandDrop.error || (IslandDrop.busy ? ({inspect: "Reading files…", extract: "Reading text…", export: "Saving copies…",compress:"Creating archive…",unpack:"Extracting archive…",merge:"Merging PDFs…",rename:"Applying names…", "rename-preview":"Preparing names…"})[IslandDrop.operation] : IslandDrop.status)
                        font.pixelSize: 12; color: IslandDrop.error ? Theme.red : Theme.subtext
                        wrapMode: Text.WordWrap; elide: Text.ElideNone
                    }
                    IconButton { visible: !!IslandDrop.lastOutput; size: 14; icon: "folder_open"; label: "Show result"; onClicked: Quickshell.execDetached(["xdg-open", IslandDrop.lastOutput.slice(0, IslandDrop.lastOutput.lastIndexOf("/"))]) }
                    IconButton { visible: !IslandDrop.busy; size: 12; icon: "close"; label: "Dismiss status"; onClicked: { IslandDrop.status = ""; IslandDrop.error = ""; } }
                }
            }
        }
    }

    component Reveal: Item {
        property bool open: false
        property real amount: open ? 1 : 0
        Layout.preferredHeight: amount * implicitHeight
        Layout.topMargin: IslandDrop.files.length > 0 ? amount * 12 : 0
        opacity: amount; visible: amount > 0; clip: true
        Behavior on amount { enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate} }
    }

    component QuietAction: AbstractButton {
        id: button
        property string glyph: ""
        property bool selected: false
        implicitHeight: 32
        implicitWidth: label.implicitWidth + (glyph ? 34 : 16)
        hoverEnabled: true
        Accessible.name: text
        opacity: enabled ? 1 : .4
        scale: pressed ? .97 : 1
        Behavior on scale { NumberAnimation { duration: Tokens.animFast; easing.type: Easing.OutCubic } }
        HoverHandler { cursorShape: Qt.PointingHandCursor }
        background: Rectangle {
            radius: 8
            color: Theme.withAlpha(Theme.text, button.pressed ? .075 : button.hovered ? .04 : 0)
            border.width: button.activeFocus ? 1 : 0; border.color: Theme.accent
            Behavior on color { ColorAnimation { duration: Tokens.animFast } }
        }
        contentItem: Item {
            Icon { x: 7; anchors.verticalCenter: parent.verticalCenter; visible: !!button.glyph; icon: button.glyph; size: 13; color: button.selected ? Theme.accent : button.hovered || button.activeFocus ? Theme.text : Theme.subtext }
            PanelText { id: label; x: button.glyph ? 26 : 8; height: parent.height; text: button.text; font.pixelSize: 12; font.weight: Font.Medium; color: button.selected ? Theme.accent : button.hovered || button.activeFocus ? Theme.text : Theme.subtext; verticalAlignment: Text.AlignVCenter; Behavior on color { ColorAnimation { duration: Tokens.animFast } } }
        }
    }
}
