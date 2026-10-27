import QtQuick
import QtQuick.Effects
import qs.theme

Item {
    id: root
    property string text: ""
    property font font: Qt.font({family:Tokens.clockFont,pixelSize:15,weight:Font.Medium,features:{tnum:1}})
    property color color: Theme.text
    property bool animated: true
    property bool countsDown: false
    Row {
        x:(parent.width-width)/2
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
                property real direction:1
                property bool ready:false
                width:metrics.advanceWidth;height:Math.min(root.height,metrics.height);y:(root.height-height)/2;clip:true
                layer.enabled:digit.progress>0&&digit.progress<1
                layer.effect: MultiEffect {
                    blurEnabled:true;blurMax:2;autoPaddingEnabled:false
                    blur:Math.sin(Math.PI*digit.progress)
                }
                TextMetrics {id:metrics;font:root.font;text:/\d/.test(digit.value)?"0":digit.value}
                function settle():void {motion.stop();shown=value;outgoing="";progress=1;}
                function update():void {
                    if (!ready || motion.running || value===shown) return;
                    if (!root.animated || Tokens.reducedMotion || !visible || !/\d/.test(value)) {shown=value;outgoing="";progress=1;return;}
                    direction=root.countsDown?-1:1;outgoing=shown;shown=value;progress=0;motion.start();
                }
                onValueChanged:update()
                onVisibleChanged:if(!visible)settle()
                Connections {target:Tokens;function onReducedMotionChanged(){if(Tokens.reducedMotion)digit.settle();}}
                Component.onCompleted:{shown=value;outgoing="";progress=1;ready=true;}
                NumberAnimation {
                    id:motion;target:digit;property:"progress";to:1
                    duration:Math.min(220,Tokens.animMedium);easing.type:Easing.OutCubic
                    onFinished:{digit.outgoing="";Qt.callLater(digit.update);}
                }
                PanelText {
                    width:parent.width;height:parent.height;y:-parent.height*digit.progress*digit.direction
                    visible:!!digit.outgoing;text:digit.outgoing;font:root.font;color:root.color
                    horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;elide:Text.ElideNone
                }
                PanelText {
                    width:parent.width;height:parent.height;y:parent.height*(1-digit.progress)*digit.direction
                    text:digit.shown;font:root.font;color:root.color
                    horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;elide:Text.ElideNone
                }
            }
        }
    }
}
