import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.components
import qs.services
import qs.theme
import "../../services/ModelDiff.js" as ModelDiff

ColumnLayout {
    id: root
    spacing: 16
    signal explainRequested()
    property bool observing: false
    property var sample: ({})
    property var history: ({cpu:[], memory:[], disk:[], network:[]})
    property string sortBy: "cpu"
    property string error: ""
    property string stopping: ""
    property string stopMessage: ""
    property bool stopFailed: false
    property bool stopReceived: false
    function stopProcess(row): void {
        if(!row.canStop||terminator.running||Preferences.preview||Session.isLocked()||Session.secure)return;
        stopping=row.key;stopMessage="";stopFailed=false;stopReceived=false;
        terminator.command=["python3",Qt.resolvedUrl("../../scripts/performance.py").toString().replace("file://",""),"--terminate",String(row.pid),row.started];
        terminator.running=true;
    }
    readonly property bool ready: sample.cpu !== undefined && sample.cpu !== null
    readonly property string finding: !ready ? "Measuring…" : sample.pressure?.memory > .05 ? "Memory pressure" : sample.pressure?.io > .1 ? "Storage waits" : sample.cpu > .85 ? "High CPU load" : "Balanced"
    readonly property string explanation: "Live local activity. CPU per process: 100% = one core. Heavy use alone does not prove a fault."
    function bytes(n, compact=false): string {
        if(compact&&n>=1024){const scale=n>=1073741824?1073741824:n>=1048576?1048576:1024;return (n/scale).toFixed(n/scale<10?1:0).replace(/\.0$/," ").trim()+" "+(scale===1073741824?"GiB":scale===1048576?"MiB":"KiB");}
        return n == null ? "—" : n >= 1073741824 ? (n/1073741824).toFixed(1)+" GiB" : n >= 1048576 ? (n/1048576).toFixed(1)+" MiB" : n >= 1024 ? Math.round(n/1024)+" KiB" : Math.round(n)+" B";
    }
    function sync(): void {
        const rows=(sample.processes||[]).slice().sort((a,b)=>(b[sortBy]||0)-(a[sortBy]||0)).slice(0,4);
        ModelDiff.reconcile(processRows, rows.map(p=>({key:String(p.pid)+":"+(p.started||""),name:p.name,pid:p.pid,started:p.started||"",canStop:!!p.canStop,cpu:p.cpu,memory:p.memory,io:p.io??-1})), "key");
    }
    function ingest(data): void {
        if(data.error){error="Metrics unavailable";return;}
        sample=data;error="";
        const rates={cpu:data.cpu,memory:data.memoryUsed/data.memoryTotal,disk:(data.diskIo||[]).reduce((sum,d)=>sum+(d.read||0)+(d.write||0),0),network:(data.download||0)+(data.upload||0)};
        const next={};
        for(const key of Object.keys(rates)) next[key]=rates[key]==null?history[key]:(history[key]||[]).concat([rates[key]]).slice(-30);
        history=next;sync();
    }
    onSortByChanged: sync()
    ListModel {id:processRows}
    Process {
        running: root.observing && !Preferences.preview && !Session.isLocked()
        command: ["python3", Qt.resolvedUrl("../../scripts/performance.py").toString().replace("file://",""), "--processes"]
        stdout: SplitParser {onRead:line=>{try{root.ingest(JSON.parse(line));}catch(e){root.error="Metrics unavailable";}}}
        onExited:code=>{if(code!==0&&root.observing)root.error="Metrics unavailable";}
    }
    Process {
        id:terminator
        stdout:StdioCollector {onStreamFinished:{
            try{
                const result=JSON.parse(text);root.stopReceived=true;root.stopFailed=!result.ok;
                root.stopMessage=result.ok?"Stop requested · "+result.name:result.error||"Could not stop process";
            }catch(e){root.stopReceived=false;}
        }}
        onExited:{
            if(!root.stopReceived){root.stopFailed=true;root.stopMessage="Could not stop process";}
            root.stopping="";clearStop.restart();
        }
    }
    Timer {id:clearStop;interval:5000;onTriggered:{root.stopMessage="";root.stopFailed=false;}}
    RowLayout {
        Layout.fillWidth:true;spacing:8
        Repeater {
            model:[{key:"cpu",label:"CPU"},{key:"memory",label:"RAM"},{key:"disk",label:"Disk"},{key:"network",label:"Network"}]
            Rectangle {
                id:metric
                required property var modelData
                Layout.fillWidth:true;Layout.preferredWidth:1;implicitHeight:100
                radius:12;color:Theme.withAlpha(Theme.text,.035)
                PanelText {x:10;y:11;text:metric.modelData.key==="memory"?"RAM used":metric.modelData.label;font.pixelSize:10;color:Theme.subtext}
                PanelText {
                    x:10;y:29;width:parent.width-20;font.pixelSize:13;font.weight:Font.Medium;font.features:({tnum:1})
                    text:!root.ready?"—":metric.modelData.key==="cpu"?Math.round(root.sample.cpu*100)+"%":metric.modelData.key==="memory"?root.bytes(root.sample.memoryUsed):root.bytes(metric.modelData.key==="disk"?(root.sample.diskIo||[]).reduce((sum,d)=>sum+(d.read||0)+(d.write||0),0):(root.sample.download||0)+(root.sample.upload||0),true)+"/s"
                }
                PanelText {x:10;y:49;width:parent.width-20;visible:metric.modelData.key==="memory";text:root.ready?"of "+root.bytes(root.sample.memoryTotal)+" usable":"";font.pixelSize:9;color:Theme.subtext}
                MetricTrace {x:10;y:72;width:parent.width-20;height:18;values:root.history[metric.modelData.key]||[];ceiling:["cpu","memory"].includes(metric.modelData.key)?1:Math.max(1024,...values)}
            }
        }
    }
    RowLayout {
        Layout.fillWidth:true;spacing:8
        Item {
            id:sorter
            Layout.fillWidth:true;implicitHeight:30
            readonly property var choices:[{key:"cpu",label:"CPU"},{key:"memory",label:"Memory"},{key:"io",label:"Disk I/O"}]
            readonly property real cell:Math.min(80,width/3)
            Rectangle {
                x:sorter.choices.findIndex(c=>c.key===root.sortBy)*sorter.cell;y:0;width:sorter.cell;height:30;radius:9
                color:Theme.withAlpha(Theme.text,.035);border.width:1;border.color:Theme.withAlpha(Theme.accent,.25)
                Behavior on x {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animFast;reversingMode:SmoothedAnimation.Immediate}}
            }
            Row {
                Repeater {
                    model:sorter.choices
                    AbstractButton {
                        required property var modelData
                        width:sorter.cell;height:30;hoverEnabled:true
                        Accessible.name:"Sort by "+modelData.label
                        onClicked:root.sortBy=modelData.key
                        background:Rectangle {radius:9;color:Theme.withAlpha(Theme.text,parent.hovered?.04:0);border.width:parent.activeFocus?1:0;border.color:Theme.accent}
                        contentItem:PanelText {text:parent.modelData.label;font.pixelSize:11;color:root.sortBy===parent.modelData.key?Theme.text:Theme.subtext;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
                        HoverHandler {cursorShape:Qt.PointingHandCursor}
                    }
                }
            }
        }
        IconButton {icon:"luma";size:15;label:"Explain with AI · uses answer quota";enabled:Preferences.searchAiEnabled&&!Luma.busy;onClicked:root.explainRequested()}
        IconButton {icon:"open_in_new";size:14;label:"Performance details";onClicked:IslandState.openMenu("performance")}
    }
    ListView {
        id:processList
        Layout.fillWidth:true;Layout.preferredHeight:count*36
        model:processRows;interactive:false;clip:true
        Behavior on Layout.preferredHeight {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animFast;reversingMode:SmoothedAnimation.Immediate}}
        add:Transition {enabled:!Tokens.reducedMotion;NumberAnimation {properties:"opacity";from:0;to:1;duration:Tokens.animFast}}
        remove:Transition {enabled:!Tokens.reducedMotion;NumberAnimation {properties:"opacity";to:0;duration:Tokens.animFast}}
        displaced:Transition {enabled:!Tokens.reducedMotion;NumberAnimation {properties:"y";duration:Tokens.animFast;easing.type:Easing.OutCubic}}
        delegate:Item {
            id:processRow
            required property var model
            width:processList.width;height:36
            Rectangle {anchors.fill:parent;radius:8;color:Theme.withAlpha(Theme.text,rowHover.hovered?.035:0);Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
            HoverHandler {id:rowHover;blocking:false}
            RowLayout {
                anchors.fill:parent;anchors.leftMargin:8;anchors.rightMargin:2;spacing:10
                PanelText {Layout.fillWidth:true;text:processRow.model.name;font.pixelSize:12;elide:Text.ElideRight}
                PanelText {text:root.sortBy==="cpu"?(processRow.model.cpu*100).toFixed(1)+"%":root.sortBy==="memory"?root.bytes(processRow.model.memory):processRow.model.io<0?"—":root.bytes(processRow.model.io)+"/s";font.pixelSize:12;font.features:({tnum:1});color:Theme.subtext}
                Item {
                    Layout.preferredWidth:30;Layout.preferredHeight:30
                    IconButton {anchors.centerIn:parent;icon:"close";size:13;color:Theme.subtext;visible:processRow.model.canStop&&root.stopping!==processRow.model.key;enabled:!terminator.running;label:"End "+processRow.model.name+" · unsaved changes may be lost";onClicked:root.stopProcess(processRow.model)}
                    ActivityPulse {anchors.centerIn:parent;visible:root.stopping===processRow.model.key;running:visible}
                }
            }
        }
    }
    RowLayout {
        Layout.fillWidth:true;spacing:7
        Rectangle {width:4;height:4;radius:2;color:root.error||root.stopFailed?Theme.red:Theme.accent}
        PanelText {Layout.fillWidth:true;text:root.error||root.stopMessage||root.finding;font.pixelSize:11;color:Theme.subtext}
        IconButton {icon:"info";size:13;label:root.explanation;color:Theme.subtext}
    }
}
