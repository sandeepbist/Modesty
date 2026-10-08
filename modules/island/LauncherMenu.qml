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
            Layout.fillWidth:true;Layout.preferredHeight:46;color:"transparent"
            Rectangle {x:8;y:parent.height+5;width:parent.width-16;height:1;color:Theme.withAlpha(Theme.text,.07)}
            Icon {x:12;anchors.verticalCenter:parent.verticalCenter;icon:"search";size:19;color:Theme.subtext}
            TextInput {
                id:input;objectName:"appSearch";x:43;anchors.verticalCenter:parent.verticalCenter;width:parent.width-58;height:24;verticalAlignment:TextInput.AlignVCenter
                focus:true;color:Theme.text;selectionColor:Theme.accent;selectedTextColor:Theme.bgSolid
                font.family:Tokens.font;font.pixelSize:15;font.hintingPreference:Font.PreferVerticalHinting;renderType:Tokens.textRenderType
                selectByMouse:true;clip:true;onTextChanged:root.query=text
                Keys.onDownPressed:root.step(1)
                Keys.onUpPressed:root.step(-1)
                Keys.onTabPressed:event=>root.step(event.modifiers&Qt.ShiftModifier?-1:1)
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
                    width:list.width-6;height:50;radius:12;color:Theme.withAlpha(Theme.text,.07)
                    Rectangle {x:1;anchors.verticalCenter:parent.verticalCenter;width:3;height:24;radius:1.5;color:Theme.accent}
                    y:list.currentItem?.y??0
                    visible:list.count>0
                    Behavior on y {enabled:!root.resettingResults&&!Tokens.reducedMotion;SpringMotion {}}
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
                        color:appRow.pressed?Theme.withAlpha(Theme.text,.1):!appRow.selected&&appRow.hovered?Theme.withAlpha(Theme.text,.035):"transparent"
                        Behavior on color {ColorAnimation {duration:Tokens.animFast}}
                    }
                    contentItem: Item {
                        Rectangle {
                            id:iconSlot;x:12;width:34;height:34;radius:10;anchors.verticalCenter:parent.verticalCenter;color:Theme.withAlpha(Theme.text,.045)
                            Image {id:appIcon;anchors.centerIn:parent;width:24;height:24;source:Quickshell.iconPath(appRow.app.icon,true);asynchronous:true;sourceSize:Qt.size(48,48);fillMode:Image.PreserveAspectFit;visible:status===Image.Ready}
                            Icon {anchors.centerIn:parent;icon:"apps";size:24;color:Theme.subtext;visible:appIcon.status!==Image.Ready}
                        }
                        Column {
                            anchors.left:iconSlot.right;anchors.leftMargin:12
                            anchors.right:parent.right;anchors.rightMargin:14
                            anchors.verticalCenter:parent.verticalCenter;spacing:2
                            PanelText {width:parent.width;text:appRow.text;font.pixelSize:15;font.weight:Font.Medium}
                            PanelText {width:parent.width;visible:Preferences.launcherDescriptions&&!!text;text:appRow.description;font.pixelSize:12;color:Theme.subtext}
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
