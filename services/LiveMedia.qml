pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Singleton {
    id:root
    property bool visibleOnScreen:false
    readonly property bool expanded:Preferences.liveMedia&&(Preferences.mediaVisualizer||Preferences.mediaLyrics)&&Media.playing
    readonly property bool hasSyncedLyrics:loadedKey===trackKey&&lines.some(line=>line.text.trim().length>0)
    readonly property bool compactTitle:Preferences.compactMissingLyrics&&Preferences.mediaLyrics&&Preferences.mediaVisualizer&&!hasSyncedLyrics
    readonly property bool listening:visibleOnScreen&&expanded&&!Preferences.preview
    property var bars:[0,0,0,0,0,0]
    property var lines:[]
    property string loadedKey:""
    property string error:""
    readonly property string trackKey:Media.artist+"\n"+Media.title
    // Validate ordering once per lyric payload. Older/malformed caches retain
    // the previous first-future-cue behavior through the linear fallback.
    readonly property bool orderedLines:lines.every((line,index)=>Number.isFinite(line.time)&&(index===0||line.time>=lines[index-1].time))
    readonly property int lyricIndex: {
        if (loadedKey !== trackKey) return -1;
        const position = Media.position;
        if (!orderedLines) {
            for (let i = 0; i < lines.length; i++) if (lines[i].time > position) return i - 1;
            return lines.length - 1;
        }
        let low = 0, high = lines.length;
        while (low < high) {
            const middle = Math.floor((low + high) / 2);
            if (lines[middle].time <= position) low = middle + 1;
            else high = middle;
        }
        return low - 1;
    }
    readonly property string lyric: {
        if(!Preferences.mediaLyrics||loadedKey!==trackKey)return "";
        return lyricIndex >= 0 ? lines[lyricIndex].text : "";
    }
    readonly property real lineRemaining: {
        if (loadedKey !== trackKey) return 8;
        const next = lines[lyricIndex + 1];
        return next ? Math.max(1, next.time - Media.position) : 8;
    }
    onTrackKeyChanged:{lines=[];loadedKey="";lyricsDelay.restart();}
    onListeningChanged:if(listening)lyricsDelay.restart()
    Connections {target:Preferences;function onMediaLyricsChanged(){if(Preferences.mediaLyrics)lyricsDelay.restart();else{root.lines=[];root.loadedKey="";lyrics.running=false;}}}
    function receiveBars(data: string): void {
        const values = data.split(";").filter(v=>v.length).slice(0,6).map(v=>Math.max(0,Math.min(1,Number(v)/100)));
        if (values.length === 6 && values.every(Number.isFinite) && values.some((value,index)=>value!==bars[index])) bars = values;
    }
    Process {
        id:analyzer;running:root.listening&&Preferences.mediaVisualizer
        command:["cava","-p",Qt.resolvedUrl("../assets/audio/cava.conf").toString().replace("file://","")]
        stdout:SplitParser {onRead:data=>root.receiveBars(data)}
        onExited:code=>{root.bars=[0,0,0,0,0,0];if(code!==0)root.error="Audio visualizer is unavailable";}
    }
    Timer {id:lyricsDelay;interval:250;onTriggered:{
        if(!root.listening||!Preferences.mediaLyrics||!Media.artist||!Media.title||root.loadedKey===root.trackKey)return;
        if(lyrics.running){restart();return;}
        lyrics.command=["python3",Qt.resolvedUrl("../scripts/lyrics.py").toString().replace("file://",""),JSON.stringify({title:Media.title,artist:Media.artist,duration:Media.length}),root.trackKey];lyrics.running=true;
    }}
    Process {id:lyrics;stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.key===root.trackKey){root.loadedKey=data.key;root.lines=data.lines;}}catch(e){}}}}
}
