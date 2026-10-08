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
    signal action(string name)
    readonly property bool available:!setting.when||setting.values.includes(read(setting.when))
    objectName:"setting-"+setting.key
    readonly property var dependency:Catalog.prerequisite(setting)
    signal prerequisite(var target)
    function reveal() { return available ? (setting.kind==="toggle"?toggleControl:setting.kind==="slider"?sliderLoader.item:setting.kind==="text"?textLoader.item.field:setting.kind==="choice"?options.itemAt(0):root) : prerequisiteButton; }
    readonly property var value:read(setting.key)
    activeFocusOnTab:setting.kind==="action"
    Accessible.name:setting.label
    Accessible.role:setting.kind==="action"?Accessible.Button:Accessible.Grouping
    Keys.onReturnPressed:if(setting.kind==="action")action(setting.key)
    Keys.onSpacePressed:if(setting.kind==="action")action(setting.key)
    TapHandler {enabled:root.setting.kind==="action";onTapped:root.action(root.setting.key)}
    HoverHandler {enabled:root.setting.kind==="action";cursorShape:Qt.PointingHandCursor}
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
    Rectangle {anchors.fill:parent;anchors.margins:-7;radius:10;color:"transparent";border.width:root.highlighted||root.activeFocus?1:0;border.color:Theme.withAlpha(Theme.accent,.65)}
    ColumnLayout {
    id:body;width:root.width;spacing:10
    RowLayout {
        Layout.fillWidth:true;spacing:20
        ColumnLayout {
            Layout.fillWidth:true;spacing:4
            PanelText {Layout.fillWidth:true;text:root.setting.label;font.pixelSize:14;font.weight:Font.Medium;wrapMode:Text.Wrap;elide:Text.ElideNone}
            PanelText {Layout.fillWidth:true;visible:!!root.setting.description;text:root.setting.description||"";font.pixelSize:12;lineHeight:1.25;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
        }
        Toggle {id:toggleControl;objectName:root.setting.kind==="toggle"?"control-"+root.setting.key:"";enabled:root.available;visible:root.setting.kind==="toggle";text:root.setting.label;checked:root.value===true;onToggled:root.write(checked)}
        PanelText {visible:root.setting.kind==="slider";text:(Math.round(Number(root.value)*100)/100)+(root.setting.unit||"");font.pixelSize:12;color:Theme.subtext;font.features:({tnum:1})}
        Icon {visible:root.setting.kind==="action";icon:"chevron_right";size:16;color:Theme.subtext}
    }
    Loader {
        id:sliderLoader;enabled:root.available
        Layout.fillWidth:true;active:root.setting.kind==="slider";visible:active
        sourceComponent:Slider {
            id:slider;objectName:"control-"+root.setting.key
            from:root.setting.min;to:root.setting.max;stepSize:root.setting.step
            implicitHeight:26
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
        id:textLoader;enabled:root.available
        Layout.fillWidth:true;active:root.setting.kind==="text";visible:active
        sourceComponent:RowLayout {
            property alias field:prefixField
            spacing:8
            EntryField {
                id:prefixField;objectName:"control-"+root.setting.key;Layout.preferredWidth:180
                Binding {target:prefixField;property:"text";value:String(root.value||"");when:!prefixField.activeFocus;restoreMode:Binding.RestoreNone}
                onEditingFinished:root.write(text)
                Accessible.name:root.setting.label
            }
            PanelText {text:":";font.pixelSize:16;color:Theme.subtext}
            Item {Layout.fillWidth:true}
        }
    }
    Flow {
        enabled:root.available
        visible:root.setting.kind==="choice";Layout.fillWidth:true;spacing:6
        Repeater {
            id:options;model:root.setting.options||[]
            ActionButton {
                id:option
                required property var modelData
                readonly property bool selected:root.value===modelData.value
                text:modelData.label
                onClicked:root.write(modelData.value)
                Accessible.role:Accessible.RadioButton;Accessible.checked:selected
                background:Rectangle {
                    radius:9;color:option.hovered?Theme.withAlpha(Theme.text,.06):"transparent"
                    border.width:1;border.color:option.selected||option.activeFocus?Theme.accent:Theme.withAlpha(Theme.text,.12)
                    Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}
                }
            }
        }
    }
    RowLayout {
        Layout.fillWidth:true;visible:!root.available;spacing:8
        PanelText {Layout.fillWidth:true;text:root.dependency?.message||"Unavailable";wrapMode:Text.Wrap;elide:Text.ElideNone;font.pixelSize:12;color:Theme.subtext}
        ActionButton {id:prerequisiteButton;objectName:"prerequisite-"+root.setting.key;text:root.dependency?"Go to "+root.dependency.label:"";visible:!!root.dependency;onClicked:root.prerequisite(root.dependency)}
    }
}
}
