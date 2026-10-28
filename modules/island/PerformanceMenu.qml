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
        objectName:"performanceCollector"
        running: IslandState.menu === "performance" && !Preferences.preview && !Session.locked
        command: ["python3", Qt.resolvedUrl("../../scripts/performance.py").toString().replace("file://", "")]
        stdout: SplitParser { onRead: line => {
            try {root.ingest(JSON.parse(line));}catch(e){root.error="Metrics unavailable";}
        } }
        onExited: code => {if(code!==0 && IslandState.menu==="performance")root.error="Metrics unavailable";}
    }
    PanelHeader {
        title:"Performance"
        Rectangle {objectName:"performanceLive";width:5;height:5;radius:2.5;color:Theme.accent;visible:!!root.sample.memoryTotal&&!root.error}
    }
    Flickable {
        id:scroll;objectName:"performanceScroll"
        Layout.fillWidth:true;Layout.fillHeight:true;Layout.minimumHeight:0;implicitHeight:metrics.implicitHeight;clip:true
        contentHeight:metrics.implicitHeight;boundsBehavior:Flickable.StopAtBounds
        activeFocusOnTab:true
        Keys.onPressed:event=>{
            if(event.key===Qt.Key_Down||event.key===Qt.Key_PageDown) contentY=Math.min(Math.max(0,contentHeight-height),contentY+(event.key===Qt.Key_Down?40:height));
            else if(event.key===Qt.Key_Up||event.key===Qt.Key_PageUp) contentY=Math.max(0,contentY-(event.key===Qt.Key_Up?40:height));
            else if(event.key===Qt.Key_Home) contentY=0;
            else if(event.key===Qt.Key_End) contentY=Math.max(0,contentHeight-height);
            else return;
            event.accepted=true;
        }
        ScrollBar.vertical:ScrollBar {}
        ColumnLayout {
            id:metrics;width:scroll.width;spacing:10
            RowLayout {
                Layout.fillWidth:true;spacing:18
                Repeater {
                    model:["CPU","Memory"]
                    ColumnLayout {
                        id:summary
                        required property string modelData
                        readonly property var value:modelData==="CPU"?root.sample.cpu:root.sample.memoryUsed/root.sample.memoryTotal
                        Layout.fillWidth:true;Layout.preferredWidth:1;spacing:3
                        PanelText {text:summary.modelData==="Memory"?"RAM used":summary.modelData;font.pixelSize:11;color:Theme.subtext}
                        Row {spacing:3
                            PanelText {objectName:summary.modelData+"Percent";text:Number.isFinite(summary.value)?Math.round(summary.value*100):"—";font.pixelSize:28;font.weight:Font.Medium;font.letterSpacing:-1;font.features:({tnum:1})}
                            PanelText {text:"%";font.pixelSize:13;color:Theme.subtext;anchors.baseline:parent.children[0].baseline}
                        }
                        PanelText {objectName:summary.modelData+"Detail";Layout.fillWidth:true;text:summary.modelData==="Memory"?root.bytes(root.sample.memoryUsed)+" / "+root.bytes(root.sample.memoryTotal):"All cores";font.pixelSize:10;color:Theme.subtext}
                        MetricTrace {objectName:summary.modelData+"History";Layout.fillWidth:true;implicitHeight:18;values:root.history[summary.modelData==="CPU"?"cpu":"memory"]||[]}
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth:true;spacing:6;visible:root.deviceNames.length>0
                Rectangle {Layout.fillWidth:true;implicitHeight:1;color:Theme.withAlpha(Theme.text,.07)}
                PanelText {text:"Disk activity";font.pixelSize:11;color:Theme.subtext}
                Repeater {
                    model:root.deviceNames
                    ColumnLayout {
                        id:drive
                        required property string modelData
                        objectName:"drive-"+modelData
                        readonly property var reading:(root.sample.diskIo||[]).find(d=>d.name===modelData)||({})
                        Layout.fillWidth:true;spacing:3
                        RowLayout {Layout.fillWidth:true;spacing:8
                            PanelText {
                                objectName:"driveName-"+drive.modelData;Layout.fillWidth:true;text:drive.modelData;font.pixelSize:12;font.weight:Font.Medium
                                HoverHandler {id:driveHover}
                                ToolTip.visible:driveHover.hovered;ToolTip.text:text
                            }
                            PanelText {objectName:"driveBusy-"+drive.modelData;text:drive.reading.busy==null?"—":Math.round(drive.reading.busy*100)+"% active";font.pixelSize:11;color:Theme.subtext;font.features:({tnum:1})}
                        }
                        RowLayout {Layout.fillWidth:true;spacing:10
                            Repeater {model:["read","write"]
                                RowLayout {
                                    required property string modelData
                                    Layout.fillWidth:true;Layout.preferredWidth:1;spacing:5
                                    PanelText {text:modelData==="read"?"Read":"Write";font.pixelSize:10;color:Theme.subtext}
                                    PanelText {objectName:drive.modelData+"-"+modelData;Layout.fillWidth:true;text:root.bytes(drive.reading[modelData])+"/s";font.pixelSize:11;font.features:({tnum:1})}
                                }
                            }
                        }
                        MetricTrace {objectName:"driveHistory-"+drive.modelData;Layout.fillWidth:true;implicitHeight:12;values:root.history[drive.modelData]||[]}
                    }
                }
            }
            ColumnLayout {
                id:network
                readonly property real peak:Math.max(1024,...root.history.download,...root.history.upload)
                Layout.fillWidth:true;spacing:6
                Rectangle {Layout.fillWidth:true;implicitHeight:1;color:Theme.withAlpha(Theme.text,.07)}
                PanelText {text:"Network";font.pixelSize:11;color:Theme.subtext}
                RowLayout {Layout.fillWidth:true;spacing:18
                    Repeater {model:["download","upload"]
                        ColumnLayout {
                            required property string modelData
                            Layout.fillWidth:true;Layout.preferredWidth:1;spacing:4
                            PanelText {text:modelData==="download"?"↓  Download":"↑  Upload";font.pixelSize:10;color:Theme.subtext}
                            PanelText {objectName:modelData+"Rate";Layout.fillWidth:true;text:root.bytes(root.sample[modelData])+"/s";font.pixelSize:14;font.weight:Font.Medium;font.features:({tnum:1})}
                            MetricTrace {objectName:modelData+"History";Layout.fillWidth:true;implicitHeight:18;values:root.history[modelData];ceiling:network.peak;stroke:modelData==="download"?Theme.accent:Theme.subtext}
                        }
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth:true;spacing:6;visible:root.diskPaths.length>0
                Rectangle {Layout.fillWidth:true;implicitHeight:1;color:Theme.withAlpha(Theme.text,.07)}
                PanelText {text:"Storage";font.pixelSize:11;color:Theme.subtext}
                Repeater {
                    model:root.diskPaths
                    ColumnLayout {
                        id:storage
                        required property string modelData
                        objectName:"storage-"+modelData
                        readonly property var disk:(root.sample.disks||[]).find(d=>d.path===modelData)||({})
                        Layout.fillWidth:true;spacing:3
                        RowLayout {Layout.fillWidth:true;spacing:8
                            PanelText {Layout.fillWidth:true;text:storage.modelData==="/"?"System storage":"Home storage";font.pixelSize:11}
                            PanelText {objectName:"storageUsage-"+storage.modelData;text:root.bytes(storage.disk.used)+" / "+root.bytes(storage.disk.total);font.pixelSize:10;color:Theme.subtext;font.features:({tnum:1})}
                        }
                        PanelText {
                            objectName:"storagePath-"+storage.modelData;Layout.fillWidth:true;text:storage.modelData;font.pixelSize:10;color:Theme.subtext
                            HoverHandler {id:pathHover}
                            ToolTip.visible:pathHover.hovered;ToolTip.text:text
                        }
                        Rectangle {Layout.fillWidth:true;implicitHeight:3;radius:1.5;color:Theme.withAlpha(Theme.text,.08)
                            Rectangle {objectName:"storageFill-"+storage.modelData;height:3;radius:1.5;width:parent.width*(storage.disk.total>0&&storage.disk.used!=null?Math.max(0,Math.min(1,storage.disk.used/storage.disk.total)):0);color:Theme.withAlpha(Theme.accent,.65)}
                        }
                    }
                }
            }
            PanelText {objectName:"performanceStatus";Layout.fillWidth:true;visible:!!root.error||!root.sample.memoryTotal;text:root.error||"Waiting for metrics…";wrapMode:Text.Wrap;color:Theme.subtext;font.pixelSize:12}
        }
    }
}
