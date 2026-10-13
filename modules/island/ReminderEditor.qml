import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.components
import qs.services
import qs.theme
import "../../services/Calendar.js" as Dates
FocusScope {
    id:root
    property string day:""
    property var entry:null
    readonly property int availableLead:entry?30:Math.max(0,Math.min(30,Dates.distance(day,Dates.key(Time.date))||0))
    property int lead:entry?.lead??Math.min(2,availableLead)
    property int count:entry?.count??Math.min(3,lead+1)
    property bool scheduling:false
    property bool repeating:false
    property string repeatKind:entry?.repeat?.kind||"none"
    property int repeatInterval:entry?.repeat?.interval||1
    property var weekdays:entry?.repeat?.weekdays||[(Dates.parse(day).getDay()||7)]
    property int anchorDay:entry?.repeat?.anchorDay||Dates.parse(day).getDate()
    property string selectedZone:entry?.zone||Reminders.zone
    property string pendingTicket:""
    property bool pendingDelete:false
    readonly property bool saving:pendingTicket!==""
    readonly property var repeatValue:({kind:repeatKind,interval:repeatInterval,weekdays,anchorDay})
    property bool deleteArmed:false
    readonly property var dates:Dates.schedule({date:day,lead,count})
    readonly property string summary:count===1?"Once · "+Qt.formatDateTime(Dates.parse(dates[0]),"d MMM"):count+" reminders · "+Qt.formatDateTime(Dates.parse(dates[0]),"d MMM")+"–"+Qt.formatDateTime(Dates.parse(day),"d MMM")
    signal cancelled()
    signal saved()
    function setLead(value:int):void {lead=value;count=Math.min(count,lead+1);}
    function save():void {
        if(saving)return;
        pendingDelete=false;
        const command={kind:entry?"update":"create",title:titleField.text,date:day,time:timeField.text,lead:repeatKind==="none"?lead:0,count:repeatKind==="none"?count:1,repeat:repeatValue,zone:selectedZone};
        if(entry){command.id=entry.id;command.expectedRevision=entry.revision;}
        const value=Reminders.request(command);if(value.ok)pendingTicket=value.ticket;else Reminders.error=value.error;
    }
    function remove():void {
        const value=Reminders.request({kind:"remove",id:entry.id,expectedRevision:entry.revision});
        if(value.ok){pendingDelete=true;pendingTicket=value.ticket;}else Reminders.error=value.error;
    }
    function checkReceipt():void {
        if(!pendingTicket)return;
        const value=Reminders.receipt(pendingTicket);if(value.status==="pending")return;
        pendingTicket="";if(value.status==="persisted"){if(pendingDelete)root.cancelled();else root.saved();}else Reminders.error=value.error;
    }
    function toggleWeekday(value):void {weekdays=weekdays.includes(value)?weekdays.filter(d=>d!==value):weekdays.concat([value]).sort((a,b)=>a-b);}
    Connections {target:Reminders;function onReceiptsChanged(){root.checkReceipt();}}
    Keys.onEscapePressed:event=>{if(saving){event.accepted=true;}else if(repeating){repeating=false;event.accepted=true;}else if(scheduling){scheduling=false;event.accepted=true;}else{root.cancelled();event.accepted=true;}}
    Component.onCompleted:Qt.callLater(()=>titleField.forceActiveFocus())
    ColumnLayout {
        anchors.fill:parent;spacing:10
        opacity:root.scheduling||root.repeating?0:1;visible:opacity>0;enabled:!root.scheduling&&!root.repeating&&!root.saving
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
        RowLayout {Layout.fillWidth:true
            IconButton {icon:"arrow_back";label:"Back to calendar";onClicked:root.cancelled()}
            PanelText {Layout.fillWidth:true;text:root.entry?"Edit reminder":"New reminder";font.pixelSize:16;font.weight:Font.Medium}
        }
        PanelText {Layout.fillWidth:true;text:Qt.formatDateTime(Dates.parse(root.day),"dddd, d MMMM yyyy");font.pixelSize:12;color:Theme.subtext}
        EntryField {id:titleField;Layout.fillWidth:true;implicitHeight:46;placeholderText:"What would you like to remember?";maximumLength:160;text:root.entry?.title||"";font.pixelSize:14;onAccepted:root.save()}
        RowLayout {Layout.fillWidth:true;spacing:12
            Icon {icon:"schedule";size:18;color:Theme.subtext}
            PanelText {Layout.fillWidth:true;text:"Remind at";font.pixelSize:12}
            EntryField {id:timeField;Layout.preferredWidth:82;text:root.entry?.time||"09:00";maximumLength:5;validator:RegularExpressionValidator {regularExpression:/([01]\d|2[0-3]):[0-5]\d/} horizontalAlignment:Text.AlignHCenter;onAccepted:root.save()}
        }
        RowLayout {Layout.fillWidth:true;spacing:8
        Rectangle {Layout.fillWidth:true;implicitHeight:52;radius:14;color:Theme.surfaceSolid;border.width:1;border.color:Theme.withAlpha(Theme.text,.07)
            Column {x:14;anchors.verticalCenter:parent.verticalCenter;width:parent.width-48;spacing:6
                PanelText {width:parent.width;text:"Advance notices";font.pixelSize:12;font.weight:Font.Medium}
                PanelText {width:parent.width;text:root.repeatKind==="none"?root.summary:"Only for one-time reminders";font.pixelSize:11;color:Theme.subtext}
            }
            Icon {anchors.right:parent.right;anchors.rightMargin:12;anchors.verticalCenter:parent.verticalCenter;icon:"chevron_right";size:16;color:Theme.subtext}
            AbstractButton {id:advanceButton;anchors.fill:parent;hoverEnabled:true;Accessible.name:"Advance notices";enabled:root.repeatKind==="none";onClicked:root.scheduling=true;HoverHandler {cursorShape:Qt.PointingHandCursor}}
        }
        Rectangle {Layout.fillWidth:true;implicitHeight:52;radius:14;color:Theme.surfaceSolid;border.width:1;border.color:Theme.withAlpha(Theme.text,.07)
            Column {x:14;anchors.verticalCenter:parent.verticalCenter;width:parent.width-48;spacing:6
                PanelText {width:parent.width;text:"Repeat";font.pixelSize:12;font.weight:Font.Medium}
                PanelText {width:parent.width;text:Dates.repeatLabel({repeat:root.repeatValue})||"Does not repeat";font.pixelSize:11;color:Theme.subtext}
            }
            Icon {anchors.right:parent.right;anchors.rightMargin:12;anchors.verticalCenter:parent.verticalCenter;icon:"chevron_right";size:16;color:Theme.subtext}
            AbstractButton {id:repeatButton;anchors.fill:parent;hoverEnabled:true;Accessible.name:"Repeat reminder";onClicked:root.repeating=true;HoverHandler {cursorShape:Qt.PointingHandCursor}}
        }
        }
        PanelText {Layout.fillWidth:true;text:"At "+timeField.text+" · "+root.selectedZone+(root.repeatKind==="none"?". Completed reminders stop notifying you.":". Completing an occurrence keeps the series active.");font.pixelSize:11;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
        Item {Layout.fillHeight:true}
        PanelText {Layout.fillWidth:true;visible:!!Reminders.error;text:Reminders.error;font.pixelSize:11;color:Theme.red;wrapMode:Text.Wrap;elide:Text.ElideNone}
        RowLayout {Layout.fillWidth:true
            ActionButton {visible:!!root.entry;text:root.deleteArmed?"Confirm delete":"Delete";onClicked:{if(root.deleteArmed){root.remove();}else root.deleteArmed=true;}}
            ActionButton {Layout.fillWidth:true;text:root.saving?"Saving…":"Save reminder";primary:true;enabled:!root.saving&&Reminders.loaded&&titleField.text.trim().length>0&&timeField.acceptableInput;onClicked:root.save()}
        }
    }
    ColumnLayout {
        anchors.fill:parent;spacing:12
        opacity:root.scheduling?1:0;visible:opacity>0;enabled:root.scheduling
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
        RowLayout {Layout.fillWidth:true
            IconButton {icon:"arrow_back";label:"Back to reminder";onClicked:root.scheduling=false}
            PanelText {Layout.fillWidth:true;text:"Advance notices";font.pixelSize:16;font.weight:Font.Medium}
        }
        PanelText {text:"Start reminding me";font.pixelSize:12;color:Theme.subtext}
        RowLayout {Layout.fillWidth:true;spacing:6
            Repeater {model:[0,1,2,7];ChoiceButton {required property int modelData;Layout.fillWidth:true;text:modelData===0?"On date":modelData===1?"1 day":modelData+" days";enabled:modelData<=root.availableLead;selected:root.lead===modelData;onClicked:root.setLead(modelData)}}
        }
        PreferenceSlider {Layout.fillWidth:true;label:"Days before";display:root.lead===0?"On date":root.lead+" days";from:0;to:root.availableLead;enabled:root.availableLead>0;stepSize:1;value:root.lead;onMoved:value=>root.setLead(value)}
        RowLayout {Layout.fillWidth:true;spacing:6
            ChoiceButton {Layout.fillWidth:true;text:"Once";selected:root.count===1;onClicked:root.count=1}
            ChoiceButton {Layout.fillWidth:true;text:"Twice";enabled:root.lead>0;selected:root.count===2;onClicked:root.count=2}
            ChoiceButton {Layout.fillWidth:true;text:"Every day";enabled:root.lead>0;selected:root.lead>1&&root.count===root.lead+1;onClicked:root.count=root.lead+1}
        }
        PreferenceSlider {Layout.fillWidth:true;label:"Number of reminders";display:String(root.count);from:1;to:Math.max(1,root.lead+1);enabled:root.lead>0;stepSize:1;value:root.count;onMoved:value=>root.count=value}
        PanelText {Layout.fillWidth:true;text:root.dates.slice(0,5).map(d=>Qt.formatDateTime(Dates.parse(d),"d MMM")).join(" · ")+(root.dates.length>5?" · +"+(root.dates.length-5)+" more":"");font.pixelSize:12;wrapMode:Text.Wrap;elide:Text.ElideNone;color:Theme.accent}
        PanelText {Layout.fillWidth:true;text:root.count===1?"One reminder at the start of your chosen window.":"Spaced across your chosen days, including the first day and the date itself.";font.pixelSize:11;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
        Item {Layout.fillHeight:true}
        ActionButton {Layout.fillWidth:true;text:"Done";onClicked:root.scheduling=false}
    }
    ColumnLayout {
        anchors.fill:parent;spacing:8
        opacity:root.repeating?1:0;visible:opacity>0;enabled:root.repeating&&!root.saving
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
        RowLayout {Layout.fillWidth:true
            IconButton {icon:"arrow_back";label:"Back to reminder";onClicked:root.repeating=false}
            PanelText {Layout.fillWidth:true;text:"Repeat reminder";font.pixelSize:16;font.weight:Font.Medium}
        }
        RowLayout {Layout.fillWidth:true;spacing:4
            Repeater {model:["none","daily","weekly","monthly"];ChoiceButton {required property string modelData;Layout.fillWidth:true;text:({none:"Never",daily:"Daily",weekly:"Weekly",monthly:"Monthly"})[modelData];selected:root.repeatKind===modelData;onClicked:root.repeatKind=modelData}}
        }
        ChoiceButton {Layout.fillWidth:true;text:"Weekdays · Monday to Friday";selected:root.repeatKind==="weekly"&&JSON.stringify(root.weekdays)==="[1,2,3,4,5]";onClicked:{root.repeatKind="weekly";root.repeatInterval=1;root.weekdays=[1,2,3,4,5];}}
        RowLayout {Layout.fillWidth:true;visible:root.repeatKind!=="none"
            PanelText {Layout.fillWidth:true;text:"Every";font.pixelSize:12}
            EntryField {id:intervalField;Layout.preferredWidth:54;text:String(root.repeatInterval);maximumLength:3;validator:IntValidator {bottom:1;top:365} onTextEdited:if(acceptableInput)root.repeatInterval=Number(text);horizontalAlignment:Text.AlignHCenter}
            PanelText {text:({daily:"days",weekly:"weeks",monthly:"months"})[root.repeatKind]||"";font.pixelSize:12;color:Theme.subtext}
        }
        RowLayout {Layout.fillWidth:true;spacing:4;visible:root.repeatKind==="weekly"
            Repeater {model:7;ChoiceButton {required property int index;Layout.fillWidth:true;text:["M","T","W","T","F","S","S"][index];Accessible.name:["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][index];selected:root.weekdays.includes(index+1);onClicked:root.toggleWeekday(index+1)}}
        }
        RowLayout {Layout.fillWidth:true;visible:root.repeatKind==="monthly"
            PanelText {Layout.fillWidth:true;text:"Day of month";font.pixelSize:12}
            EntryField {id:anchorField;Layout.preferredWidth:54;text:String(root.anchorDay);maximumLength:2;validator:IntValidator {bottom:1;top:31} onTextEdited:if(acceptableInput)root.anchorDay=Number(text);horizontalAlignment:Text.AlignHCenter}
        }
        PanelText {Layout.fillWidth:true;visible:root.repeatKind==="monthly";text:"Short months use their last day. The original day returns in longer months.";font.pixelSize:11;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
        EntryField {Layout.fillWidth:true;text:root.selectedZone;placeholderText:"Timezone, such as Asia/Kolkata";Accessible.name:"Reminder timezone";onTextEdited:root.selectedZone=text.trim()}
        PanelText {Layout.fillWidth:true;text:"Repeats follow this timezone's calendar. Completion advances the series; Delete cancels it.";font.pixelSize:11;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
        Item {Layout.fillHeight:true}
        ActionButton {Layout.fillWidth:true;text:"Done";enabled:!!root.selectedZone&&(root.repeatKind==="none"||intervalField.acceptableInput)&&(root.repeatKind!=="monthly"||anchorField.acceptableInput)&&(root.repeatKind!=="weekly"||root.weekdays.length>0);onClicked:root.repeating=false}
    }
}
