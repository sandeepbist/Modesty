import QtQuick
import QtQuick.Controls
import qs.components
import qs.services
import qs.theme
Rectangle {
    id:root
    readonly property real viewportHeight:Math.min(height,parent?.viewportHeight??height)
    radius:Math.max(12,Preferences.expandedRadius-Preferences.innerPadding)
    color:"transparent";antialiasing:true
    function duration(s:real):string {return Math.floor(s/60)+":"+String(Math.floor(s%60)).padStart(2,"0");}
    // Artwork clipping is decorative, never an ancestor of the player controls.
    Rectangle {id:backdrop;width:parent.width;height:root.viewportHeight;radius:root.radius;color:Theme.surfaceSolid;antialiasing:true}
    Art {anchors.fill:backdrop;source:Media.artUrl;radius:root.radius}
    Rectangle {anchors.fill:backdrop;color:Media.artUrl?Theme.withAlpha(Theme.surfaceSolid,.93):Theme.surfaceSolid;radius:root.radius}
    function revealFocus():void {
        const focused=root.Window.window?.activeFocusItem;
        let ancestor=focused;
        while(ancestor&&ancestor!==viewport.contentItem)ancestor=ancestor.parent;
        if(!ancestor)return;
        const p=focused.mapToItem(viewport.contentItem,0,0);
        if(p.x<viewport.contentX)viewport.contentX=p.x;
        else if(p.x+focused.width>viewport.contentX+viewport.width)viewport.contentX=Math.min(p.x,p.x+focused.width-viewport.width);
        if(p.y<viewport.contentY)viewport.contentY=p.y;
        else if(p.y+focused.height>viewport.contentY+viewport.height)viewport.contentY=Math.min(p.y,p.y+focused.height-viewport.height);
    }
    Connections {target:root.Window.window;function onActiveFocusItemChanged(){Qt.callLater(root.revealFocus);}}
    Flickable {
        id:viewport;objectName:"mediaViewport";anchors.fill:parent;anchors.bottomMargin:root.height-root.viewportHeight;clip:true
        onWidthChanged:Qt.callLater(root.revealFocus)
        onHeightChanged:Qt.callLater(root.revealFocus)
        contentWidth:Math.max(width,280,playback.width+2*(12+Math.max(elapsed.implicitWidth,total.implicitWidth)+8+repeatButton.width+6));contentHeight:Math.max(height,166)
        boundsBehavior:Flickable.StopAtBounds
        ScrollBar.horizontal:ScrollBar {policy:ScrollBar.AsNeeded}
        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
    Item {
        width:viewport.contentWidth;height:viewport.contentHeight
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
        handle:Rectangle {x:seek.visualPosition*(seek.width-width);y:(seek.height-height)/2;width:8;height:8;radius:4;color:Theme.accent;border.width:seek.activeFocus?2:0;border.color:Theme.text;opacity:seek.hovered||seek.pressed||seek.activeFocus?1:0;Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}}
    }
    PanelText {id:elapsed;visible:!!Media.active;x:12;anchors.verticalCenter:playback.verticalCenter;text:root.duration(seek.pressed?seek.value*Media.length:Media.position);font.pixelSize:11;font.features:({tnum:1});color:Theme.subtext}
    PanelText {id:total;visible:!!Media.active;anchors.right:parent.right;anchors.rightMargin:12;anchors.verticalCenter:playback.verticalCenter;text:root.duration(Media.length);font.pixelSize:11;font.features:({tnum:1});color:Theme.subtext}
    Column {anchors.centerIn:parent;spacing:10;visible:!Media.active
        Icon {anchors.horizontalCenter:parent.horizontalCenter;icon:"music_note";size:28;color:Theme.subtext}
        PanelText {text:"No media playing";font.pixelSize:14;color:Theme.subtext}
    }
    Row {id:playback;visible:!!Media.active;x:(parent.width-width)/2;anchors.bottom:parent.bottom;anchors.bottomMargin:7;spacing:6
        IconButton {anchors.verticalCenter:parent.verticalCenter;icon:"skip_previous";label:"Previous track";size:14;enabled:Media.canGoPrevious;onClicked:Media.previous()}
        IconButton {icon:Media.playing?"pause":"play_arrow";label:Media.playing?"Pause":"Play";size:18;background:Theme.accent;color:Theme.accentText;enabled:!!Media.active;onClicked:Media.togglePlaying()}
        IconButton {anchors.verticalCenter:parent.verticalCenter;icon:"skip_next";label:"Next track";size:14;enabled:Media.canGoNext;onClicked:Media.next()}
    }
    RepeatButton {id:repeatButton;visible:!!Media.active;anchors.left:playback.right;anchors.leftMargin:6;anchors.verticalCenter:playback.verticalCenter;size:14}
    }
    }
}
