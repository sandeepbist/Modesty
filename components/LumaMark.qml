import QtQuick
import qs.theme
import qs.services
import "../modules/companion" as Companion

// Window companion: shared pose staging, interactions and physical edge motion.
Item {
    id:root
    property real size:28
    property bool busy:false
    property bool engaged:false
    property bool reacting:false
    property string activity:busy?"composing":engaged?"attending":"idle"
    property string moodOverride:""
    property bool animate:true
    property color color:Theme.accent
    property bool portrait:true
    property bool shown:true
    property bool interactive:false
    property bool typing:false
    // Local response timers must never replace the caller's typing binding.
    property bool responding:false
    readonly property bool typingActive:typing||responding
    property real exposure:portrait||shown?1:0
    property real lift:0
    property real settle:1
    property real revealHeight:size
    property real look:0
    property int interactionCount:0
    property real lastGreeting:0
    property string previousActivity:"idle"
    readonly property bool working:["routing","reading","composing"].includes(activity)
    readonly property bool moving:animate&&!Tokens.reducedMotion
    readonly property bool arriving:moving&&(entrance.running||character.gesture==="arrival")
    readonly property bool departing:departure.running
    signal departed()
    readonly property string gesture:character.gesture
    readonly property int frame:character.frame
    readonly property bool ready:character.ready
    readonly property string baseMood:moodOverride|| (portrait?(working?"working":reacting?"attentive":"idle"):
        activity==="routing"?"thinking":activity==="reading"?"reading":activity==="composing"?"writing":
        typingActive?"writing":activity==="review"||activity==="error"?"attentive":"idle")
    width:size;height:size;implicitWidth:size;implicitHeight:size
    opacity:portrait?1:exposure
    visible:opacity>0
    transform:Scale {origin.x:root.size*.44;origin.y:root.size*.7;xScale:root.settle;yScale:root.settle}
    Accessible.role:interactive?Accessible.Button:Accessible.Graphic
    Accessible.name:"Window companion"
    Accessible.description:working?"Working alongside you":"Tap for a friendly reaction"
    Accessible.ignored:!interactive
    Accessible.onPressAction:interact()

    function respond():void {
        if(!shown||portrait||working)return;
        responding=true;typingRest.restart();
    }
    function react(name:string):void {if(shown&&moving&&!arriving)character.play(name);}
    function interact():void {
        if(!interactive||!shown||!moving)return;
        // Interaction never cancels an answer or executes a desktop action.
        if(working){character.play("glance");return;}
        const actions=["playful","encourage","greeting","stretch","swing","watching","polish","wink"];
        character.play(actions[interactionCount%actions.length]);interactionCount++;
        touchMotion.restart();
    }
    function present():void {
        entrance.stop();departure.stop();
        touchMotion.stop();
        if(!moving){exposure=shown?1:0;lift=shown?0:size*.74;revealHeight=shown?size:size*.7;settle=1;if(!shown)departed();return;}
        if(shown){
            if(exposure===0){lift=size*.74;revealHeight=size*.7;}
            exposure=1;settle=1;
            character.play("arrival");entrance.start();
        }else{
            typingRest.stop();responding=false;
            if(exposure===0){departed();return;}
            character.play("departure");departure.start();
        }
    }
    onShownChanged:if(!portrait)present()
    onActivityChanged:{
        const completed=!["routing","reading","composing"].includes(activity)&&["routing","reading","composing"].includes(previousActivity);
        previousActivity=activity;
        if(!portrait&&shown&&moving){
            if(activity==="error")reaction.name="uncertain";
            else if(completed&&["ready","review"].includes(activity))reaction.name="success";
            else reaction.name="";
            if(reaction.name&&!arriving)reaction.restart();else reaction.stop();
        }
    }
    onArrivingChanged:if(!arriving&&shown&&moving&&reaction.name)reaction.restart()
    onMovingChanged:if(!moving){entrance.stop();departure.stop();touchMotion.stop();exposure=shown?1:0;lift=shown?0:size*.74;revealHeight=shown?size:size*.7;settle=1;responding=false;typingRest.stop();if(!shown)departed();}
    onSizeChanged:if(!arriving&&!departing){revealHeight=shown?size:size*.7;lift=shown?0:size*.74;}
    onVisibleChanged:if(!visible){typingRest.stop();reaction.stop();responding=false;look=0;}
    Component.onCompleted:if(!portrait&&shown)present()

    Timer {id:typingRest;interval:650;onTriggered:root.responding=false}
    Timer {id:reaction;property string name:"";interval:0;onTriggered:{if(root.shown&&root.moving&&!root.arriving)character.play(name);name="";}}
    Timer {
        interval:24000;repeat:true
        running:root.shown&&!root.portrait&&root.moving&&!root.working&&!root.typingActive&&!root.arriving&&!root.moodOverride
        onTriggered:{const actions=["glance","swing","watching"];character.play(actions[root.interactionCount%actions.length]);root.interactionCount++;}
    }
    ParallelAnimation {
        id:entrance
        NumberAnimation {target:root;property:"lift";to:0;duration:1000;easing.type:Easing.InOutCubic}
        SequentialAnimation {
            PauseAnimation {duration:650}
            NumberAnimation {target:root;property:"revealHeight";to:root.size;duration:400;easing.type:Easing.OutQuint}
        }
    }
    ParallelAnimation {
        id:departure
        NumberAnimation {target:root;property:"revealHeight";to:root.size*.7;duration:90;easing.type:Easing.InOutCubic}
        SequentialAnimation {
            PauseAnimation {duration:70}
            NumberAnimation {target:root;property:"lift";to:root.size*.74;duration:290;easing.type:Easing.InCubic}
        }
        onFinished:{root.exposure=0;root.settle=1;root.departed();}
    }
    SequentialAnimation {
        id:touchMotion
        NumberAnimation {target:root;property:"lift";to:-3;duration:150;easing.type:Easing.OutCubic}
        NumberAnimation {target:root;property:"lift";to:0;duration:420;easing.type:Easing.OutQuint}
    }
    Item {
        width:root.size;height:root.portrait?root.size:root.revealHeight
        clip:!root.portrait&&(root.arriving||root.departing)
        Companion.IllustratedCharacter {
        id:character;width:root.size;height:root.size
        transform:Translate {y:root.lift}
        portrait:root.portrait;richAnimations:!root.portrait;ambientEnabled:false
        holdGesture:root.arriving||root.departing
        mood:root.baseMood;animate:root.animate;look:root.look
        Behavior on look {NumberAnimation {duration:Tokens.reducedMotion?0:220;easing.type:Easing.OutQuint}}
        onGestureFinished:name=>{if(name==="arrival"&&root.shown&&!root.working&&!root.typingActive&&!reaction.name)play("acknowledge");}
        }
    }
    MouseArea {
        width:parent.width;height:root.portrait?parent.height:parent.height*.7
        enabled:root.interactive&&root.shown&&!root.arriving;hoverEnabled:true
        cursorShape:Qt.PointingHandCursor
        onEntered:{
            if(root.moving&&!root.working&&!root.typingActive&&Date.now()-root.lastGreeting>14000){character.play("greeting");root.lastGreeting=Date.now();}
        }
        onPositionChanged:mouse=>root.look=Math.max(-1,Math.min(1,(mouse.x-width*.44)/(width*.5)))
        onExited:root.look=0
        onClicked:root.interact()
        onPressAndHold:if(root.moving&&!root.working)character.play("stretch")
    }
}
