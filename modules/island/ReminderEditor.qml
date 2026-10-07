import QtQuick
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
    property bool deleteArmed:false
    readonly property var dates:Dates.schedule({date:day,lead,count})
    readonly property string summary:count===1?"Once · "+Qt.formatDateTime(Dates.parse(dates[0]),"d MMM"):count+" reminders · "+Qt.formatDateTime(Dates.parse(dates[0]),"d MMM")+"–"+Qt.formatDateTime(Dates.parse(day),"d MMM")
    signal cancelled()
    signal saved()
    function setLead(value:int):void {lead=value;count=Math.min(count,lead+1);}
    function save():void {if(Reminders.store(entry?.id||"",titleField.text,day,timeField.text,lead,count))root.saved();}
    Keys.onEscapePressed:event=>{if(scheduling){scheduling=false;event.accepted=true;}else{root.cancelled();event.accepted=true;}}
    Component.onCompleted:Qt.callLater(()=>titleField.forceActiveFocus())
    ColumnLayout {
        anchors.fill:parent;spacing:14
        opacity:root.scheduling?0:1;visible:opacity>0;enabled:!root.scheduling
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
        Rectangle {Layout.fillWidth:true;implicitHeight:70;radius:14;color:Theme.surfaceSolid;border.width:1;border.color:Theme.withAlpha(Theme.text,.07)
            Column {x:14;anchors.verticalCenter:parent.verticalCenter;width:parent.width-48;spacing:6
                PanelText {width:parent.width;text:"Schedule";font.pixelSize:12;font.weight:Font.Medium}
                PanelText {width:parent.width;text:root.summary;font.pixelSize:11;color:Theme.subtext}
            }
            Icon {anchors.right:parent.right;anchors.rightMargin:12;anchors.verticalCenter:parent.verticalCenter;icon:"chevron_right";size:16;color:Theme.subtext}
            MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:root.scheduling=true}
        }
        PanelText {Layout.fillWidth:true;text:!root.entry&&Dates.timestamp(root.dates[0],timeField.text)<=Time.date.getTime()?"The first reminder is due now and will appear when you save.":"At "+timeField.text+" in your local time. Completed reminders stop notifying you.";font.pixelSize:11;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
        Item {Layout.fillHeight:true}
        PanelText {Layout.fillWidth:true;visible:!!Reminders.error;text:Reminders.error;font.pixelSize:11;color:Theme.red;wrapMode:Text.Wrap;elide:Text.ElideNone}
        RowLayout {Layout.fillWidth:true
            ActionButton {visible:!!root.entry;text:root.deleteArmed?"Confirm delete":"Delete";onClicked:{if(root.deleteArmed){Reminders.remove(root.entry.id);root.cancelled();}else root.deleteArmed=true;}}
            ActionButton {Layout.fillWidth:true;text:"Save reminder";primary:true;enabled:Reminders.loaded&&titleField.text.trim().length>0&&timeField.acceptableInput;onClicked:root.save()}
        }
    }
    ColumnLayout {
        anchors.fill:parent;spacing:12
        opacity:root.scheduling?1:0;visible:opacity>0;enabled:root.scheduling
        Behavior on opacity {NumberAnimation {duration:Tokens.animFast}}
        RowLayout {Layout.fillWidth:true
            IconButton {icon:"arrow_back";label:"Back to reminder";onClicked:root.scheduling=false}
            PanelText {Layout.fillWidth:true;text:"Reminder schedule";font.pixelSize:16;font.weight:Font.Medium}
        }
        PanelText {text:"Start reminding me";font.pixelSize:12;color:Theme.subtext}
        RowLayout {Layout.fillWidth:true;spacing:6
            Repeater {model:[0,1,2,7];ChoiceButton {required property int modelData;Layout.fillWidth:true;text:modelData===0?"On date":modelData===1?"1 day":modelData+" days";enabled:modelData<=root.availableLead;selected:root.lead===modelData;onClicked:root.setLead(modelData)}}
        }
        PreferenceSlider {Layout.fillWidth:true;label:"Days before";display:root.lead===0?"On date":root.lead+" days";from:0;to:root.availableLead;enabled:root.availableLead>0;stepSize:1;value:root.lead;onMoved:value=>root.setLead(value)}
        RowLayout {Layout.fillWidth:true;spacing:6
            ChoiceButton {Layout.fillWidth:true;text:"Once";selected:root.count===1;onClicked:root.count=1}
            ChoiceButton {Layout.fillWidth:true;text:"Twice";enabled:root.lead>0;selected:root.count===2;onClicked:root.count=2}
            ChoiceButton {Layout.fillWidth:true;text:"Daily";enabled:root.lead>0;selected:root.lead>1&&root.count===root.lead+1;onClicked:root.count=root.lead+1}
        }
        PreferenceSlider {Layout.fillWidth:true;label:"Number of reminders";display:String(root.count);from:1;to:Math.max(1,root.lead+1);enabled:root.lead>0;stepSize:1;value:root.count;onMoved:value=>root.count=value}
        PanelText {Layout.fillWidth:true;text:root.dates.slice(0,5).map(d=>Qt.formatDateTime(Dates.parse(d),"d MMM")).join(" · ")+(root.dates.length>5?" · +"+(root.dates.length-5)+" more":"");font.pixelSize:12;wrapMode:Text.Wrap;elide:Text.ElideNone;color:Theme.accent}
        PanelText {Layout.fillWidth:true;text:root.count===1?"One reminder at the start of your chosen window.":"Spaced across your chosen days, including the first day and the date itself.";font.pixelSize:11;color:Theme.subtext;wrapMode:Text.Wrap;elide:Text.ElideNone}
        Item {Layout.fillHeight:true}
        ActionButton {Layout.fillWidth:true;text:"Done";onClicked:root.scheduling=false}
    }
}
