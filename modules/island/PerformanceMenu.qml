import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell.Io
import qs.services
import qs.theme
import qs.components
ColumnLayout {
    id: root
    spacing: 14
    property var sample: ({})
    property var history: ({cpu:[], memory:[], download:[], upload:[]})
    property var deviceNames: []
    property var diskPaths: []
    property string error: ""
    function bytes(value): string {
        if(value == null) return "—";
        const n = Math.max(0,Number(value));
        return n >= 1073741824 ? (n/1073741824).toFixed(1)+" GiB" : n >= 1048576 ? (n/1048576).toFixed(1)+" MiB" : n >= 1024 ? (n/1024).toFixed(1)+" KiB" : Math.round(n)+" B";
    }
    function ingest(data): void {
        if(data.error){error=data.error;return;}
        sample=data;error="";
        const names=(data.diskIo||[]).map(d=>d.name);
        if(JSON.stringify(names)!==JSON.stringify(deviceNames)) deviceNames=names;
        const paths=(data.disks||[]).map(d=>d.path);
        if(JSON.stringify(paths)!==JSON.stringify(diskPaths)) diskPaths=paths;
        const next={};
        const values={cpu:data.cpu,memory:data.memoryUsed/data.memoryTotal,download:data.download,upload:data.upload};
        for(const d of data.diskIo||[]) values[d.name]=d.busy;
        for(const key of Object.keys(values)) next[key]=values[key]==null ? history[key]||[] : (history[key]||[]).concat([values[key]]).slice(-30);
        history=next;
    }
    Process {
        running: IslandState.menu === "performance" && !Preferences.preview && !Session.locked
        command: ["python3", Qt.resolvedUrl("../../scripts/performance.py").toString().replace("file://", "")]
        stdout: SplitParser { onRead: line => {
            try {root.ingest(JSON.parse(line));}catch(e){root.error="Metrics unavailable";}
        } }
        onExited: code => {if(code!==0 && IslandState.menu==="performance")root.error="Metrics unavailable";}
    }
    PanelHeader {
        title:"Performance"
        Rectangle {width:5;height:5;radius:2.5;color:Theme.accent;visible:!!root.sample.memoryTotal&&!root.error}
    }
    Flickable {
        Layout.fillWidth:true;Layout.fillHeight:true;Layout.minimumHeight:0;implicitHeight:metrics.implicitHeight;clip:true
        contentHeight:metrics.implicitHeight;boundsBehavior:Flickable.StopAtBounds
        ScrollBar.vertical:ScrollBar {}
        ColumnLayout {
            id:metrics;width:parent.width;spacing:12
            RowLayout {
                Layout.fillWidth:true;spacing:10
                Repeater {
                    model:["CPU","Memory"]
                    Rectangle {
                        id:summary
                        required property string modelData
                        readonly property var value:modelData==="CPU"?root.sample.cpu:root.sample.memoryUsed/root.sample.memoryTotal
                        Layout.fillWidth:true;Layout.preferredWidth:1;implicitHeight:116
                        radius:18;color:Theme.withAlpha(Theme.text,.035)
                        border.width:1;border.color:Theme.withAlpha(Theme.text,.045)
                        Column {
                            anchors.left:parent.left;anchors.right:parent.right;anchors.top:parent.top;anchors.margins:14;spacing:5
                            PanelText {text:summary.modelData==="Memory"?"RAM used":summary.modelData;font.pixelSize:12;color:Theme.subtext}
                            Row {spacing:3
                                PanelText {text:Number.isFinite(summary.value)?Math.round(summary.value*100):"—";font.pixelSize:30;font.weight:Font.Medium;font.letterSpacing:-1;font.features:({tnum:1})}
                                PanelText {text:"%";font.pixelSize:13;color:Theme.subtext;anchors.baseline:parent.children[0].baseline}
                            }
                            PanelText {text:summary.modelData==="Memory"?root.bytes(root.sample.memoryUsed)+" / "+root.bytes(root.sample.memoryTotal):"All cores";font.pixelSize:10;color:Theme.subtext}
                        }
                        MetricTrace {anchors.left:parent.left;anchors.right:parent.right;anchors.bottom:parent.bottom;anchors.margins:10;height:23;values:root.history[summary.modelData==="CPU"?"cpu":"memory"]||[]}
                    }
                }
            }
            Repeater {
                model:root.deviceNames
                Rectangle {
                    id:drive
                    required property string modelData
                    readonly property var reading:(root.sample.diskIo||[]).find(d=>d.name===modelData)||({})
                    Layout.fillWidth:true;implicitHeight:100;radius:18
                    color:Theme.withAlpha(Theme.text,.035);border.width:1;border.color:Theme.withAlpha(Theme.text,.045)
                    ColumnLayout {
                        anchors.fill:parent;anchors.margins:12;spacing:6
                        RowLayout {Layout.fillWidth:true
                            PanelText {text:"Disk";font.pixelSize:13;font.weight:Font.Medium}
                            PanelText {Layout.fillWidth:true;text:drive.modelData;font.pixelSize:10;color:Theme.subtext}
                            PanelText {text:drive.reading.busy==null?"—":Math.round(drive.reading.busy*100)+"% active";font.pixelSize:11;color:Theme.subtext;font.features:({tnum:1})}
                        }
                        RowLayout {Layout.fillWidth:true;spacing:14
                            Repeater {model:["read","write"]
                                Column {required property string modelData;Layout.fillWidth:true;Layout.preferredWidth:1;spacing:4
                                    PanelText {text:modelData==="read"?"Read":"Write";font.pixelSize:10;color:Theme.subtext}
                                    PanelText {width:parent.width;text:root.bytes(drive.reading[modelData])+"/s";font.pixelSize:14;font.weight:Font.Medium;font.features:({tnum:1})}
                                }
                            }
                        }
                        MetricTrace {Layout.fillWidth:true;Layout.fillHeight:true;Layout.minimumHeight:12;values:root.history[drive.modelData]||[]}
                    }
                }
            }
            Rectangle {
                Layout.fillWidth:true;implicitHeight:116;radius:18
                color:Theme.withAlpha(Theme.text,.035);border.width:1;border.color:Theme.withAlpha(Theme.text,.045)
                ColumnLayout {anchors.fill:parent;anchors.margins:14;spacing:10
                    PanelText {text:"Network";font.pixelSize:13;font.weight:Font.Medium}
                    RowLayout {Layout.fillWidth:true;spacing:14
                        Repeater {model:["download","upload"]
                            Column {required property string modelData;Layout.fillWidth:true;Layout.preferredWidth:1;spacing:4
                                PanelText {text:modelData==="download"?"↓  Download":"↑  Upload";font.pixelSize:10;color:Theme.subtext}
                                PanelText {width:parent.width;text:root.bytes(root.sample[modelData])+"/s";font.pixelSize:14;font.weight:Font.Medium;font.features:({tnum:1})}
                            }
                        }
                    }
                    Item {Layout.fillWidth:true;Layout.fillHeight:true;Layout.minimumHeight:20
                        readonly property real peak:Math.max(1024,...root.history.download,...root.history.upload)
                        MetricTrace {anchors.fill:parent;values:root.history.download;ceiling:parent.peak}
                        MetricTrace {anchors.fill:parent;values:root.history.upload;ceiling:parent.peak;stroke:Theme.subtext}
                    }
                }
            }
            Repeater {
                model:root.diskPaths
                ColumnLayout {
                    required property string modelData
                    readonly property var disk:(root.sample.disks||[]).find(d=>d.path===modelData)||({used:0,total:1})
                    Layout.fillWidth:true;Layout.leftMargin:3;Layout.rightMargin:3;spacing:7
                    RowLayout {Layout.fillWidth:true
                        PanelText {Layout.fillWidth:true;text:modelData==="/"?"System storage":"Home storage";font.pixelSize:11;color:Theme.subtext}
                        PanelText {text:root.bytes(disk.used)+" / "+root.bytes(disk.total);font.pixelSize:10;color:Theme.subtext}
                    }
                    Rectangle {Layout.fillWidth:true;height:3;radius:1.5;color:Theme.withAlpha(Theme.text,.08)
                        Rectangle {height:3;radius:1.5;width:parent.width*Math.min(1,disk.used/disk.total);color:Theme.withAlpha(Theme.accent,.65)}
                    }
                }
            }
            PanelText {Layout.fillWidth:true;visible:!!root.error;text:root.error;wrapMode:Text.Wrap;color:Theme.subtext;font.pixelSize:12}
        }
    }
}
