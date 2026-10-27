import QtQuick
import QtQuick.Controls
import Quickshell
import qs.services
import qs.theme
import qs.components
Rectangle {
    id:root
    property real maximumWidth:10000
    width:Math.min(maximumWidth,icons.width+14);height:inFooter?38:Preferences.barHeight;radius:height/2;color:inFooter?"transparent":Theme.bgSolid;antialiasing:true
    border.width:inFooter?0:1;border.color:Theme.withAlpha(Theme.text,.055)
    property bool inFooter:false
    visible:Tray.items.length>0
    Flickable {
        id:viewport
        anchors.fill:parent;clip:true;contentWidth:icons.width+14;contentHeight:height
        boundsBehavior:Flickable.StopAtBounds;flickableDirection:Flickable.HorizontalFlick
        ScrollBar.horizontal:ScrollBar {policy:ScrollBar.AsNeeded}
    Row {id:icons;x:7;anchors.verticalCenter:parent.verticalCenter;spacing:Preferences.traySpacing
        Repeater {model:Tray.items
            AbstractButton {
                id:item;required property var modelData
                padding:0;focusPolicy:Qt.StrongFocus
                onActiveFocusChanged:if(activeFocus){
                    const left=icons.x+x,right=left+width;
                    if(left<viewport.contentX)viewport.contentX=left;
                    else if(right>viewport.contentX+viewport.width)viewport.contentX=right-viewport.width;
                }
                Accessible.name:modelData.tooltipTitle||modelData.title||modelData.id
                function activate(button):void {
                    if(Preferences.preview)return;
                    hoverDelay.stop();Hints.hide(item);
                    if(button===Qt.RightButton||modelData.onlyMenu)Tray.show(modelData,root.inFooter);
                    else if(button===Qt.MiddleButton)modelData.secondaryActivate();
                    else{Tray.close();IslandState.closeMenu();modelData.activate();}
                }
                onClicked:activate(Qt.LeftButton)
                Keys.onReturnPressed:clicked()
                Keys.onEnterPressed:clicked()
                Keys.onPressed:event=>{
                    if(event.key===Qt.Key_Menu||event.key===Qt.Key_F10&&(event.modifiers&Qt.ShiftModifier)){
                        activate(Qt.RightButton);event.accepted=true;
                    }
                }
                width:Math.max(26,Preferences.trayIconSize+8);height:Math.min(Preferences.barHeight-4,width)
                readonly property bool selected:Tray.selected===modelData
                Component.onDestruction:Tray.exit(item)
                background:Rectangle {radius:Math.min(10,height/2);color:"transparent";border.width:item.activeFocus?1:0;border.color:Theme.accent}
                Rectangle {
                    anchors.fill:parent;radius:Math.min(10,height/2);antialiasing:true
                    color:Theme.text;opacity:item.selected?.1:mouse.pressed?.12:mouse.containsMouse?.055:0
                    Behavior on opacity {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                }
                Item {
                    anchors.centerIn:parent;width:Preferences.trayIconSize;height:width
                    transform:Translate {y:mouse.containsMouse?-1:0;Behavior on y {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}}
                    scale:mouse.pressed?.94:1
                    Behavior on scale {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                    Image {
                        id:icon;anchors.fill:parent
                        source:{const uri=item.modelData.icon||"";if(uri.startsWith("image://icon/")&&!Quickshell.hasThemeIcon(decodeURIComponent(uri.slice(13).split("?")[0])))return Quickshell.iconPath(item.modelData.id,true);return uri;}
                        sourceSize:Qt.size(Preferences.trayIconSize*2,Preferences.trayIconSize*2)
                        asynchronous:true;fillMode:Image.PreserveAspectFit;smooth:true;mipmap:true
                    }
                    Icon {anchors.centerIn:parent;icon:"apps";size:Preferences.trayIconSize-2;color:Theme.subtext;visible:icon.status!==Image.Ready}
                }
                Rectangle {anchors.horizontalCenter:parent.horizontalCenter;anchors.bottom:parent.bottom;width:8;height:2;radius:1;color:Theme.accent;opacity:item.selected?1:0;Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}}
                Timer {id:hoverDelay;interval:300;onTriggered:if(mouse.containsMouse)Tray.show(item.modelData,root.inFooter)}
                MouseArea {
                    id:mouse;anchors.fill:parent;hoverEnabled:true;acceptedButtons:Qt.LeftButton|Qt.RightButton|Qt.MiddleButton;cursorShape:Qt.PointingHandCursor
                    onEntered:{Tray.enter(item);hoverDelay.restart();Hints.show(item,item.modelData.tooltipTitle||item.modelData.title||item.modelData.id);}
                    onExited:{hoverDelay.stop();Tray.exit(item);Hints.hide(item);}
                    onClicked:event=>item.activate(event.button)
                    onWheel:event=>{if(!Preferences.preview)item.modelData.scroll(event.angleDelta.y||event.angleDelta.x,event.angleDelta.y===0);}
                }
            }
        }
    }
    }
}
