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
    readonly property string lyric: {
        if(!Preferences.mediaLyrics||loadedKey!==trackKey)return "";
        let current="";
        for(const line of lines){if(line.time>Media.position)break;current=line.text;}
        return current;
    }
    readonly property real lineRemaining: {
        if (loadedKey !== trackKey) return 8;
        for (const line of lines) if (line.time > Media.position) return Math.max(1, line.time - Media.position);
        return 8;
    }
    onTrackKeyChanged:{lines=[];loadedKey="";lyricsDelay.restart();}
    onListeningChanged:if(listening)lyricsDelay.restart()
    Connections {target:Preferences;function onMediaLyricsChanged(){if(Preferences.mediaLyrics)lyricsDelay.restart();else{root.lines=[];root.loadedKey="";lyrics.running=false;}}}
    Process {
        id:analyzer;running:root.listening&&Preferences.mediaVisualizer
        command:["cava","-p",Qt.resolvedUrl("../assets/audio/cava.conf").toString().replace("file://","")]
        stdout:SplitParser {onRead:data=>{const values=data.split(";").filter(v=>v.length).slice(0,6).map(v=>Math.max(0,Math.min(1,Number(v)/100)));if(values.length===6)root.bars=values;}}
        onExited:code=>{root.bars=[0,0,0,0,0,0];if(code!==0)root.error="Audio visualizer is unavailable";}
    }
    Timer {id:lyricsDelay;interval:250;onTriggered:{
        if(!root.listening||!Preferences.mediaLyrics||!Media.artist||!Media.title||root.loadedKey===root.trackKey)return;
        if(lyrics.running){restart();return;}
        lyrics.command=["python3",Qt.resolvedUrl("../scripts/lyrics.py").toString().replace("file://",""),JSON.stringify({title:Media.title,artist:Media.artist,duration:Media.length}),root.trackKey];lyrics.running=true;
    }}
    Process {id:lyrics;stdout:StdioCollector {onStreamFinished:{try{const data=JSON.parse(text);if(data.key===root.trackKey){root.loadedKey=data.key;root.lines=data.lines;}}catch(e){}}}}
}
