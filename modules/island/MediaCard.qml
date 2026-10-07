import QtQuick
import QtQuick.Controls
import qs.components
import qs.services
import qs.theme
Rectangle {
    id:root
    radius:Math.max(12,Preferences.expandedRadius-Preferences.innerPadding)
    color:Theme.surfaceSolid;antialiasing:true
    // Artwork clipping is decorative, never an ancestor of the player controls.
    Art {anchors.fill:parent;source:Media.artUrl;radius:root.radius}
    Rectangle {anchors.fill:parent;color:Media.artUrl?Theme.withAlpha(Theme.surfaceSolid,.93):Theme.surfaceSolid;radius:root.radius}
    Art {x:12;y:12;width:88;height:88;source:Media.artUrl;radius:10;visible:!!Media.active}
    Column {x:114;y:13;width:parent.width-126;spacing:4;visible:!!Media.active
        PanelText {width:parent.width;text:Media.title||"Nothing playing";font.pixelSize:15;font.weight:Font.Medium;maximumLineCount:2;wrapMode:Text.Wrap}
        PanelText {width:parent.width;visible:!!Media.artist;text:Media.artist;font.pixelSize:12;color:Theme.subtext}
        PanelText {width:parent.width;text:Media.active?.trackAlbum||Media.active?.identity||"";font.pixelSize:11;color:Theme.subtext;opacity:.8}
    }
    Slider {
        id:seek;x:12;y:parent.height-57;width:parent.width-24;height:19;padding:0;hoverEnabled:true
        visible:!!Media.active
        Binding {target:seek;property:"value";value:Media.progress;when:!seek.pressed;restoreMode:Binding.RestoreNone}
        enabled:Media.canSeek;onMoved:Media.seekTo(value*Media.length);Accessible.name:"Playback position"
        background:Rectangle {y:(seek.height-height)/2;width:seek.width;height:3;radius:1.5;color:Theme.withAlpha(Theme.text,.16)
            Rectangle {width:parent.width*seek.visualPosition;height:3;radius:1.5;color:Theme.accent}
        }
        handle:Rectangle {x:seek.visualPosition*(seek.width-width);y:(seek.height-height)/2;width:8;height:8;radius:4;color:Theme.accent;opacity:seek.hovered||seek.pressed?1:0;Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}}
    }
    function duration(s:real):string {return Math.floor(s/60)+":"+String(Math.floor(s%60)).padStart(2,"0");}
    PanelText {visible:!!Media.active;x:12;anchors.verticalCenter:playback.verticalCenter;text:root.duration(seek.pressed?seek.value*Media.length:Media.position);font.pixelSize:11;font.features:({tnum:1});color:Theme.subtext}
    PanelText {visible:!!Media.active;anchors.right:parent.right;anchors.rightMargin:12;anchors.verticalCenter:playback.verticalCenter;text:root.duration(Media.length);font.pixelSize:11;font.features:({tnum:1});color:Theme.subtext}
    Column {anchors.centerIn:parent;spacing:10;visible:!Media.active
        Icon {anchors.horizontalCenter:parent.horizontalCenter;icon:"music_note";size:28;color:Theme.subtext}
        PanelText {text:"No media playing";font.pixelSize:14;color:Theme.subtext}
    }
    Row {id:playback;visible:!!Media.active;anchors.horizontalCenter:parent.horizontalCenter;anchors.bottom:parent.bottom;anchors.bottomMargin:7;spacing:6
        IconButton {anchors.verticalCenter:parent.verticalCenter;icon:"skip_previous";label:"Previous track";size:14;enabled:Media.canGoPrevious;onClicked:Media.previous()}
        IconButton {icon:Media.playing?"pause":"play_arrow";label:Media.playing?"Pause":"Play";size:18;background:Theme.accent;color:Theme.accentText;enabled:!!Media.active;onClicked:Media.togglePlaying()}
        IconButton {anchors.verticalCenter:parent.verticalCenter;icon:"skip_next";label:"Next track";size:14;enabled:Media.canGoNext;onClicked:Media.next()}
        RepeatButton {anchors.verticalCenter: parent.verticalCenter; size: 14}
    }
}
