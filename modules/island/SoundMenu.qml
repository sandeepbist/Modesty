import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.services
import qs.theme
import qs.components
ColumnLayout {
    spacing:12
    PanelHeader {title:"Sound"}
    Flickable {Layout.fillWidth:true;Layout.fillHeight:true;Layout.minimumHeight:0;implicitHeight:content.implicitHeight;contentHeight:content.implicitHeight;clip:true;boundsBehavior:Flickable.StopAtBounds
        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
        ColumnLayout {id:content;width:parent.width;spacing:12
            Repeater {model:[{title:"Output",nodes:Audio.outputs,output:true},{title:"Input",nodes:Audio.inputs,output:false},{title:"Applications",nodes:Audio.streams,output:false}]
                ColumnLayout {id:section;required property var modelData;Layout.fillWidth:true;spacing:6
                    PanelText {text:section.modelData.title;font.pixelSize:11;color:Theme.subtext}
                    PanelText {visible:!section.modelData.nodes.length;text:"No active "+section.modelData.title.toLowerCase();font.pixelSize:11;color:Theme.subtext}
                    Repeater {model:section.modelData.nodes
                        Rectangle {id:device;required property var modelData;Layout.fillWidth:true;implicitHeight:deviceBody.implicitHeight+28;radius:15;color:Theme.withAlpha(Theme.text,.045)
                            ColumnLayout {id:deviceBody;x:14;y:14;width:parent.width-28;spacing:8
                                RowLayout {Layout.fillWidth:true;PanelText {Layout.fillWidth:true;text:device.modelData.description||device.modelData.name;font.pixelSize:13;font.weight:Font.Medium}IconButton {icon:device.modelData.audio?.muted?"volume_off":"volume_up";label:"Toggle mute";size:16;onClicked:Audio.muteNode(device.modelData)}IconButton {visible:section.modelData.title!=="Applications";icon:(section.modelData.output?Audio.sink:Audio.source)===device.modelData?"check_circle":"radio_button_unchecked";label:"Use this device";size:16;color:Theme.accent;onClicked:Audio.setDefault(device.modelData,section.modelData.output)} }
                                PreferenceSlider {Layout.fillWidth:true;backgroundColor:"transparent";label:"Volume";display:Math.round((device.modelData.audio?.volume||0)*100)+"%";from:0;to:1.5;stepSize:.01;value:device.modelData.audio?.volume||0;onMoved:value=>Audio.setNodeVolume(device.modelData,value)}
                            }
                        }
                    }
                }
            }
        }
    }
}
