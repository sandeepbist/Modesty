import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import Quickshell.Widgets
import qs.components
import qs.services
import qs.theme
Item {
    id:root
    readonly property string detail: ["wifi","bluetooth","display","sound","notifhistory","recorder","focus","performance"].includes(IslandState.state)?IslandState.state:""
    readonly property real apertureHeight:root.parent?.parent?.height??height+Preferences.innerPadding*2
    readonly property real apertureWidth:root.parent?.parent?.width??width+Preferences.innerPadding*2
    readonly property real overviewHeight:ControlLayout.panelHeight-Preferences.innerPadding*2
    readonly property bool modal:!!detail||sheet.opacity>.01
    readonly property bool outgoingDetailVisible: {
        if(!detail)return false;
        for(let i=0;i<detailPanes.count;i++) {
            const pane=detailPanes.itemAt(i);
            if(pane&&!pane.selected&&pane.opacity>.01)return true;
        }
        return false;
    }
    function diagnostics(): var {
        const panes=[];
        for(let i=0;i<detailPanes.count;i++){const pane=detailPanes.itemAt(i);panes.push({name:pane.modelData,selected:pane.selected,opacity:pane.opacity,enabled:pane.enabled,status:pane.status});}
        return {detail,backgroundEnabled:tiles.enabled,modal,sheetHeight:sheet.height,panes};
    }
    Item {
        width:parent.width;height:root.detail?40:root.overviewHeight;clip:true
        Behavior on height {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.morphDuration;reversingMode:SmoothedAnimation.Immediate}}
        Item {
            id:tiles; width:parent.width;height:root.overviewHeight
            opacity:root.detail?0.25:1;enabled:!root.modal
            Behavior on opacity { NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutCubic} }
            Repeater { model:Object.keys(ControlLayout.shapes)
                Item {
                    id:tile
                    required property string modelData
                    readonly property var entry:ControlLayout.items.find(a=>a.id===modelData)
                    readonly property real pitch:(tiles.width+Preferences.controlGap)/ControlLayout.columns
                    visible:!!entry
                    x:(entry?.x??0)*pitch;y:(entry?.y??0)*pitch
                    width:(entry?.w??1)*pitch-Preferences.controlGap;height:(entry?.h??1)*pitch-Preferences.controlGap
                    Behavior on x {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}}
                    Behavior on y {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}}
                    Behavior on width {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}}
                    Behavior on height {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.animMedium;reversingMode:SmoothedAnimation.Immediate}}
                    Loader {
                        anchors.fill:parent;active:!!tile.entry
                        sourceComponent:ControlTile {kind:tile.modelData;interactive:!root.detail&&root.enabled}
                    }
                }
            }
        }
    }
    Item {
        id:footer;objectName:"controlFooter";z:11
        opacity:!root.modal&&ControlLayout.footerShown&&root.apertureHeight>=root.overviewHeight+Preferences.innerPadding*2-2?1:0
        visible:opacity>0;enabled:!root.modal&&opacity>.7
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
        readonly property bool showTray:Preferences.footerVisible&&Preferences.footerTray&&Tray.items.length>0
        readonly property bool showActions:Preferences.footerVisible&&(Preferences.footerSettings||Preferences.footerPerformance)
        readonly property real dividerWidth:showTray&&showActions?13:0
        width:parent.width;height:38
        y:root.overviewHeight-height
        Rectangle {width:parent.width;height:1;y:-5;color:Theme.withAlpha(Theme.text,.06)}
        RowLayout {
            id:footerButtons;spacing:6;anchors.verticalCenter:parent.verticalCenter
            width:footer.width-footer.dividerWidth-(footer.showTray?footerTray.width:0)
            visible:footer.showActions
            Repeater {
                model:[{key:"footerSettings",icon:"settings",label:"Settings",panel:"settings"},{key:"footerPerformance",icon:"monitoring",label:"Performance",panel:"performance"}]
                ActionButton {
                    id:action
                    required property var modelData
                    objectName:modelData.key
                    visible:Preferences.footerVisible&&Preferences[modelData.key]
                    Layout.fillWidth:true;Layout.preferredWidth:1;Layout.minimumWidth:0
                    implicitHeight:38;text:modelData.label
                    focusPolicy:Qt.StrongFocus
                    Accessible.name:text
                    Keys.onReturnPressed:clicked()
                    Keys.onEnterPressed:clicked()
                    contentItem:Item {
                        Row {
                            anchors.centerIn:parent;spacing:6
                            Icon {icon:action.modelData.icon;size:17;color:Theme.subtext}
                            PanelText {objectName:action.modelData.key+"Label";text:action.text;width:Math.min(implicitWidth,Math.max(0,action.availableWidth-23));font.pixelSize:11;color:Theme.subtext;anchors.verticalCenter:parent.verticalCenter}
                        }
                    }
                    background:Rectangle {
                        radius:10
                        color:Theme.withAlpha(Theme.text,action.pressed?.1:action.hovered?.055:0)
                        border.width:action.activeFocus?1:0;border.color:Theme.accent
                    }
                    onClicked:{Tray.close();IslandState.openMenu(modelData.panel);}
                }
            }
        }
        Rectangle {x:footerButtons.width+6;anchors.verticalCenter:parent.verticalCenter;width:1;height:16;visible:footer.dividerWidth>0;color:Theme.withAlpha(Theme.text,.1)}
        TrayIcons {
            id:footerTray;objectName:"footerTray";inFooter:true
            maximumWidth:footer.showActions?Math.max(0,footer.width*.28):footer.width
            visible:footer.showTray
            anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter
        }
    }
    MouseArea {anchors.fill:parent;z:9;visible:Tray.open&&Tray.inFooter;onClicked:Tray.close();hoverEnabled:true;onWheel:event=>event.accepted=true}
    TrayMenu {inFooter:true;z:10;maximumHeight:Math.max(100,footer.y-8);width:Math.min(280,parent.width-12);anchors.horizontalCenter:parent.horizontalCenter;y:Math.max(0,footer.y-height-8)}
    // A modal barrier covers the whole card, including its exposed top row.
    MouseArea {anchors.fill:parent;z:2;enabled:root.modal;visible:enabled;acceptedButtons:Qt.AllButtons;hoverEnabled:true;onWheel:event=>event.accepted=true}
    // All detail routes inhabit one surface. Its bounds follow the outer pill;
    // only the settled inner content is replaced, so cards never stack or snap.
    RectangularShadow {z:2;x:sheet.x;y:sheet.y;width:sheet.width;height:sheet.height;radius:sheet.radius;blur:22;offset.y:5;color:"#65000000";opacity:sheet.opacity;visible:Preferences.shadows&&sheet.visible}
    ClippingRectangle {
        id:sheet;z:3;x:6;y:40
        width:Math.max(0,Math.min(root.width,root.apertureWidth-Preferences.innerPadding*2)-12)
        height:Math.max(0,root.apertureHeight-Preferences.innerPadding*2-48)
        radius:Math.max(0,Math.min(Math.max(16,Preferences.expandedRadius-Preferences.innerPadding),width/2,height/2))
        color:Theme.surfaceSolid;border.width:1;border.color:Theme.withAlpha(Theme.text,.07);contentInsideBorder:false;antialiasing:true
        opacity:root.detail?1:0;visible:opacity>0
        Behavior on opacity {NumberAnimation {duration:root.detail?Tokens.animFast:Tokens.reducedMotion?0:Math.round(70/Preferences.motionSpeed);easing.type:Easing.OutCubic}}
        SurfaceLighting {anchors.fill:parent;radius:sheet.radius;active:!!root.detail;interactive:true}
        MouseArea {anchors.fill:parent;acceptedButtons:Qt.AllButtons;onWheel:event=>event.accepted=true}
        Repeater {
            id:detailPanes
            model:["wifi","bluetooth","display","sound","notifhistory","recorder","focus","performance"]
            delegate:Loader {
                id:loader;required property string modelData
                readonly property bool selected:root.detail===modelData
                property bool revealed:false
                property real heldHeight:IslandState.sizes[modelData][1]-Preferences.innerPadding*2-80
                function measure():void {if(item&&modelData!=="notifhistory")IslandState.measurePanel(modelData,item.implicitHeight);}
                function settle():void {if(selected)heldHeight=IslandState.sizes[modelData][1]-Preferences.innerPadding*2-80;}
                onSelectedChanged:{if(!selected)revealed=false;Qt.callLater(settle);}
                Connections {target:IslandState;function onSizesChanged(){Qt.callLater(loader.settle);}}
                readonly property bool revealReady:selected&&status===Loader.Ready&&!root.outgoingDetailVisible&&sheet.height>=height*.94+32&&sheet.width>=root.width-13
                onRevealReadyChanged:if(revealReady)revealed=true
                x:16;y:16;width:Math.max(0,root.width-44);height:Math.max(0,heldHeight)
                opacity:selected&&(revealed||revealReady)?1:0
                visible:opacity>0;enabled:selected&&opacity>.7
                transform:Translate {y:4*(1-loader.opacity)}
                Behavior on opacity {NumberAnimation {duration:loader.selected?Tokens.animFast:Tokens.reducedMotion?0:Math.round(70/Preferences.motionSpeed);easing.type:Easing.OutCubic}}
                active:selected||opacity>0;asynchronous:true
                source:({performance:"PerformanceMenu.qml",focus:"FocusMenu.qml",recorder:"RecorderMenu.qml",wifi:"WifiMenu.qml",bluetooth:"BluetoothMenu.qml",display:"DisplayMenu.qml",sound:"SoundMenu.qml",notifhistory:"NotifHistory.qml"})[modelData]
                onLoaded:{Qt.callLater(measure);Qt.callLater(settle);}
                Connections {target:loader.item;function onImplicitHeightChanged(){Qt.callLater(loader.measure);}}
            }
        }
    }
}
