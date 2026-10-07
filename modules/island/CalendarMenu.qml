import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.components
import qs.services
import qs.theme
import "../../services/Calendar.js" as Dates
FocusScope {
    id:root
    property string selectedDate:Reminders.focusDate||Dates.key(Time.date)
    property int year:Dates.parse(selectedDate).getFullYear()
    property int month:Dates.parse(selectedDate).getMonth()
    property string mode:"days"
    property bool upcoming:false
    property bool editing:false
    readonly property real compactHeight:320-Preferences.innerPadding*2
    function toggleDate(day:string):void {const closing=Reminders.calendarExpanded&&selectedDate===day;select(day);Reminders.calendarExpanded=!closing;}
    onEditingChanged:Reminders.calendarEditing=editing
    property var edited:null
    property var pending:null
    readonly property date viewDate:new Date(year,month,1,12)
    readonly property int yearBase:Math.floor(year/12)*12
    readonly property var entries:upcoming?Reminders.items.filter(r=>!r.done).sort((a,b)=>a.date.localeCompare(b.date)||a.time.localeCompare(b.time)):Reminders.forDate(selectedDate)
    function navigate(y:int,m:int,nextMode:string):void {const d=new Date(Math.max(1900,Math.min(9999,y)),m,1,12);pending={year:Math.max(1900,Math.min(9999,d.getFullYear())),month:d.getFullYear()<1900?0:d.getFullYear()>9999?11:d.getMonth(),mode:nextMode};if(!turn.running)turn.start();}
    function step(direction:int):void {Reminders.calendarExpanded=false;const base=pending||{year,month,mode};if(base.mode==="days")navigate(base.year,base.month+direction,base.mode);else navigate(base.year+(base.mode==="years"?12:1)*direction,base.month,base.mode);}
    function select(day:string):void {selectedDate=day;upcoming=false;const d=Dates.parse(day);if(d.getFullYear()!==year||d.getMonth()!==month)navigate(d.getFullYear(),d.getMonth(),"days");}
    function today():void {Reminders.calendarExpanded=false;select(Dates.key(Time.date));navigate(Time.date.getFullYear(),Time.date.getMonth(),"days");}
    function edit(entry):void {Reminders.calendarExpanded=true;edited=entry;Reminders.error="";editing=true;}
    function syncAgenda():void {
        const next=entries;
        for(let i=agendaModel.count-1;i>=0;i--)if(!next.some(r=>r.id===agendaModel.get(i).entry.id))agendaModel.remove(i);
        next.forEach((r,index)=>{let found=-1;for(let i=0;i<agendaModel.count;i++)if(agendaModel.get(i).entry.id===r.id){found=i;break;}if(found<0)agendaModel.insert(index,{entry:r});else{if(found!==index)agendaModel.move(found,index,1);agendaModel.setProperty(index,"entry",r);}});
    }
    onEntriesChanged:Qt.callLater(syncAgenda)
    function consumeDraft():void {if(Reminders.drafting){root.select(Reminders.focusDate||Dates.key(Time.date));if(!root.editing)root.edit(null);Reminders.drafting=false;}}
    Component.onCompleted:{syncAgenda();consumeDraft();}
    Connections {target:Reminders;function onDraftingChanged(){root.consumeDraft();}function onFocusDateChanged(){if(Reminders.focusDate)root.select(Reminders.focusDate);}}
    Keys.onPressed:event=>{
        if(editing)return;
        if(event.key===Qt.Key_Home){today();event.accepted=true;}
        else if(event.key===Qt.Key_PageUp||event.key===Qt.Key_PageDown){step(event.key===Qt.Key_PageUp?-1:1);event.accepted=true;}
        else if([Qt.Key_Left,Qt.Key_Right,Qt.Key_Up,Qt.Key_Down].includes(event.key)){if(mode!=="days")step(event.key===Qt.Key_Left||event.key===Qt.Key_Up?-1:1);else select(Dates.add(selectedDate,event.key===Qt.Key_Left?-1:event.key===Qt.Key_Right?1:event.key===Qt.Key_Up?-7:7));event.accepted=true;}
        else if(event.key===Qt.Key_Return&&selectedDate>=Dates.key(Time.date)){edit(null);event.accepted=true;}
    }
    SequentialAnimation {
        id:turn
        NumberAnimation {target:calendarBody;property:"opacity";to:0;duration:Tokens.reducedMotion?0:80}
        ScriptAction {script:{if(root.pending){root.year=root.pending.year;root.month=root.pending.month;root.mode=root.pending.mode;root.pending=null;}}}
        NumberAnimation {target:calendarBody;property:"opacity";to:1;duration:Tokens.reducedMotion?0:140;easing.type:Easing.OutCubic}
        onFinished:if(root.pending)restart()
    }
    ColumnLayout {
        width:parent.width;height:root.compactHeight;spacing:6
        opacity:root.editing?0:1;visible:opacity>0;enabled:!root.editing
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
        RowLayout {Layout.fillWidth:true;Layout.minimumHeight:28;Layout.preferredHeight:28;Layout.maximumHeight:28;spacing:4
            IconButton {icon:"chevron_left";label:root.mode==="days"?"Previous month":"Previous years";size:12;background:Theme.surfaceSolid;onClicked:root.step(-1)}
            PanelText {Layout.fillWidth:true;Layout.fillHeight:true;text:root.mode==="days"?Qt.formatDateTime(root.viewDate,"MMMM yyyy"):root.mode==="months"?String(root.year):root.yearBase+"–"+(root.yearBase+11);font.pixelSize:13;font.weight:Font.DemiBold;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter
                MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;acceptedButtons:Qt.LeftButton|Qt.RightButton;onClicked:mouse=>{Reminders.calendarExpanded=false;if(mouse.button===Qt.RightButton)root.today();else root.navigate(root.year,root.month,root.mode==="days"?"months":root.mode==="months"?"years":"days");}}
            }
            IconButton {icon:"chevron_right";label:root.mode==="days"?"Next month":"Next years";size:12;background:Theme.surfaceSolid;onClicked:root.step(1)}
        }
        Item {
            id:calendarBody;Layout.fillWidth:true;Layout.minimumHeight:root.compactHeight-34;Layout.preferredHeight:root.compactHeight-34;Layout.maximumHeight:root.compactHeight-34
            GridLayout {
                anchors.fill:parent;columns:7;rowSpacing:2;columnSpacing:2;visible:root.mode==="days"
                Repeater {model:["S","M","T","W","T","F","S"];PanelText {required property string modelData;Layout.fillWidth:true;Layout.preferredHeight:20;text:modelData;font.pixelSize:10;color:Theme.subtext;horizontalAlignment:Text.AlignHCenter}}
                Repeater {model:42
                    AbstractButton {
                        id:cell;required property int index
                        readonly property date day:new Date(root.year,root.month,index-root.viewDate.getDay()+1,12)
                        readonly property string key:Dates.key(day)
                        readonly property bool today:key===Dates.key(Time.date)
                        readonly property bool selected:Reminders.calendarExpanded&&key===root.selectedDate
                        Layout.fillWidth:true;Layout.fillHeight:true;hoverEnabled:true
                        onClicked:root.toggleDate(key)
                        Accessible.name:Qt.formatDateTime(day,"dddd, d MMMM yyyy")
                        background:Rectangle {anchors.centerIn:parent;width:23;height:23;radius:12;color:cell.today?Theme.accent:cell.pressed?Theme.withAlpha(Theme.text,.1):cell.hovered?Theme.withAlpha(Theme.text,.055):"transparent";border.width:cell.selected?1:0;border.color:Theme.accent;Behavior on color {ColorAnimation {duration:Tokens.animFast}}}
                        contentItem:Item {
                            PanelText {anchors.centerIn:parent;text:cell.day.getDate();font.pixelSize:12;font.weight:cell.today?Font.Medium:Font.Normal;font.features:({tnum:1});color:cell.today?Theme.accentText:cell.selected?Theme.accent:Theme.text;opacity:cell.day.getMonth()===root.month?1:.3}
                            Rectangle {anchors.horizontalCenter:parent.horizontalCenter;y:parent.height-4;width:3;height:3;radius:1.5;color:Theme.accent;visible:Reminders.hasDate(cell.key)}
                        }
                        HoverHandler {cursorShape:Qt.PointingHandCursor}
                    }
                }
            }
            GridLayout {anchors.fill:parent;columns:3;rowSpacing:8;columnSpacing:8;visible:root.mode!=="days"
                Repeater {model:12
                    ChoiceButton {required property int index;Layout.fillWidth:true;Layout.fillHeight:true;text:root.mode==="months"?Qt.formatDateTime(new Date(root.year,index,1),"MMM"):String(root.yearBase+index);selected:root.mode==="months"?index===root.month:root.yearBase+index===root.year;enabled:root.mode==="months"||root.yearBase+index>=1900&&root.yearBase+index<=9999;onClicked:root.mode==="months"?root.navigate(root.year,index,"days"):root.navigate(root.yearBase+index,root.month,"months")}
                }
            }
        }
    }
    ColumnLayout {
        x:0;y:root.compactHeight+8;width:parent.width;height:Math.max(0,parent.height-y);spacing:6
        opacity:!root.editing&&Reminders.calendarExpanded&&height>100?1:0;visible:opacity>0;enabled:!root.editing&&Reminders.calendarExpanded
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
        Rectangle {Layout.fillWidth:true;Layout.preferredHeight:1;color:Theme.withAlpha(Theme.text,.07)}
        RowLayout {Layout.fillWidth:true
            PanelText {Layout.fillWidth:true;text:root.upcoming?"All reminders":Qt.formatDateTime(Dates.parse(root.selectedDate),"ddd, d MMM");font.pixelSize:12;font.weight:Font.Medium}
            IconButton {icon:"notifications";label:root.upcoming?"Selected date":"All reminders";size:16;color:root.upcoming?Theme.accent:Theme.subtext;onClicked:root.upcoming=!root.upcoming}
            IconButton {icon:"add";label:"Add reminder";size:18;enabled:Reminders.loaded&&root.selectedDate>=Dates.key(Time.date);onClicked:root.edit(null)}
        }
        ListView {
            id:agenda;Layout.fillWidth:true;Layout.fillHeight:true;model:ListModel {id:agendaModel} spacing:6;clip:true;boundsBehavior:Flickable.StopAtBounds
            ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
            add:Transition {NumberAnimation {property:"opacity";from:0;to:1;duration:Tokens.animFast}}
            remove:Transition {NumberAnimation {property:"opacity";to:0;duration:Tokens.animFast}}
            displaced:Transition {NumberAnimation {properties:"x,y";duration:Tokens.animMedium;easing.type:Easing.OutCubic}}
            delegate:Rectangle {
                id:row;required property var entry;width:agenda.width-4;height:48;radius:12;color:Theme.surfaceSolid
                IconButton {x:5;anchors.verticalCenter:parent.verticalCenter;icon:row.entry.done?"check_circle":"radio_button_unchecked";label:row.entry.done?"Mark incomplete":"Mark complete";size:17;color:row.entry.done?Theme.accent:Theme.subtext;onClicked:Reminders.complete(row.entry.id,!row.entry.done)}
                Column {x:43;anchors.verticalCenter:parent.verticalCenter;width:parent.width-54;spacing:4
                    PanelText {width:parent.width;text:row.entry.title;font.pixelSize:12;font.strikeout:row.entry.done;opacity:row.entry.done?.5:1}
                    PanelText {width:parent.width;text:(root.upcoming?Qt.formatDateTime(Dates.parse(row.entry.date),"d MMM")+" · ":"")+row.entry.time;font.pixelSize:10;color:Theme.subtext}
                }
                MouseArea {x:40;width:parent.width-40;height:parent.height;cursorShape:Qt.PointingHandCursor;onClicked:{root.selectedDate=row.entry.date;root.edit(row.entry);}}
            }
            PanelText {anchors.centerIn:parent;width:parent.width-24;text:Reminders.error||(!Preferences.remindersEnabled?"Reminder notifications are paused":root.upcoming?"No pending reminders":"No reminders for this day");visible:agenda.count===0;horizontalAlignment:Text.AlignHCenter;font.pixelSize:11;color:Reminders.error?Theme.red:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
        }
        PanelText {Layout.fillWidth:true;visible:agenda.count>0&&!!Reminders.error;text:Reminders.error;font.pixelSize:10;color:Theme.red;wrapMode:Text.Wrap;elide:Text.ElideNone}
    }
    Loader {anchors.fill:parent;active:root.editing||opacity>0;opacity:root.editing?1:0;visible:opacity>0;enabled:root.editing;Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
        sourceComponent:ReminderEditor {day:root.selectedDate;entry:root.edited;onCancelled:{root.editing=false;root.forceActiveFocus();}onSaved:{root.editing=false;root.upcoming=false;root.forceActiveFocus();}}
    }
}
