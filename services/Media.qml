pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Services.Mpris
Singleton {
    id: root
    readonly property var players: Mpris.players.values
    function isSpotify(player): bool {
        return String(player.desktopEntry||"").toLowerCase().includes("spotify")
            || String(player.dbusName||"").toLowerCase().startsWith("org.mpris.mediaplayer2.spotify")
            || String(player.identity||"").toLowerCase()==="spotify";
    }
    // Keep the music player stable while it is playing; a paused Spotify must
    // never hide an actively playing browser or another player.
    readonly property MprisPlayer active: players.find(p => isSpotify(p) && p.isPlaying)
        ?? players.find(p => p.isPlaying) ?? players.find(p => isSpotify(p)) ?? players[0] ?? null
    readonly property bool playing: !!active?.isPlaying
    readonly property string title: active?.trackTitle ?? ""
    readonly property string artist: active?.trackArtist ?? ""
    readonly property string artUrl: active?.trackArtUrl ?? ""
    // A registered browser alone is not a media session. Keep paused tracks
    // available for resume, including streams without a duration or artwork.
    readonly property bool hasSession: !!active && (playing || title.trim().length > 0 || artist.trim().length > 0)
    readonly property real length: active?.length ?? 0
    readonly property bool canGoNext: active?.canGoNext ?? false
    readonly property bool canGoPrevious: active?.canGoPrevious ?? false
    readonly property bool canSeek: active?.canSeek ?? false
    readonly property bool canRepeat: !!active?.canControl && !!active?.loopSupported
    readonly property int loopState: active?.loopState ?? MprisLoopState.None
    readonly property bool repeating: loopState !== MprisLoopState.None
    readonly property string repeatIcon: loopState === MprisLoopState.Track ? "repeat_one" : "repeat"
    readonly property string repeatLabel: !canRepeat ? "Repeat unavailable for this player" : loopState === MprisLoopState.Track ? "Repeat one · click to turn off" : loopState === MprisLoopState.Playlist ? "Repeat all · click to repeat one" : "Repeat off · click to repeat all"
    function cycleRepeat(): void {
        if (preview || !canRepeat) return;
        active.loopState = loopState === MprisLoopState.None ? MprisLoopState.Playlist : loopState === MprisLoopState.Playlist ? MprisLoopState.Track : MprisLoopState.None;
    }
    property real position: 0
    property real syncTime: Date.now()
    property real syncPosition: 0
    readonly property real progress: length > 0 ? Math.min(1, position / length) : 0
    readonly property bool preview: Quickshell.env("MODESTY_PREVIEW") === "1"
    function sync(): void { syncPosition = active?.position ?? 0; position = syncPosition; syncTime = Date.now(); }
    function togglePlaying(): void { if (!preview && active?.canTogglePlaying) active.togglePlaying(); }
    function play(player:var): bool {const target=player||active;if(preview||!target)return false;if(target.isPlaying)return true;if(!target.canPlay)return false;target.play();return true;}
    function pause(player:var): bool {const target=player||active;if(preview||!target)return false;if(!target.isPlaying)return true;if(!target.canPause)return false;target.pause();return true;}
    function stop(): void { if (!preview && active?.canControl) active.stop(); }
    function next(): void { if (!preview && canGoNext) active.next(); }
    function previous(): void { if (!preview && canGoPrevious) active.previous(); }
    function seekTo(seconds: real): void { if (!preview && canSeek && length > 0) { active.position = Math.max(0, Math.min(length, seconds)); sync(); } }
    onActiveChanged: sync()
    Connections {
        target: root.active
        function onPositionChanged() { root.sync(); }
        function onTrackChanged() { root.sync(); }
        function onIsPlayingChanged() { root.sync(); }
    }
    // Hidden lyrics do not need position ticks. The first visible tick catches
    // up from the MPRIS timestamp, preserving the displayed playhead and lyrics.
    Timer { interval: ["media","quicksettings"].includes(IslandState.state)?100:250; repeat:true;triggeredOnStart:true;running:root.playing&&(["media","quicksettings"].includes(IslandState.state)||(LiveMedia.listening&&Preferences.mediaLyrics&&LiveMedia.hasSyncedLyrics));onTriggered:root.position=Math.min(root.length||Infinity,root.syncPosition+(Date.now()-root.syncTime)/1000) }
}
