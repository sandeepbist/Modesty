import QtQuick
import QtQuick.Controls
import qs.services
import qs.components
import qs.theme
Rectangle {
    id: root
    property string kind
    property bool editing: false
    property bool interactive: true
    readonly property bool usable: interactive && !editing && enabled
    readonly property bool toggleTile:["focus","recorder","appearance","awake","peace","nightlight","wifi","bluetooth"].includes(kind)
    property color foreground:toggleTile&&selected?Theme.accentText:Theme.text
    readonly property bool level: kind === "display" || kind === "sound"
    readonly property bool vertical: height > width * 1.2 || width < 110
    readonly property string title: ({focus:"Focus",recorder:"Recorder",appearance:"Appearance",awake:"Keep Awake",wifi:"Wi-Fi",bluetooth:"Bluetooth",media:Media.title||"Nothing playing",display:"Display",sound:"Sound",notifications:"Notifications",peace:"Peace",nightlight:"Night Light",lock:"Lock",power:"Power"})[kind] || kind
    readonly property string icon: ({focus:"timer",recorder:"videocam",appearance:Theme.light?"light_mode":"dark_mode",awake:"coffee",wifi:"wifi",bluetooth:"bluetooth",display:"light_mode",sound:Audio.muted?"volume_off":"volume_up",peace:"do_not_disturb_on",nightlight:"bedtime",lock:"lock",power:"power_settings_new"})[kind] || "music_note"
    readonly property bool selected: kind === "focus" ? FocusTimer.active : kind === "recorder" ? Recorder.active : kind === "appearance" ? Theme.light : kind === "awake" ? KeepAwake.active : kind === "wifi" ? Wireless.enabled : kind === "bluetooth" ? Radio.enabled : kind === "peace" ? Notifications.dnd : kind === "nightlight" ? Display.nightLight : false
    readonly property string subtitle: kind === "focus" ? (FocusTimer.active?FocusTimer.phase==="finished"?"Complete":FocusTimer.timeText:Preferences.focusMinutes+" min") : kind === "recorder" ? (Recorder.active?Recorder.label:"Ready") : kind === "appearance" ? (Theme.light?"Light":"Dark") : kind === "awake"&&KeepAwake.active&&KeepAwake.until ? KeepAwake.remaining+" min left" : kind === "wifi" ? Wireless.connectedName || (Wireless.enabled?"Not connected":"Off") : kind === "bluetooth" ? Radio.devices.filter(d=>d.connected).map(d=>d.name).join(", ") || (Radio.enabled?"On":"Off") : selected?"On":"Off"
    radius: Math.min(Preferences.controlRadius,width/2,height/2)
    color: toggleTile&&selected ? Theme.accent : Theme.surfaceSolid
    gradient:Gradient {
        GradientStop {position:0;color:Qt.lighter(root.color,root.selected?1.045:1.025)}
        GradientStop {position:1;color:root.color}
    }
    antialiasing:true
    border.width: 1; border.color: activeFocus ? Theme.accent : Theme.withAlpha(foreground, hover.hovered && usable ? .15 : Tokens.borderAlpha)
    Behavior on foreground { ColorAnimation { duration: Tokens.animFast } }
    Behavior on border.color { ColorAnimation { duration: Tokens.animFast } }
    Behavior on color { ColorAnimation { duration: Tokens.animFast } }
    SurfaceLighting {anchors.fill:parent;radius:root.radius;active:root.usable;focused:root.activeFocus;interactive:!root.editing}
    Rectangle {
        anchors.fill: parent; radius: root.radius; antialiasing: true
        color: root.foreground
        opacity: tileTap.pressed && root.usable ? .085 : hover.hovered && root.usable && !root.level ? .035 : 0
        Behavior on opacity { NumberAnimation { duration: Tokens.animFast; easing.type: Easing.OutCubic } }
    }
    function activate(): void { if(!usable)return; if(["focus","recorder","wifi","bluetooth","display","sound","power"].includes(kind))IslandState.openMenu(kind);else if(kind==="notifications")IslandState.openMenu("notifhistory");else if(kind==="appearance")Theme.toggleMode();else if(kind==="awake")KeepAwake.toggle();else if(kind==="peace")Notifications.dnd=!Notifications.dnd;else if(kind==="nightlight")Display.setNightLight(!Display.nightLight);else if(kind==="lock")Session.lock(false); }
    HoverHandler { id:hover;onHoveredChanged:{if(hovered&&root.usable)Hints.show(root,root.title+(root.width<=90?" · "+root.subtitle:""));else Hints.hide(root);} cursorShape: root.usable?Qt.PointingHandCursor:Qt.ArrowCursor }
    Keys.onReturnPressed: activate()
    Keys.onEnterPressed: activate()
    Keys.onSpacePressed: activate()
    activeFocusOnTab: usable
    Accessible.role:root.toggleTile?Accessible.CheckBox:Accessible.Button
    Accessible.name:root.title
    Accessible.description:root.subtitle
    Accessible.checked:root.selected
    Item {
        anchors.fill: parent; visible: !root.level && root.kind!=="media" && root.kind!=="notifications"
        Icon {x:root.width>90?14:(parent.width-width)/2;anchors.verticalCenter:parent.verticalCenter;icon:root.icon;size:Preferences.controlIconSize;color:root.foreground}
        Column { x:Math.max(48,Preferences.controlIconSize+24); anchors.verticalCenter: parent.verticalCenter; width:Math.max(0,parent.width-x-14); spacing:3; visible:root.width>90
            PanelText { width:parent.width;visible:!["wifi","bluetooth"].includes(root.kind); text:root.title;color:root.foreground; font.pixelSize:12; font.weight:Font.DemiBold }
            PanelText { width:parent.width; text:root.subtitle; font.pixelSize:["wifi","bluetooth"].includes(root.kind)?12:11; color:root.selected?Theme.withAlpha(Theme.bgSolid,.72):Theme.subtext; Behavior on color {ColorAnimation {duration:Tokens.animFast}} }
        }
        TapHandler { id:tileTap; enabled:root.usable; onTapped:{Hints.hide(root);root.activate();} }
    }
    Loader {
        anchors.fill:parent; active:root.level
        sourceComponent: Item {
            anchors.fill:parent

            Icon {
                x:root.vertical?(parent.width-width)/2:14
                y:root.vertical?parent.height-height-17:(parent.height-height)/2
                icon:root.icon;size:root.vertical?Math.min(24,root.width-24):22
                color:root.vertical&&levelSlider.position>.25?Theme.bgSolid:Theme.text;z:2
            }
            PanelText {
                id:levelValue
                anchors.right:parent.right;anchors.rightMargin:root.vertical?0:40
                y:root.vertical?16:(parent.height-height)/2
                width:root.vertical?parent.width:38;height:14
                visible:root.vertical?root.height>95:root.width>=170
                horizontalAlignment:root.vertical?Text.AlignHCenter:Text.AlignRight
                text:Math.round(levelSlider.position*100)+"%";font.pixelSize:11;font.features:({tnum:1})
                color:root.vertical&&levelSlider.position>.85?Theme.bgSolid:Theme.subtext;z:2
            }
            Slider {
                id:levelSlider;padding:0;hoverEnabled:true
                x:root.vertical?8:48
                y:root.vertical?8:(parent.height-height)/2
                width:root.vertical?parent.width-16:Math.max(16,parent.width-(levelValue.visible?132:88))
                height:root.vertical?parent.height-16:Preferences.sliderThickness+16
                orientation:root.vertical?Qt.Vertical:Qt.Horizontal;from:0;to:1
                stepSize:.01;snapMode:Slider.SnapAlways;wheelEnabled:true
                Binding {target:levelSlider;property:"value";value:root.kind==="sound"?Math.min(1,Audio.volume):SystemInfo.brightness;when:!levelSlider.pressed;restoreMode:Binding.RestoreNone}
                enabled:root.usable&&(root.kind==="sound"?!!Audio.sink:SystemInfo.brightnessAvailable)
                onMoved:root.kind==="sound"?Audio.setVolume(value):SystemInfo.setBrightness(value)
                Accessible.name:root.title
                background:Rectangle {
                    width:levelSlider.width;height:root.vertical?levelSlider.height:Preferences.sliderThickness
                    y:root.vertical?0:8;radius:root.vertical?Math.min(14,width/2):height/2
                    color:Theme.withAlpha(Theme.text,.09)
                    // A clipped fill reaches a real zero, with rounded outer corners.
                    clip:true
                    border.width:1;border.color:Theme.withAlpha(Theme.text,levelSlider.pressed ? .16 : levelSlider.hovered ? .1 : 0)
                    Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}
                    Rectangle {
                        x:0;y:root.vertical?parent.height-height:0
                        width:root.vertical?parent.width:parent.width*levelSlider.position
                        height:root.vertical?parent.height*levelSlider.position:parent.height
                        radius:Math.min(parent.radius,width/2,height/2);color:Theme.accent
                        Behavior on width {enabled:!levelSlider.pressed;NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                        Behavior on height {enabled:!levelSlider.pressed;NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                    }
                }
                handle:Item {}
            }
            IconButton {
                anchors.right:parent.right;anchors.rightMargin:4;anchors.verticalCenter:parent.verticalCenter
                size:14;icon:"chevron_right";label:root.title+" options";visible:!root.vertical
                enabled:root.usable;onClicked:root.activate()
            }
            TapHandler {enabled:root.vertical&&root.usable;acceptedButtons:Qt.RightButton;onTapped:root.activate()}
        }
    }
    Loader {
        anchors.fill:parent; active:root.kind==="media"
        sourceComponent: Art {
            anchors.fill:parent;source:Media.artUrl;radius:root.radius
            Rectangle { anchors.fill:parent;radius:root.radius;color:Media.artUrl?"#aa141b17":Theme.surfaceSolid }
            PanelText { x:12;y:11;visible:root.width>=100&&root.height>=90;width:parent.width-(root.width < 132 ? 42 : 24);text:Media.title||"Nothing playing";font.pixelSize:12;font.weight:Font.DemiBold;color:Media.artUrl?"#f5ffffff":Theme.text }
            PanelText { x:12;y:29;visible:root.width>=100&&root.height>=90;width:parent.width-24;text:Media.artist;font.pixelSize:11;color:Media.artUrl?"#bdffffff":Theme.subtext }
            RepeatButton {anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 3; size: 11; visible: root.width < 132 && root.height>=90; enabled: root.usable && Media.canRepeat}
            Row { anchors.horizontalCenter:parent.horizontalCenter;anchors.bottom:parent.bottom;anchors.bottomMargin:12;spacing:root.width>160?6:1
                IconButton { icon:"skip_previous";label:"Previous";size:12;visible:root.width>=100;enabled:root.usable&&Media.canGoPrevious;onClicked:Media.previous() }
                IconButton { icon:Media.playing?"pause":"play_arrow";label:"Play / pause";size:17;background:Theme.accent;color:Theme.accentText;enabled:root.usable&&!!Media.active;onClicked:Media.togglePlaying() }
                IconButton { icon:"skip_next";label:"Next";size:12;visible:root.width>=100;enabled:root.usable&&Media.canGoNext;onClicked:Media.next() }
                RepeatButton {visible: root.width >= 132; size: 12; enabled: root.usable && Media.canRepeat}
            }
            Rectangle { x:10;y:parent.height-6;width:parent.width-20;height:2;radius:1;color:Theme.withAlpha(Theme.text,0.15);Rectangle { width:parent.width*Media.progress;height:2;color:Theme.accent;radius:1 } }
        }
    }
    Loader {
        anchors.fill:parent;active:root.kind==="notifications";visible:active
        sourceComponent:NotificationFeed {interactive:root.usable;showTitle:false}
    }
}
