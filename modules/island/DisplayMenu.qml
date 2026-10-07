import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.services
import qs.theme
import qs.components
ColumnLayout {
    spacing:12
    PanelHeader {title:"Display"}
    Flickable {Layout.fillWidth:true;Layout.fillHeight:true;Layout.minimumHeight:0;implicitHeight:cards.implicitHeight;contentHeight:cards.implicitHeight;clip:true;boundsBehavior:Flickable.StopAtBounds
        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
        ColumnLayout {id:cards;width:parent.width;spacing:10
            Repeater {model:Display.monitors
                Rectangle {id:monitor;required property var modelData;property bool modesOpen:false;Layout.fillWidth:true;implicitHeight:details.implicitHeight+28;radius:16;color:Theme.withAlpha(Theme.text,0.045)
                    ColumnLayout {id:details;x:14;y:14;width:parent.width-28;spacing:10
                        RowLayout {Layout.fillWidth:true;Icon {icon:"desktop_windows";color:monitor.modelData.focused?Theme.accent:Theme.subtext;size:18}ColumnLayout {Layout.fillWidth:true;spacing:2;PanelText {Layout.fillWidth:true;text:monitor.modelData.name;font.weight:Font.Medium;font.pixelSize:13}PanelText {Layout.fillWidth:true;text:monitor.modelData.width+" × "+monitor.modelData.height+" · "+Math.round(monitor.modelData.refreshRate)+" Hz · "+monitor.modelData.scale+"×";font.pixelSize:11;color:Theme.subtext}}PanelText {text:monitor.modelData.focused?"Focused":"";font.pixelSize:10;color:Theme.accent} }
                        PreferenceSlider {Layout.fillWidth:true;visible:monitor.modelData.name.startsWith("eDP")||monitor.modelData.name.startsWith("LVDS");backgroundColor:"transparent";label:"Brightness";display:Math.round(SystemInfo.brightness*100)+"%";value:SystemInfo.brightness;from:0.01;to:1;stepSize:0.01;enabled:SystemInfo.brightnessAvailable;onMoved:value=>SystemInfo.setBrightness(value)}
                        Flow {Layout.fillWidth:true;spacing:4;Repeater {model:[1,1.25,1.5,1.75,2];ActionButton {required property real modelData;text:modelData+"×";implicitWidth:Math.max(40,(details.width-16)/5);implicitHeight:27;padding:4;primary:monitor.modelData.scale===modelData;enabled:!Display.busy&&Math.abs(monitor.modelData.width/modelData-Math.round(monitor.modelData.width/modelData))<.001&&Math.abs(monitor.modelData.height/modelData-Math.round(monitor.modelData.height/modelData))<.001;onClicked:Display.change(monitor.modelData.name,"",modelData)}} }
                        ActionButton {Layout.fillWidth:true;text:"Resolution · "+monitor.modelData.width+" × "+monitor.modelData.height;onClicked:monitor.modesOpen=!monitor.modesOpen}
                        ColumnLayout {Layout.fillWidth:true;visible:monitor.modesOpen;Repeater {model:monitor.modelData.availableModes;ActionButton {required property string modelData;Layout.fillWidth:true;text:modelData;enabled:!Display.busy;onClicked:{Display.change(monitor.modelData.name,modelData,monitor.modelData.scale);monitor.modesOpen=false;}}} }
                    }
                }
            }
            PreferenceSwitch {Layout.fillWidth:true;label:"Night Light";description:Display.nightLight?Display.temperature+" K":"Warmer colors after dark";checked:Display.nightLight;onToggled:checked=>Display.setNightLight(checked)}
            PreferenceSlider {Layout.fillWidth:true;visible:Display.nightLight;label:"Temperature";display:Display.temperature+" K";from:2000;to:6500;stepSize:25;value:Display.temperature;onMoved:value=>{Display.temperature=value;Display.setNightLight(true);}}
        }
    }
    PanelText {Layout.fillWidth:true;visible:!!Display.error;text:Display.error;color:Theme.red;wrapMode:Text.Wrap;elide:Text.ElideNone;font.pixelSize:11}
    RowLayout {visible:Display.pending;Layout.fillWidth:true;PanelText {Layout.fillWidth:true;text:"Keep changes? "+Display.remaining+" s";font.pixelSize:11}ActionButton {text:"Revert";onClicked:Display.confirm(false)}ActionButton {text:"Keep";primary:true;onClicked:Display.confirm(true)}}
}
