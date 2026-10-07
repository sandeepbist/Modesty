import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Services.Pipewire
import qs.components
import qs.services
import qs.theme

ColumnLayout {
    id: root
    spacing: 12

    PanelHeader {
        title:"Privacy";backPanel:"clock"
        PanelText {visible:Audio.captureStreams.length>0;text:Audio.captureStreams.length+" active";font.pixelSize:11;color:Theme.red}
    }

    Flickable {
        id: captureList
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 64
        implicitHeight: Math.max(64, streams.implicitHeight)
        contentHeight: streams.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ColumnLayout {
            id: streams
            width: parent.width
            spacing: 7
            Repeater {
                model: Audio.captureStreams
                Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: 58
                    radius: 14
                    color: Theme.withAlpha(Theme.text, .055)
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 11
                        spacing: 10
                        Icon { icon: Audio.captureKind(modelData) === "Microphone" ? "mic" : "videocam"; size: 18; color: Audio.captureKind(modelData) === "Camera" ? "#30d158" : Audio.captureKind(modelData) === "Microphone" ? "#ff9f0a" : "#64b5ff" }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            PanelText { Layout.fillWidth: true; text: Audio.captureLabel(modelData); font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            PanelText { text: Audio.captureKind(modelData) + (modelData.directCamera ? " · device open" : modelData.audio?.muted ? " · muted" : " · in use"); font.pixelSize: 11; color: Theme.subtext }
                        }
                    }
                }
            }
        }
        PanelText {parent:captureList;anchors.centerIn:parent;width:Math.max(0,parent.width-24);horizontalAlignment:Text.AlignHCenter;visible:!Audio.captureStreams.length;text:"No active capture";color:Theme.subtext;font.pixelSize:13}
    }

    RowLayout {
        Layout.fillWidth: true
        PanelText {Layout.fillWidth:true;text:"Microphone";font.pixelSize:13;color:Theme.subtext;visible:!!Audio.source}
        IconButton { icon: Audio.source?.audio?.muted ? "mic_off" : "mic"; label: Audio.source?.audio?.muted ? "Unmute microphone" : "Mute microphone"; size: 16; visible: !!Audio.source; onClicked: Audio.muteNode(Audio.source) }
    }
}
