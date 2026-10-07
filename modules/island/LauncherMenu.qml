import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.services
import qs.components
import qs.theme
FocusScope {
    id:root
    objectName:"launcherPanel"
    property string query:""
    property int selected:0
    readonly property var results:Apps.search(query)
    property bool resettingResults:false
    onQueryChanged:selected=0
    // Update occupied rows together: search never leaves animated empty slots.
    onResultsChanged: {
        resettingResults=true;
        selected=0;
        list.cancelFlick();
        list.positionViewAtBeginning();
        Qt.callLater(()=>root.resettingResults=false);
    }
    function beginSearch(): void { input.clear(); selected=0; list.positionViewAtBeginning(); input.forceActiveFocus(); }
    function launch(): void { if(calculator.requested){calculator.copy();}else if(results[selected]){Apps.launch(results[selected]);} }
    Connections {target:Apps;function onLaunched(){if(IslandState.menu=== "launcher")IslandState.closeMenu();}}
    function step(delta: int): void { selected=Math.max(0,Math.min(results.length-1,selected+delta)); }
    function diagnostics(): var { return {selected,query,activeFocus:input.activeFocus,count:results.length}; }
    onActiveFocusChanged:if(activeFocus)input.forceActiveFocus()
    // Keyboard input is ready throughout the morph; invisible pointer targets are not.
    MouseArea {anchors.fill:parent;z:20;enabled:root.parent.opacity<.7;acceptedButtons:Qt.AllButtons;onPressed:event=>event.accepted=true}
    ColumnLayout {
        anchors.fill:parent;anchors.margins:6;spacing:12
        Rectangle {
            Layout.fillWidth:true;Layout.preferredHeight:46;radius:12;color:Theme.withAlpha(Theme.text,.025)
            border.width:0
            Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}
            Icon {x:12;anchors.verticalCenter:parent.verticalCenter;icon:"search";size:19;color:Theme.subtext}
            TextInput {
                id:input;objectName:"appSearch";x:43;anchors.verticalCenter:parent.verticalCenter;width:parent.width-58;height:24;verticalAlignment:TextInput.AlignVCenter
                focus:true;color:Theme.text;selectionColor:Theme.accent;selectedTextColor:Theme.bgSolid
                font.family:Tokens.font;font.pixelSize:15;font.hintingPreference:Font.PreferVerticalHinting;renderType:Tokens.textRenderType
                selectByMouse:true;clip:true;onTextChanged:root.query=text
                Keys.onDownPressed:root.step(1)
                Keys.onUpPressed:root.step(-1)
                Keys.onTabPressed:root.step(1)
                Keys.onBacktabPressed:root.step(-1)
                Keys.onPressed: event => {
                    if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) { root.launch(); event.accepted = true; }
                    else if (event.key === Qt.Key_PageDown) { root.step(Preferences.launcherVisibleRows); event.accepted = true; }
                    else if (event.key === Qt.Key_PageUp) { root.step(-Preferences.launcherVisibleRows); event.accepted = true; }
                }
                PanelText {anchors.fill:parent;text:"Search";visible:!input.text;color:Theme.subtext;font.pixelSize:15;verticalAlignment:Text.AlignVCenter}
            }
        }
        CalculatorResult {id:calculator;Layout.fillWidth:true;query:root.query}
        Item {
            visible:!calculator.requested;Layout.fillWidth:true;Layout.fillHeight:true
            ListView {
                id:list;anchors.fill:parent;clip:true
                model:root.results.length;currentIndex:root.selected
                spacing:6
                highlightFollowsCurrentItem:false
                highlight:Rectangle {
                    width:list.width-6;height:50;radius:12;color:"transparent"
                    border.width:1.25;border.color:Theme.withAlpha(Theme.accent,.85)
                    y:list.currentItem?.y??0
                    visible:list.count>0
                    Behavior on y {enabled:!root.resettingResults&&!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:160;reversingMode:SmoothedAnimation.Immediate}}
                }
                highlightRangeMode:ListView.ApplyRange
                preferredHighlightBegin:0;preferredHighlightEnd:height-50
                highlightMoveDuration:Tokens.reducedMotion?0:160
                keyNavigationEnabled:false
                boundsBehavior:Flickable.StopAtBounds
                ScrollBar.vertical:ScrollBar {width:4}
                ViewportFade {view:list;edge:12}
                delegate: AbstractButton {
                    id:appRow;required property int index
                    readonly property var app:root.results[index]??({name:"",icon:""})
                    readonly property bool selected:root.selected===index
                    readonly property string description:app.entry?.comment || app.entry?.genericName || ""
                    width:list.width-6;height:50;padding:0
                    text:app.name;Accessible.name:text;Accessible.description:description
                    focusPolicy:Qt.NoFocus;hoverEnabled:true
                    onClicked:{root.selected=index;root.launch();}
                    background:Rectangle {
                        radius:12;antialiasing:true
                        color:appRow.pressed?Theme.withAlpha(Theme.text,.06):"transparent"
                        border.width:1
                        border.color:!appRow.selected&&appRow.hovered?Theme.withAlpha(Theme.text,.16):"transparent"
                        Behavior on border.color {ColorAnimation {duration:Tokens.animFast}}
                        Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                    }
                    contentItem: Item {
                        Item {
                            id:iconSlot;x:13;width:30;height:30;anchors.verticalCenter:parent.verticalCenter
                            Image {id:appIcon;anchors.fill:parent;source:Quickshell.iconPath(appRow.app.icon,true);asynchronous:true;sourceSize:Qt.size(60,60);visible:status===Image.Ready}
                            Icon {anchors.centerIn:parent;icon:"apps";size:26;color:Theme.subtext;visible:appIcon.status!==Image.Ready}
                        }
                        Column {
                            anchors.left:iconSlot.right;anchors.leftMargin:13
                            anchors.right:parent.right;anchors.rightMargin:14
                            anchors.verticalCenter:parent.verticalCenter;spacing:3
                            PanelText {width:parent.width;text:appRow.text;font.pixelSize:15;font.weight:Font.Medium}
                        }

                    }
                }
            }
            Column {parent:list;anchors.centerIn:parent;spacing:12;visible:!root.results.length
                Icon {anchors.horizontalCenter:parent.horizontalCenter;icon:"search_off";size:28;color:Theme.subtext}
                PanelText {text:"No applications found";font.pixelSize:13;color:Theme.subtext}
            }
        }
        Item {Layout.fillHeight:true;visible:calculator.requested}
        PanelText {Layout.fillWidth:true;visible:!!Apps.error;text:Apps.error;color:Theme.red;font.pixelSize:12;wrapMode:Text.Wrap;elide:Text.ElideNone}

    }
}
