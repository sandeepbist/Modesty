import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.components
import qs.services
import qs.theme
FocusScope {
    id: root
    function reveal(key){return columnChoices.itemAt(0);}
    objectName:"custom-layout"
    property string selected: ""
    property string gesture: ""
    property var gestureStartItems: []
    property var previewItems: null
    property var original: null
    property point startPoint
    property real dragX: 0
    property real dragY: 0
    property bool dragging: false
    property bool removing: false
    property int heldRows: 6
    property var scrollParent: null
    property point pointerInScroll
    Component.onCompleted: {
        for(let item=parent;item;item=item.parent)if(item.contentY!==undefined&&item.contentHeight!==undefined){scrollParent=item;break;}
    }
    function trackPointer(point) {if(scrollParent)pointerInScroll=grid.mapToItem(scrollParent,point.x,point.y);}
    Timer {
        interval:16;repeat:true;running:root.dragging&&!!root.scrollParent
        onTriggered:{
            const view=root.scrollParent,edge=42;
            const amount=root.pointerInScroll.y<edge?-7:root.pointerInScroll.y>view.height-edge?7:0;
            if(!amount)return;
            const before=view.contentY;
            view.contentY=Math.max(0,Math.min(Math.max(0,view.contentHeight-view.height),before+amount));
            if(view.contentY!==before)root.update(grid.mapFromItem(view,root.pointerInScroll.x,root.pointerInScroll.y));
        }
    }
    readonly property var viewItems: previewItems || ControlLayout.items
    readonly property var selectedItem: viewItems.find(a=>a.id===selected)
    readonly property int viewRows: Math.max(6,...viewItems.map(a=>a.y+a.h+1))
    implicitHeight: body.implicitHeight
    function begin(id,mode,point) {
        selected=id; forceActiveFocus(); gesture=mode;
        gestureStartItems=ControlLayout.items; original=gestureStartItems.find(a=>a.id===id);
        startPoint=point;trackPointer(point); dragX=original.x*grid.pitch; dragY=original.y*grid.pitch;
        heldRows=Math.max(6,ControlLayout.rows+2); dragging=mode==="resize";
    }
    function update(point) {
        if(!original)return;
        const dx=point.x-startPoint.x,dy=point.y-startPoint.y;
        if(!dragging&&Math.abs(dx)+Math.abs(dy)<5)return;
        dragging=true;
        let x=original.x,y=original.y,w=original.w,h=original.h;
        if(gesture==="move") {
            dragX=Math.max(0,Math.min(grid.width-(w*grid.pitch-Preferences.controlGap),original.x*grid.pitch+dx));
            dragY=Math.max(0,original.y*grid.pitch+dy);
            x=Math.round(dragX/grid.pitch); y=Math.round(dragY/grid.pitch);
            removing=point.y>grid.height+8;
        } else {
            w=Math.round(original.w+dx/grid.pitch); h=Math.round(original.h+dy/grid.pitch);
        }
        const next=ControlLayout.previewMove(gestureStartItems,selected,x,y,w,h);
        if(next&&JSON.stringify(next)!==JSON.stringify(previewItems))previewItems=next;
    }
    function finish(cancel) {
        const next=previewItems, remove=removing, id=selected, changed=dragging;
        gesture=""; dragging=false; removing=false; original=null;
        if(!cancel&&changed) {
            if(remove)ControlLayout.remove(id);
            else if(next&&JSON.stringify(next)!==JSON.stringify(ControlLayout.items))ControlLayout.commit(next,ControlLayout.columns);
        }
        previewItems=null;
    }
    function resize(w,h) {const a=selectedItem;if(a)ControlLayout.move(a.id,a.x,a.y,w,h);}
    Keys.onPressed:event=>{
        const a=selectedItem;if(!a)return;
        if(event.key===Qt.Key_Escape&&gesture){finish(true);event.accepted=true;return;}
        if(event.key===Qt.Key_Delete){ControlLayout.remove(a.id);selected="";}
        else if(event.key===Qt.Key_Left)event.modifiers&Qt.ShiftModifier?resize(a.w-1,a.h):ControlLayout.move(a.id,a.x-1,a.y,a.w,a.h);
        else if(event.key===Qt.Key_Right)event.modifiers&Qt.ShiftModifier?resize(a.w+1,a.h):ControlLayout.move(a.id,a.x+1,a.y,a.w,a.h);
        else if(event.key===Qt.Key_Up)event.modifiers&Qt.ShiftModifier?resize(a.w,a.h-1):ControlLayout.move(a.id,a.x,a.y-1,a.w,a.h);
        else if(event.key===Qt.Key_Down)event.modifiers&Qt.ShiftModifier?resize(a.w,a.h+1):ControlLayout.move(a.id,a.x,a.y+1,a.w,a.h);
        else return;
        event.accepted=true;
    }
    ColumnLayout {
        id: body; width: parent.width; spacing: 14
        RowLayout {Layout.fillWidth:true;spacing:5;enabled:!root.gesture
            Repeater {id:columnChoices;model:[5,6,7,8,9];ActionButton {required property int modelData;text:String(modelData);implicitWidth:28;implicitHeight:28;primary:ControlLayout.columns===modelData;onClicked:ControlLayout.tidy(modelData)}}
            Item {Layout.fillWidth:true}
            ActionButton {text:"Tidy";onClicked:ControlLayout.tidy(ControlLayout.columns)}
            ActionButton {text:"Undo";enabled:ControlLayout.history.length>0;onClicked:ControlLayout.undo()}
            ActionButton {text:"Reset";onClicked:ControlLayout.reset()}
        }
        Item {
            id:grid;Layout.alignment:Qt.AlignHCenter;Layout.preferredWidth:Math.min(body.width,Preferences.controlsWidth-Preferences.innerPadding*2)
            Layout.preferredHeight:(root.gesture?root.heldRows:root.viewRows)*pitch-Preferences.controlGap
            readonly property real pitch:(width+Preferences.controlGap)/ControlLayout.columns
            Repeater {model:ControlLayout.columns*(root.gesture?root.heldRows:root.viewRows)
                Rectangle {required property int index;x:(index%ControlLayout.columns)*grid.pitch;y:Math.floor(index/ControlLayout.columns)*grid.pitch;width:grid.pitch-Preferences.controlGap;height:width;radius:Preferences.controlRadius;color:Theme.withAlpha(Theme.text,.025)}
            }
            Rectangle {
                visible:root.dragging&&root.gesture==="move"&&!root.removing&&!!root.selectedItem
                x:(root.selectedItem?.x??0)*grid.pitch;y:(root.selectedItem?.y??0)*grid.pitch
                width:(root.selectedItem?.w??1)*grid.pitch-Preferences.controlGap;height:(root.selectedItem?.h??1)*grid.pitch-Preferences.controlGap
                radius:Preferences.controlRadius;color:Theme.withAlpha(Theme.accent,.08);border.width:1;border.color:Theme.withAlpha(Theme.accent,.5)
            }
            // Stable identifiers preserve pointer grabs and allow neighbors to animate.
            Repeater {model:Object.keys(ControlLayout.shapes)
                Item {
                    id:tile;required property string modelData
                    readonly property var entry:root.viewItems.find(a=>a.id===modelData)
                    readonly property bool following:root.selected===modelData&&root.dragging&&root.gesture==="move"
                    visible:!!entry
                    x:following?root.dragX:(entry?.x??0)*grid.pitch
                    y:following?root.dragY:(entry?.y??0)*grid.pitch
                    width:(entry?.w??1)*grid.pitch-Preferences.controlGap;height:(entry?.h??1)*grid.pitch-Preferences.controlGap
                    z:root.selected===modelData?5:0
                    Behavior on x {enabled:!tile.following;NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
                    Behavior on y {enabled:!tile.following;NumberAnimation {duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
                    Behavior on width {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                    Behavior on height {NumberAnimation {duration:Tokens.animFast;easing.type:Easing.OutCubic}}
                    Loader {anchors.fill:parent;active:!!tile.entry;sourceComponent:ControlTile {kind:tile.modelData;editing:true;opacity:root.removing&&tile.following?.45:1}}
                    Rectangle {anchors.fill:parent;anchors.margins:-2;radius:Preferences.controlRadius+2;color:"transparent";border.width:root.selected===tile.modelData?1.5:0;border.color:Theme.accent}
                    MouseArea {
                        anchors.fill:parent;preventStealing:true;hoverEnabled:true;cursorShape:tile.following?Qt.ClosedHandCursor:Qt.OpenHandCursor;acceptedButtons:Qt.LeftButton|Qt.RightButton
                        onPressed:mouse=>{root.selected=tile.modelData;root.forceActiveFocus();if(mouse.button===Qt.RightButton)sizes.popup();else root.begin(tile.modelData,"move",mapToItem(grid,mouse.x,mouse.y));}
                        onPositionChanged:mouse=>{if(pressed&&root.gesture==="move"){const p=mapToItem(grid,mouse.x,mouse.y);root.trackPointer(p);root.update(p);}}
                        onReleased:if(root.gesture==="move")root.finish(false)
                        onCanceled:root.finish(true)
                    }
                    Rectangle {
                        width:24;height:24;anchors.right:parent.right;anchors.bottom:parent.bottom;radius:8;color:Theme.accent;visible:root.selected===tile.modelData
                        Icon {anchors.centerIn:parent;icon:"south_east";size:14;color:Theme.bgSolid}
                        MouseArea {anchors.fill:parent;preventStealing:true;cursorShape:Qt.SizeFDiagCursor
                            onPressed:mouse=>root.begin(tile.modelData,"resize",mapToItem(grid,mouse.x,mouse.y))
                            onPositionChanged:mouse=>{if(pressed){const p=mapToItem(grid,mouse.x,mouse.y);root.trackPointer(p);root.update(p);}}
                            onReleased:root.finish(false)
                            onCanceled:root.finish(true)
                        }
                    }
                    Menu {id:sizes
                        MenuItem {text:"Rotate";onTriggered:if(tile.entry)ControlLayout.move(tile.modelData,tile.entry.x,tile.entry.y,tile.entry.h,tile.entry.w)}
                        Repeater {model:ControlLayout.shapes[tile.modelData].filter(s=>s[0]<=ControlLayout.columns);MenuItem {required property var modelData;text:modelData[0]+" × "+modelData[1];onTriggered:if(tile.entry)ControlLayout.move(tile.modelData,tile.entry.x,tile.entry.y,modelData[0],modelData[1])}}
                        MenuSeparator {}MenuItem {text:"Remove";onTriggered:ControlLayout.remove(tile.modelData)}
                    }
                }
            }
        }
        Rectangle {Layout.fillWidth:true;Layout.preferredHeight:40;radius:12;color:root.removing?Theme.withAlpha(Theme.red,.15):"transparent";border.width:1;border.color:root.removing?Theme.red:Theme.withAlpha(Theme.text,.1);PanelText {anchors.centerIn:parent;text:"Remove";font.pixelSize:11;color:root.removing?Theme.red:Theme.subtext}}
        RowLayout {visible:!!root.selectedItem;enabled:!root.gesture;Layout.fillWidth:true
            PanelText {Layout.fillWidth:true;text:root.selected; font.pixelSize:12;font.weight:Font.Medium}
            ActionButton {text:"Rotate";onClicked:root.resize(root.selectedItem.h,root.selectedItem.w)}
            ActionButton {text:"Remove";onClicked:ControlLayout.remove(root.selected)}
        }
        PreferenceSlider {visible:!!root.selectedItem;enabled:!root.gesture;Layout.fillWidth:true;label:"Tile width";display:(root.selectedItem?.w??1)+" columns";from:1;to:ControlLayout.columns;stepSize:1;value:root.selectedItem?.w??1;onMoved:value=>root.resize(value,root.selectedItem.h)}
        PreferenceSlider {visible:!!root.selectedItem;enabled:!root.gesture;Layout.fillWidth:true;label:"Tile height";display:(root.selectedItem?.h??1)+" rows";from:1;to:6;stepSize:1;value:root.selectedItem?.h??1;onMoved:value=>root.resize(root.selectedItem.w,value)}
        PanelText {text:"Add a control";font.pixelSize:12;font.weight:Font.Medium}
        Flow {Layout.fillWidth:true;spacing:6;Repeater {model:Object.keys(ControlLayout.shapes).filter(id=>!ControlLayout.items.some(a=>a.id===id));ActionButton {required property string modelData;text:({nightlight:"Night Light",awake:"Keep Awake"})[modelData]||modelData.charAt(0).toUpperCase()+modelData.slice(1);onClicked:ControlLayout.add(modelData)}}}
        PanelText {Layout.fillWidth:true;visible:!!ControlLayout.error;text:ControlLayout.error;font.pixelSize:11;color:ControlLayout.error?Theme.red:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
        ActionButton {text:"Open live control center";onClicked:IslandState.openMenu("quicksettings")}
    }
}
