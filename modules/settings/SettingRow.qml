import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.components
import qs.services
import qs.theme
import "SettingsCatalog.js" as Catalog

Item {
    id:root
    implicitHeight:body.implicitHeight
    required property var setting
    property bool highlighted:false
    readonly property bool fullDescription:setting.kind==="choice"||(setting.description||"").length>80
    signal action(string name)
    readonly property bool available:!setting.when||setting.values.includes(read(setting.when))
    objectName:"setting-"+setting.key
    readonly property var dependency:Catalog.prerequisite(setting)
    signal prerequisite(var target)
    function reveal() { return available ? (setting.kind==="toggle"?toggleControl:setting.kind==="slider"?sliderLoader.item:setting.kind==="text"?textLoader.item.field:setting.kind==="choice"?choiceLoader.item:root) : prerequisiteButton; }
    readonly property var value:read(setting.key)
    activeFocusOnTab:setting.kind==="action"
    Accessible.name:setting.label
    Accessible.role:setting.kind==="action"?Accessible.Button:Accessible.Grouping
    Keys.onReturnPressed:if(setting.kind==="action")action(setting.key)
    Keys.onSpacePressed:if(setting.kind==="action")action(setting.key)
    TapHandler {id:actionTap;enabled:root.setting.kind==="action";onTapped:root.action(root.setting.key)}
    HoverHandler {id:actionHover;enabled:root.setting.kind==="action";cursorShape:Qt.PointingHandCursor}
    function read(key) {
        if(key==="themeMode")return Theme.light?"light":"dark";
        if(key==="peace")return Notifications.dnd;
        if(key==="awake")return KeepAwake.active;
        if(key==="nightLight")return Display.nightLight;
        if(key==="temperature")return Display.temperature;
        return Preferences[key];
    }
    function write(value) {
        const key=setting.key;
        if(key==="themeMode"){Theme.setMode(value);return;}
        if(key==="peace"){Notifications.dnd=value;return;}
        if(key==="awake"){KeepAwake.setActive(value);return;}
        if(key==="nightLight"){Display.setNightLight(value);return;}
        if(key==="temperature"){Display.temperature=value;Display.setNightLight(true);return;}
        Preferences.set(key,value);
    }
    Rectangle {anchors.fill:parent;anchors.margins:-7;radius:10;color:root.setting.kind==="action"?Theme.withAlpha(Theme.text,actionTap.pressed?.08:actionHover.hovered?.035:0):"transparent";border.width:root.highlighted||root.activeFocus?1:0;border.color:Theme.withAlpha(Theme.accent,.65)}
    ColumnLayout {
    id:body;width:root.width;spacing:8
    RowLayout {
        Layout.fillWidth:true;Layout.minimumHeight:40;spacing:12
        ColumnLayout {
            Layout.fillWidth:true;spacing:4
            PanelText {Layout.fillWidth:true;text:root.setting.label;font.pixelSize:13;font.weight:Font.Medium;wrapMode:Text.Wrap;elide:Text.ElideNone}
            PanelText {Layout.fillWidth:true;visible:!!root.setting.description&&!root.fullDescription;text:root.setting.description||"";font.pixelSize:12;lineHeight:1.3;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
        }
        Toggle {id:toggleControl;implicitWidth:40;implicitHeight:32;objectName:root.setting.kind==="toggle"?"control-"+root.setting.key:"";enabled:root.available;visible:root.setting.kind==="toggle";text:root.setting.label;checked:root.value===true;onToggled:root.write(checked)}
    Loader {
        id:sliderLoader;enabled:root.available
        Layout.preferredWidth:164;Layout.minimumWidth:140;opacity:enabled?1:.4;active:root.setting.kind==="slider";visible:active
        sourceComponent:Slider {
            id:slider;objectName:"control-"+root.setting.key
            from:root.setting.min;to:root.setting.max;stepSize:root.setting.step
            implicitHeight:36
            Binding {target:slider;property:"value";value:Number(root.value);when:!slider.pressed;restoreMode:Binding.RestoreNone}
            onMoved:root.write(value)
            Accessible.name:root.setting.label
            hoverEnabled:true
            background:Rectangle {
                x:slider.leftPadding;y:(slider.height-height)/2;width:slider.availableWidth;height:4;radius:2;color:Theme.withAlpha(Theme.text,.1)
                Rectangle {width:parent.width*slider.visualPosition;height:4;radius:2;color:Theme.accent}
            }
            handle:Rectangle {
                x:slider.leftPadding+slider.visualPosition*(slider.availableWidth-width);y:(slider.height-height)/2
                width:14;height:14;radius:7;color:Theme.accent;antialiasing:true
                border.width:slider.activeFocus?2:0;border.color:Theme.text
                scale:slider.pressed?1.14:slider.hovered?1.06:1
                Behavior on scale {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
            }
        }
    }
    Loader {
        id:choiceLoader; enabled:root.available
        Layout.preferredWidth:180;Layout.minimumWidth:140;opacity:enabled?1:.4
        active:root.setting.kind==="choice";visible:active
        sourceComponent:ComboBox {
            id:choice;objectName:"control-"+root.setting.key
            model:root.setting.options;textRole:"label";valueRole:"value"
            implicitHeight:36;leftPadding:12;rightPadding:32;hoverEnabled:true
            Binding {target:choice;property:"currentIndex";value:root.setting.options.findIndex(o=>o.value===root.value)}
            onActivated:root.write(currentValue)
            Accessible.name:root.setting.label
            Accessible.description:root.setting.description||""
            contentItem:PanelText {text:choice.displayText;font.pixelSize:12;verticalAlignment:Text.AlignVCenter}
            indicator:Icon {x:choice.width-width-10;y:(choice.height-height)/2;icon:choice.popup.visible?"expand_less":"expand_more";size:15;color:Theme.subtext}
            background:Rectangle {radius:8;color:Theme.withAlpha(Theme.text,choice.pressed ? .1 : choice.hovered ? .07 : .035);border.width:1;border.color:choice.activeFocus?Theme.accent:Theme.withAlpha(Theme.text,.08)}
            delegate:ItemDelegate {
                id:option
                objectName:"option-"+root.setting.key+"-"+index
                width:choiceList.width-18;implicitHeight:Math.max(36,optionLabel.implicitHeight+16);leftPadding:8;rightPadding:8
                required property var modelData
                required property int index
                highlighted:choice.highlightedIndex===index
                hoverEnabled:true
                Accessible.name:modelData.label
                Accessible.role:Accessible.ListItem
                Accessible.selected:choice.currentIndex===index
                contentItem:RowLayout {
                    spacing:8
                    Icon {icon:"check";size:15;color:Theme.accent;opacity:choice.currentIndex===option.index?1:0}
                    PanelText {id:optionLabel;Layout.fillWidth:true;text:option.modelData.label;font.pixelSize:12;wrapMode:Text.Wrap;elide:Text.ElideNone;verticalAlignment:Text.AlignVCenter}
                }
                background:Rectangle {radius:6;color:option.highlighted?Theme.accentLow:option.hovered?Theme.withAlpha(Theme.text,.055):"transparent"}
            }
            popup:Popup {
                objectName:"choice-popup-"+root.setting.key
                y:choice.height+6;width:choice.width;padding:6;margins:8
                implicitHeight:Math.min(264,choiceList.contentHeight+12,choice.Window.window?choice.Window.window.height-32:264)
                background:Rectangle {radius:10;color:Theme.surfaceSolid;border.width:1;border.color:Theme.withAlpha(Theme.text,.14)}
                contentItem:ListView {
                    id:choiceList;objectName:"choice-list-"+root.setting.key;clip:true;model:choice.popup.visible?choice.delegateModel:null
                    currentIndex:choice.highlightedIndex;boundsBehavior:Flickable.StopAtBounds
                    ScrollBar.vertical:SettingsScrollBar {}
                }
            }
        }
    }
        PanelText {Layout.preferredWidth:52;horizontalAlignment:Text.AlignRight;visible:root.setting.kind==="slider";text:(Math.round(Number(root.value)*100)/100)+(root.setting.unit||"");font.pixelSize:12;color:Theme.subtext;font.features:({tnum:1})}
        Icon {visible:root.setting.kind==="action";icon:"chevron_right";size:16;color:Theme.subtext}
    }
    PanelText {Layout.fillWidth:true;visible:!!root.setting.description&&root.fullDescription;text:root.setting.description||"";font.pixelSize:12;lineHeight:1.3;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
    Loader {
        id:textLoader;enabled:root.available
        Layout.fillWidth:true;active:root.setting.kind==="text";visible:active
        sourceComponent:RowLayout {
            property alias field:prefixField
            spacing:8
            EntryField {
                id:prefixField;objectName:"control-"+root.setting.key;Layout.preferredWidth:180;Layout.maximumWidth:parent.width-20
                Binding {target:prefixField;property:"text";value:String(root.value||"");when:!prefixField.activeFocus;restoreMode:Binding.RestoreNone}
                onEditingFinished:root.write(text)
                Accessible.name:root.setting.label
            }
            PanelText {text:":";font.pixelSize:16;color:Theme.subtext}
            Item {Layout.fillWidth:true}
        }
    }
    RowLayout {
        Layout.fillWidth:true;visible:!root.available;spacing:8
        PanelText {Layout.fillWidth:true;text:root.dependency?.message||"Unavailable";wrapMode:Text.Wrap;elide:Text.ElideNone;font.pixelSize:12;color:Theme.subtext}
        ActionButton {id:prerequisiteButton;objectName:"prerequisite-"+root.setting.key;text:root.dependency?"Go to "+root.dependency.label:"";visible:!!root.dependency;onClicked:root.prerequisite(root.dependency)}
    }
}
}
