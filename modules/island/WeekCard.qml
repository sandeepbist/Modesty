import QtQuick
import qs.components
import qs.services
import qs.theme
Item {
    id:root
    readonly property real sidePadding:14
    Row {
        id:week
        anchors.horizontalCenter:parent.horizontalCenter
        width:Math.max(0,parent.width-root.sidePadding*2)
        y:Math.max(30,parent.height-34);spacing:3
        Repeater {
            model:7
            Column {
                id:dayColumn
                required property int index
                readonly property int distance:Math.abs(index-3)
                readonly property date day:new Date(Time.date.getFullYear(),Time.date.getMonth(),Time.date.getDate()+index-3)
                width:Math.max(0,(week.width-week.spacing*6)/7);spacing:5
                opacity:[1,.76,.48,.25][distance]
                PanelText {
                    width:parent.width;text:Qt.formatDateTime(dayColumn.day,"ddd").slice(0,1)
                    horizontalAlignment:Text.AlignHCenter;font.pixelSize:10
                    color:dayColumn.distance===0?Theme.accent:Theme.subtext
                }
                PanelText {
                    width:parent.width;text:dayColumn.day.getDate();horizontalAlignment:Text.AlignHCenter
                    font.pixelSize:12;font.features:({tnum:1});font.weight:dayColumn.distance===0?Font.DemiBold:Font.Normal
                    color:dayColumn.distance===0?Theme.accent:Theme.text
                }
            }
        }
    }
    TapHandler {onTapped:IslandState.openMenu("calendar")}
}
