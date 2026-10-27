import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import QtQuick.Controls
import Quickshell.Widgets
import qs.components
import qs.services
import qs.theme
Item {
    id:root
    readonly property string detail: ["wifi","bluetooth","display","sound","notifhistory","recorder","focus","performance"].includes(IslandState.state)?IslandState.state:""
    readonly property real apertureHeight:root.parent?.bodyApertureHeight??root.parent?.parent?.height??height+Preferences.innerPadding*2
    readonly property real apertureWidth:root.parent?.bodyApertureWidth??root.parent?.parent?.width??width+Preferences.innerPadding*2
    readonly property real bodyHeight:Math.max(0,Math.min(height,(root.parent?.maximumBodyHeight??Infinity)-Preferences.innerPadding*2))
    readonly property var detailFrame:IslandState.detailFrame
    readonly property real finalSheetWidth:Math.max(0,width-2*detailFrame.inset)
    readonly property real finalSheetHeight:Math.max(0,bodyHeight-detailFrame.top-detailFrame.inset)
    readonly property real gridWidth:Math.max(width,ControlLayout.columns*(40+Preferences.controlGap)-Preferences.controlGap)
    readonly property real gridHeight:ControlLayout.rows*(gridWidth+Preferences.controlGap)/ControlLayout.columns-Preferences.controlGap
    readonly property var missingActivities:[{kind:"focus",active:Activities.focus},{kind:"recorder",active:Activities.recording}].filter(a=>a.active&&!ControlLayout.items.some(t=>t.id===a.kind))
    readonly property real ongoingHeight:missingActivities.length?44:0
    readonly property real overviewHeight:gridHeight+(ControlLayout.footerShown?48:0)
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
    function revealFocus():void {
        const focused=root.Window.window?.activeFocusItem;
        if(!focused)return;
        let ancestor=focused;
        while(ancestor&&ancestor!==root)ancestor=ancestor.parent;
        if(ancestor!==root)return;
        for(ancestor=focused.parent;ancestor&&ancestor!==root;ancestor=ancestor.parent) {
            if(!(ancestor instanceof Flickable))continue;
            const p=focused.mapToItem(ancestor.contentItem,0,0);
            const x=p.x<ancestor.contentX?p.x:p.x+focused.width>ancestor.contentX+ancestor.width?Math.min(p.x,p.x+focused.width-ancestor.width):ancestor.contentX;
            const y=p.y<ancestor.contentY?p.y:p.y+focused.height>ancestor.contentY+ancestor.height?Math.min(p.y,p.y+focused.height-ancestor.height):ancestor.contentY;
            ancestor.contentX=Math.max(ancestor.originX,Math.min(ancestor.originX+Math.max(0,ancestor.contentWidth-ancestor.width),x));
            ancestor.contentY=Math.max(ancestor.originY,Math.min(ancestor.originY+Math.max(0,ancestor.contentHeight-ancestor.height),y));
        }
    }
    function scrollKey(event):void {
        if(![Qt.Key_Home,Qt.Key_End,Qt.Key_PageUp,Qt.Key_PageDown].includes(event.key))return;
        let viewport=overview;
        if(detail) {
            const selected=detailPanes.itemAt(["wifi","bluetooth","display","sound","notifhistory","recorder","focus","performance"].indexOf(detail));
            function find(item) {if(item instanceof Flickable&&item.contentHeight>item.height)return item;for(const child of item?.children||[]){const result=find(child);if(result)return result;}return null;}
            viewport=find(selected?.item)||detailViewport;
        }
        if(!viewport)return;
        const minimum=viewport.originY,maximum=minimum+Math.max(0,viewport.contentHeight-viewport.height);
        viewport.contentY=event.key===Qt.Key_Home?minimum:event.key===Qt.Key_End?maximum:Math.max(minimum,Math.min(maximum,viewport.contentY+(event.key===Qt.Key_PageUp?-1:1)*viewport.height*.8));
        event.accepted=true;
    }
    Connections {target:root.Window.window;function onActiveFocusItemChanged(){Qt.callLater(root.revealFocus);}}
    Keys.onPressed:event=>scrollKey(event)
    RowLayout {
        width:root.width;height:38;spacing:6
        visible:root.missingActivities.length>0;enabled:!root.modal;opacity:tiles.opacity
        Repeater {
            model:root.missingActivities
            ActionButton {
                required property var modelData
                objectName:"ongoing-"+modelData.kind
                Layout.fillWidth:true;Layout.preferredWidth:1;Layout.minimumWidth:0
                implicitHeight:38;focusPolicy:Qt.StrongFocus
                text:modelData.kind==="focus"?"Focus timer · "+FocusTimer.timeText:"Recording · "+Recorder.label
                Accessible.name:text+". Open details"
                Keys.onReturnPressed:clicked()
                Keys.onEnterPressed:clicked()
                onClicked:IslandState.openMenu(modelData.kind)
            }
        }
    }
    Flickable {
        id:overview;objectName:"controlOverview"
        y:root.ongoingHeight
        width:parent.width;height:Math.max(0,Math.min(root.bodyHeight-root.ongoingHeight,root.detail?root.detailFrame.top-root.ongoingHeight:root.overviewHeight));clip:true
        contentWidth:root.gridWidth;contentHeight:root.overviewHeight
        boundsBehavior:Flickable.StopAtBounds
        activeFocusOnTab:!root.modal
        interactive:!root.modal
        ScrollBar.horizontal:ScrollBar {policy:ScrollBar.AsNeeded}
        ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
        Behavior on height {enabled:!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:Tokens.morphDuration;reversingMode:SmoothedAnimation.Immediate}}
        Item {
            id:tiles;width:root.gridWidth;height:root.gridHeight
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
    Item {
        id:footer;objectName:"controlFooter";z:11
        opacity:!root.modal&&ControlLayout.footerShown?1:0
        visible:opacity>0;enabled:!root.modal&&opacity>.7
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
        readonly property bool showTray:Preferences.footerVisible&&Preferences.footerTray&&Tray.items.length>0
        readonly property bool showActions:Preferences.footerVisible&&(Preferences.footerSettings||Preferences.footerPerformance)
        readonly property real dividerWidth:showTray&&showActions?13:0
        width:root.gridWidth;height:38
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
    }
    Item {
        z:1;y:overview.y;width:overview.width;height:overview.height;visible:!root.modal
        WheelHandler {
            orientation:Qt.Horizontal;target:null
            acceptedDevices:PointerDevice.Mouse|PointerDevice.TouchPad
            onWheel:event=>{overview.contentX=Math.max(0,Math.min(Math.max(0,overview.contentWidth-overview.width),overview.contentX-(event.pixelDelta.x||event.angleDelta.x/2)));event.accepted=true;}
        }
    }
    MouseArea {
        width:parent.width
        // The footer shares the overview's stacking context, so exclude its visible area.
        height: {
            const top=overview.y+footer.y-overview.contentY;
            return footer.visible&&top<Math.min(root.height,overview.y+overview.height)&&top+footer.height>Math.max(0,overview.y)
                ?Math.max(0,overview.y,top):root.height;
        }
        z:9;visible:Tray.open&&Tray.inFooter;onClicked:Tray.close();hoverEnabled:true;onWheel:event=>event.accepted=true
    }
    TrayMenu {inFooter:true;z:10;maximumHeight:Math.max(100,footer.y-overview.contentY-8);width:Math.min(280,parent.width-12);anchors.horizontalCenter:parent.horizontalCenter;y:Math.max(0,footer.y-overview.contentY-height-8)}
    // A modal barrier covers the whole card, including its exposed top row.
    MouseArea {anchors.fill:parent;z:2;enabled:root.modal;visible:enabled;acceptedButtons:Qt.AllButtons;hoverEnabled:true;onWheel:event=>event.accepted=true}
    // All detail routes inhabit one surface. Its bounds follow the outer pill;
    // only the settled inner content is replaced, so cards never stack or snap.
    RectangularShadow {z:2;x:sheet.x;y:sheet.y;width:sheet.width;height:sheet.height;radius:sheet.radius;blur:22;offset.y:5;color:"#65000000";opacity:sheet.opacity;visible:Preferences.shadows&&sheet.visible}
    ClippingRectangle {
        id:sheet;objectName:"controlDetailSheet";z:3;x:root.detailFrame.inset;y:root.detailFrame.top
        width:Math.max(0,Math.min(root.width,root.apertureWidth-Preferences.innerPadding*2)-2*root.detailFrame.inset)
        height:Math.max(0,root.apertureHeight-Preferences.innerPadding*2-root.detailFrame.top-root.detailFrame.inset)
        radius:Math.max(0,Math.min(Preferences.expandedRadius-Preferences.innerPadding-root.detailFrame.inset,width/2,height/2))
        color:Theme.surfaceSolid;border.width:1;border.color:Theme.withAlpha(Theme.text,.07);contentInsideBorder:false;antialiasing:true
        opacity:root.detail?1:0;visible:opacity>0
        Behavior on opacity {NumberAnimation {duration:root.detail?Tokens.animFast:Tokens.reducedMotion?0:Math.round(70/Preferences.motionSpeed);easing.type:Easing.OutCubic}}
        SurfaceLighting {anchors.fill:parent;radius:sheet.radius;active:!!root.detail;interactive:true}
        MouseArea {anchors.fill:parent;acceptedButtons:Qt.AllButtons;onWheel:event=>event.accepted=true}
        Flickable {
            id:detailViewport;objectName:"controlDetailViewport"
            x:root.detailFrame.padding;y:root.detailFrame.padding
            width:Math.max(0,root.finalSheetWidth-2*root.detailFrame.padding);height:Math.max(0,root.finalSheetHeight-2*root.detailFrame.padding)
            contentWidth:Math.max(width,280);contentHeight:Math.max(height,detailPanes.itemAt(detailPanes.model.indexOf(root.detail))?.height??0)
            boundsBehavior:Flickable.StopAtBounds;clip:true
            ScrollBar.horizontal:ScrollBar {policy:ScrollBar.AsNeeded}
            ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
        Repeater {
            id:detailPanes
            model:["wifi","bluetooth","display","sound","notifhistory","recorder","focus","performance"]
            delegate:Loader {
                id:loader;required property string modelData
                readonly property bool selected:root.detail===modelData
                property bool revealed:false
                property real heldHeight:IslandState.sizes[modelData][1]-Preferences.innerPadding*2-IslandState.detailChromeHeight
                function measure():void {if(item&&modelData!=="notifhistory")IslandState.measurePanel(modelData,item.implicitHeight);}
                function settle():void {if(selected)heldHeight=IslandState.sizes[modelData][1]-Preferences.innerPadding*2-IslandState.detailChromeHeight;}
                onSelectedChanged:{if(!selected)revealed=false;Qt.callLater(settle);}
                Connections {target:IslandState;function onSizesChanged(){Qt.callLater(loader.settle);}}
                readonly property bool revealReady:selected&&status===Loader.Ready&&!root.outgoingDetailVisible&&sheet.height>=Math.min(height,detailViewport.height)*.94+2*root.detailFrame.padding&&sheet.width+.5>=detailViewport.width+2*root.detailFrame.padding
                onRevealReadyChanged:if(revealReady)revealed=true
                width:detailViewport.contentWidth;height:Math.max(0,Math.min(heldHeight,detailViewport.height),["focus","recorder"].includes(modelData)?item?.implicitHeight??0:0)
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
}
