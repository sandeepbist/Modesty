import QtQuick
import qs.theme
import "SwordsmanFrames.js" as Art

Item {
    id:root
    property string mood:"idle"
    property bool animate:true
    property bool richAnimations:false
    property bool ambientEnabled:true
    property bool portrait:false
    property bool holdGesture:false
    property real look:0
    signal gestureFinished(string name)
    property int frame:0
    property string gesture:"idle"
    property int step:0
    property int idleVisit:0
    property var timeline:[]
    property bool looping:false
    property real breath:0
    property real lean:0
    property real breeze:0
    property int previousFrame:0
    property int displayedFrame:0
    property real frameBlend:1
    readonly property bool moving:animate&&visible&&!Tokens.reducedMotion
    readonly property var pose:Art.frames[displayedFrame]
    readonly property var previousPose:Art.frames[previousFrame]
    readonly property bool ready:baseAtlas.status===Image.Ready&&(!richAnimations||[entryAtlas,exitAtlas,attentionAtlas,focusAtlas,reactionsAtlas,arrivalAtlas].every(a=>a.status===Image.Ready))
    function unitFor(pose):real {return (portrait?width/250:height*.5/215)*215/(pose.headWidth??215);}
    readonly property real unit:unitFor(pose)
    readonly property real previousUnit:unitFor(previousPose)
    clip:portrait
    readonly property var sequences:({
        idle:[[0,5600],[1,115],[0,3800],[2,800],[0,4300],[1,100],[0,180],[1,95]],
        typing:[[4,210],[5,170],[4,240],[5,200],[4,470],[5,220],[4,170],[5,310]],
        working:[[4,700],[5,300],[4,480],[5,220],[4,1200]],
        watching:[[6,3300],[7,850],[6,4600],[7,1050],[6,2400]],
        sleeping:[[3,10000]],
        doze:[[14,700],[15,650],[3,1600]],
        wave:[[8,240],[9,260],[8,260],[9,330],[8,450],[0,700]],
        happy:[[10,430],[11,310],[10,550],[22,750],[23,300],[0,900]],
        glance:[[12,850],[13,550],[0,600]],
        yawn:[[14,900],[15,650],[1,160],[0,700]],
        stretch:[[17,220],[16,1150],[17,600],[0,500]],
        polish:[[18,650],[19,600],[18,700],[19,550],[18,850],[0,700]],
        swing:[[20,650],[21,650],[20,650],[21,700],[0,550]],
        wink:[[22,650],[23,550],[0,550]],
        arrival:[[60,125],[61,130],[62,135],[63,135],[64,130],[65,135],[66,140],[67,160],[68,180],[69,160],[70,170],[71,190]],
        greeting:[[28,180],[29,190],[30,230],[31,250]],
        departure:[[72,30],[73,30],[74,30],[75,30],[76,30],[77,30],[78,30],[79,30],[80,30],[81,30],[82,30],[83,30]],
        thinking:[[36,1400],[37,1200],[38,850],[39,1400]],
        writing:[[40,210],[41,170],[42,200],[43,230],[42,180],[41,240]],
        reading:[[44,2400],[45,260],[46,230],[47,2100]],
        success:[[48,190],[49,210],[50,450],[51,600]],
        uncertain:[[52,220],[53,420],[54,850],[55,1100]],
        playful:[[56,180],[57,230],[58,600],[59,350]],
        attentive:[[84,2600],[85,650],[86,140],[87,2000]],
        acknowledge:[[88,150],[89,200],[90,220],[91,1000]],
        encourage:[[92,150],[93,260],[94,480],[95,600]]
    })
    function play(name:string):void {if(moving)start(name,false);}
    function atlasFor(sheet:int):var {return [baseAtlas,gestureAtlas,arrivalAtlas,focusAtlas,reactionsAtlas,entryAtlas,exitAtlas,attentionAtlas][sheet]||baseAtlas;}
    onFrameChanged:{
        previousFrame=displayedFrame;displayedFrame=frame;
        frameMotion.stop();frameBlend=1;
        if(moving&&atlasFor(pose.sheet).status===Image.Ready&&atlasFor(previousPose.sheet).status===Image.Ready){frameBlend=0;frameMotion.duration=Math.min(85,(timeline[step]?.[1]||115)*.75);frameMotion.start();}
    }
    NumberAnimation {id:frameMotion;target:root;property:"frameBlend";to:1;duration:85;easing.type:Easing.InOutSine}
    function start(name,repeat):void {
        beat.stop();gesture=name;step=0;looping=repeat;
        const fallback={arrival:"wave",greeting:"wave",departure:"glance",thinking:"idle",writing:"typing",reading:"watching",success:"happy",uncertain:"glance",playful:"wink",attentive:"glance",acknowledge:"glance",encourage:"happy"};
        timeline=sequences[!richAnimations&&fallback[name]?fallback[name]:name]||sequences.idle;
        frame=timeline[0][0];
        if(moving){beat.interval=timeline[0][1];beat.start();}
    }
    function settleMood():void {
        ambient.stop();
        start(mood,["idle","typing","working","watching","sleeping","thinking","writing","reading","attentive"].includes(mood));
        if(mood==="idle"&&moving&&ambientEnabled){ambient.interval=9000+(idleVisit%4)*2100;ambient.start();}
    }
    onMoodChanged:{
        if(holdGesture&&!looping&&moving)return;
        if(gesture==="sleeping"&&mood==="idle"&&moving){start("stretch",false);ambient.restart();}
        else if(mood==="sleeping"&&moving){ambient.stop();start("doze",false);}
        else settleMood();
    }
    onMovingChanged:{
        if(moving)settleMood();
        else {ambient.stop();frameMotion.stop();start(mood,false);frameBlend=1;}
    }
    Component.onCompleted:settleMood()
    Timer {
        id:beat
        onTriggered:{
            root.step++;
            if(root.step>=root.timeline.length){
                if(root.looping)root.step=0;
                else {
                    // A wave or celebration finishes once, even if its feedback
                    // timer has not elapsed. Ambient behaviour resumes quietly.
                    const finished=root.gesture;
                    const continuous=["idle","typing","working","watching","sleeping","thinking","writing","reading","attentive"];
                    root.start(continuous.includes(root.mood)?root.mood:"idle",true);
                    root.gestureFinished(finished);
                    return;
                }
            }
            root.frame=root.timeline[root.step][0];
            interval=root.timeline[root.step][1];
            if(root.moving)restart();
        }
    }
    Timer {
        id:ambient
        onTriggered:{
            if(root.mood!=="idle"||!root.moving||!root.ambientEnabled)return;
            const choices=["glance","swing","polish","glance","stretch","wink","yawn"];
            root.start(choices[root.idleVisit%choices.length],false);root.idleVisit++;
            interval=11000+(root.idleVisit%4)*2300;restart();
        }
    }
    SequentialAnimation on breath {
        running:root.moving;loops:Animation.Infinite
        NumberAnimation {to:1;duration:1900;easing.type:Easing.InOutSine}
        NumberAnimation {to:0;duration:2300;easing.type:Easing.InOutSine}
    }
    SequentialAnimation on lean {
        running:root.moving&&["idle","watching","sleeping","thinking","reading","attentive"].includes(root.mood);loops:Animation.Infinite
        NumberAnimation {to:1;duration:2600;easing.type:Easing.InOutSine}
        NumberAnimation {to:-1;duration:3400;easing.type:Easing.InOutSine}
        NumberAnimation {to:0;duration:1700;easing.type:Easing.InOutSine}
    }
    NumberAnimation on breeze {
        running:root.moving;loops:Animation.Infinite
        from:0;to:Math.PI*2;duration:6200
    }
    // Stable texture providers: changing a gesture never decodes another image.
    Image {
        id:baseAtlas;visible:false
        source:Qt.resolvedUrl("../../assets/companion/swordsman/poses.png")
        sourceSize:Qt.size(1254,1254);smooth:true;mipmap:true;asynchronous:true;cache:true
    }
    Image {
        id:gestureAtlas;visible:false
        source:Qt.resolvedUrl("../../assets/companion/swordsman/gestures.png")
        sourceSize:Qt.size(1254,1254);smooth:true;mipmap:true;asynchronous:true;cache:true
    }
    Image {id:arrivalAtlas;visible:false;source:root.richAnimations?Qt.resolvedUrl("../../assets/companion/swordsman/arrival.png"):"";smooth:true;mipmap:true;asynchronous:true;cache:true}
    Image {id:focusAtlas;visible:false;source:root.richAnimations?Qt.resolvedUrl("../../assets/companion/swordsman/focus.png"):"";smooth:true;mipmap:true;asynchronous:true;cache:true}
    Image {id:reactionsAtlas;visible:false;source:root.richAnimations?Qt.resolvedUrl("../../assets/companion/swordsman/reactions.png"):"";smooth:true;mipmap:true;asynchronous:true;cache:true}
    Image {id:entryAtlas;visible:false;source:root.richAnimations?Qt.resolvedUrl("../../assets/companion/swordsman/entry-v2.png"):"";smooth:true;mipmap:true;asynchronous:true;cache:true}
    Image {id:exitAtlas;visible:false;source:root.richAnimations?Qt.resolvedUrl("../../assets/companion/swordsman/exit-v2.png"):"";smooth:true;mipmap:true;asynchronous:true;cache:true}
    Image {id:attentionAtlas;visible:false;source:root.richAnimations?Qt.resolvedUrl("../../assets/companion/swordsman/attention-v2.png"):"";smooth:true;mipmap:true;asynchronous:true;cache:true}
    Item {
        anchors.fill:parent
        transform:[
            Scale {origin.x:root.width*.44;origin.y:root.height*.70;yScale:1+(root.moving?root.breath*.007:0)},
            Rotation {origin.x:root.width*.44;origin.y:root.height*.70;angle:root.moving?root.lean*.45+root.look*1.25:0}
        ]
        ShaderEffect {
            // Keep each pose's proportions while blending. Stretching the old
            // texture into the new bounds distorts faces during a gesture.
            readonly property real currentX:root.width*(root.portrait?.5:.44)+(root.pose.x-root.pose.anchor)*root.unit
            readonly property real currentY:root.portrait?(root.height-225*root.unit)/2:root.pose.baseline!==undefined?root.height*root.pose.baseline-root.pose.h*root.unit:root.height*.7-root.pose.h*.68*root.unit
            readonly property real oldX:root.width*(root.portrait?.5:.44)+(root.previousPose.x-root.previousPose.anchor)*root.previousUnit
            readonly property real oldY:root.portrait?(root.height-225*root.previousUnit)/2:root.previousPose.baseline!==undefined?root.height*root.previousPose.baseline-root.previousPose.h*root.previousUnit:root.height*.7-root.previousPose.h*.68*root.previousUnit
            x:root.frameBlend<1?Math.min(currentX,oldX):currentX
            y:root.frameBlend<1?Math.min(currentY,oldY):currentY
            width:(root.frameBlend<1?Math.max(currentX+root.pose.w*root.unit,oldX+root.previousPose.w*root.previousUnit):currentX+root.pose.w*root.unit)-x
            height:(root.frameBlend<1?Math.max(currentY+root.pose.h*root.unit,oldY+root.previousPose.h*root.previousUnit):currentY+root.pose.h*root.unit)-y
            property var atlas:root.atlasFor(root.pose.sheet)
            property var previousAtlas:root.atlasFor(root.previousPose.sheet)
            property vector4d previousRect:Qt.vector4d(root.previousPose.x/1254,root.previousPose.y/1254,root.previousPose.w/1254,root.previousPose.h/1254)
            property real blend:root.frameBlend
            property real phase:root.breeze
            property real energy:root.moving?(root.mood==="sleeping"?.45:1):0
            property vector4d frameRect:Qt.vector4d(root.pose.x/1254,root.pose.y/1254,root.pose.w/1254,root.pose.h/1254)
            property vector2d spriteSize:Qt.vector2d(width,height)
            property vector4d currentBounds:Qt.vector4d((currentX-x)/width,(currentY-y)/height,root.pose.w*root.unit/width,root.pose.h*root.unit/height)
            property vector4d previousBounds:Qt.vector4d((oldX-x)/width,(oldY-y)/height,root.previousPose.w*root.previousUnit/width,root.previousPose.h*root.previousUnit/height)
            mesh:GridMesh {resolution:Qt.size(20,24)}
            vertexShader:Qt.resolvedUrl("../../assets/companion/swordsman/shaders/living.vert.qsb")
            fragmentShader:Qt.resolvedUrl("../../assets/companion/swordsman/shaders/living.frag.qsb")
        }
    }
}
