pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Pipewire

Singleton {
    id: root

    readonly property var outputs: Pipewire.nodes.values.filter(n=>n.audio&&!n.isStream&&n.isSink)
    readonly property var inputs: Pipewire.nodes.values.filter(n=>n.audio&&!n.isStream&&!n.isSink)
    readonly property var streams: Pipewire.nodes.values.filter(n=>n.audio&&n.isStream)
    // Quickshell exposes media classes as PwNodeType flags, not strings.
    readonly property var microphoneStreams: Pipewire.nodes.values.filter(n=>n.type === PwNodeType.AudioInStream && Pipewire.links.values.some(link=>link.target === n && (link.source?.type & PwNodeType.Audio) && (link.source?.type & PwNodeType.Source)))
    readonly property var videoCaptureStreams: Array.from(new Set(Pipewire.links.values.filter(link => (link.source?.type & PwNodeType.Video) && (link.source?.type & PwNodeType.Source) && link.target).map(link => link.target)))
    property var directCameras: []
    readonly property var captureStreams: microphoneStreams.concat(videoCaptureStreams, directCameras)
    readonly property bool videoCapture: videoCaptureStreams.length > 0
    readonly property var captureSources: Array.from(new Set(Pipewire.links.values.filter(link => root.videoCaptureStreams.includes(link.target)).map(link => link.source).filter(Boolean)))
    readonly property bool cameraCapture: directCameras.length > 0 || videoCaptureStreams.some(node => captureKind(node) === "Camera")
    readonly property bool screenCapture: videoCaptureStreams.some(node => captureKind(node) === "Screen")
    readonly property string indicatorKind: cameraCapture ? "camera" : videoCapture ? (screenCapture ? "screen" : "video") : microphoneStreams.length ? "microphone" : ""
    readonly property string captureSummary: {
        const kinds = Array.from(new Set(captureStreams.map(node => captureKind(node) === "Screen" ? "Screen sharing" : captureKind(node) === "Video" ? "Video capture" : captureKind(node))));
        const apps = Array.from(new Set(captureStreams.map(captureLabel)));
        return kinds.join(" + ") + (apps.length ? " · " + apps.join(", ") : "");
    }
    function captureLabel(node): string { return node.label || node.properties?.["application.name"] || node.description || node.nickname || node.name || "Application"; }
    function captureKind(node): string {
        if (node.directCamera) return "Camera";
        if (node.type === PwNodeType.AudioInStream) return "Microphone";
        const sources = Pipewire.links.values.filter(link => link.target === node).map(link => link.source);
        const nodes = [node].concat(sources);
        // Only explicit camera metadata gets green; unknown video remains identifiable as video.
        if (nodes.some(n => /camera/i.test(n?.properties?.["media.role"] || "") || /^(v4l2|libcamera)$/.test(n?.properties?.["device.api"] || "") || !!n?.properties?.["api.v4l2.path"])) return "Camera";
        if (nodes.some(n => /screen/i.test(n?.properties?.["media.role"] || "") || /screen.?cast|screen.?shar|xdg-desktop-portal/i.test(n?.name || ""))) return "Screen";
        return "Video";
    }
    readonly property PwNode source: Pipewire.defaultAudioSource
    function setDefault(node, output: bool): void { if(Quickshell.env("MODESTY_PREVIEW")==="1")return;if(output)Pipewire.preferredDefaultAudioSink=node;else Pipewire.preferredDefaultAudioSource=node; }
    function setNodeVolume(node, value: real): void { if(Quickshell.env("MODESTY_PREVIEW")!=="1"&&node?.audio)node.audio.volume=Math.max(0,Math.min(1.5,value)); }
    function muteNode(node): void { if(Quickshell.env("MODESTY_PREVIEW")!=="1"&&node?.audio)node.audio.muted=!node.audio.muted; }
    readonly property PwNode sink: Pipewire.defaultAudioSink
    readonly property bool muted: !!sink?.audio?.muted
    readonly property real volume: sink?.audio?.volume ?? 0

    // Keep the default sink's properties bound (required by the pipewire service)
    PwObjectTracker {
        objects: Array.from(new Set((IslandState.state === "sound" ? Pipewire.nodes.values.filter(n=>n.audio) : [root.sink,root.source]).concat(root.microphoneStreams, root.videoCaptureStreams, root.captureSources).filter(Boolean)))
    }
    readonly property bool cameraObserverEnabled: Preferences.privacyRadar && Quickshell.env("MODESTY_PREVIEW") !== "1"
    onCameraObserverEnabledChanged: if (!cameraObserverEnabled) { cameraRetry.stop(); directCameras = []; }
    Timer { id: cameraRetry; interval: 5000 }
    Process {
        id: cameraObserver
        running: root.cameraObserverEnabled && !cameraRetry.running
        command: ["python3", Qt.resolvedUrl("../scripts/privacy-camera.py").toString().replace("file://", "")]
        stdout: SplitParser {onRead: line => {if (!root.cameraObserverEnabled) return; try {root.directCameras = JSON.parse(line);} catch (e) {}}}
        onExited: {
            root.directCameras = [];
            if (root.cameraObserverEnabled) {
                console.warn("Camera observer stopped; retrying in five seconds.");
                cameraRetry.restart();
            }
        }
    }

    function setVolume(v: real): void {
        if (Quickshell.env("MODESTY_PREVIEW") === "1") return;
        if (sink?.audio) {
            sink.audio.muted = false;
            sink.audio.volume = Math.max(0, Math.min(1.5, v));
        }
    }

}
