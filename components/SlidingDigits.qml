import QtQuick
import qs.theme

Item {
    id: root
    property string text: ""
    property font font: Qt.font({family:Tokens.clockFont,pixelSize:15,weight:Font.Medium,features:{tnum:1}})
    property color color: Theme.text
    property bool animated: true
    Row {
        anchors.centerIn: parent
        height: parent.height
        Repeater {
            model: root.text.length
            Item {
                id: digit
                required property int index
                property string value:root.text.charAt(index)
                property string shown:value
                property string outgoing:""
                property real progress:1
                property bool ready:false
                width:metrics.advanceWidth;height:root.height;clip:true
                TextMetrics {id:metrics;font:root.font;text:/\d/.test(digit.value)?"0":digit.value}
                function update():void {
                    if (!ready || motion.running || value===shown) return;
                    if (!root.animated || Tokens.reducedMotion || !visible || !/\d/.test(value)) {shown=value;outgoing="";progress=1;return;}
                    outgoing=shown;shown=value;progress=0;motion.start();
                }
                onValueChanged:update()
                onVisibleChanged:if(!visible){motion.stop();shown=value;outgoing="";progress=1;}
                Component.onCompleted:{shown=value;outgoing="";progress=1;ready=true;}
                NumberAnimation {
                    id:motion;target:digit;property:"progress";to:1
                    duration:Math.min(220,Tokens.animMedium);easing.type:Easing.OutCubic
                    onFinished:{digit.outgoing="";Qt.callLater(digit.update);}
                }
                PanelText {
                    width:parent.width;height:parent.height;y:-parent.height*digit.progress
                    visible:!!digit.outgoing;text:digit.outgoing;font:root.font;color:root.color
                    horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;elide:Text.ElideNone
                }
                PanelText {
                    width:parent.width;height:parent.height;y:parent.height*(1-digit.progress)
                    text:digit.shown;font:root.font;color:root.color
                    horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;elide:Text.ElideNone
                }
            }
        }
    }
}
