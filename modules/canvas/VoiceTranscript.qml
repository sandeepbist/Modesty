import QtQuick
import qs.components
import qs.theme
import "../../services/ModelDiff.js" as ModelDiff

// Keep heard words mounted. Reveal only new/corrected words; center each line.
Item {
    id:root
    property string text:""
    property font font:Qt.font({family:Tokens.font,pixelSize:20,weight:Font.Normal,preferTypoLineMetrics:true,hintingPreference:Font.PreferVerticalHinting})
    property color color:Theme.text
    property real lineHeight:1.28
    property bool animate:true
    property bool ready:false
    property int lineCount:1
    readonly property real lineSize:Math.ceil(font.pixelSize*lineHeight)
    implicitHeight:lineCount*lineSize
    Accessible.name:text
    Accessible.role:Accessible.StaticText
    ListModel {id:words}
    TextMetrics {id:measure;font:root.font}
    function sync():void {
        if(!ready||width<=0)return;
        const all=text.trim().split(/\s+/).filter(Boolean);
        // The live viewport shows three lines; bound layout work on long speech.
        const start=Math.max(0,all.length-96),next=[],lines=[];
        measure.text=" ";const gap=Math.max(3,measure.advanceWidth);
        let line=[],extent=0;
        for(let i=start;i<all.length;i++){
            measure.text=all[i];const w=Math.min(width,Math.ceil(measure.advanceWidth));
            if(line.length&&extent+gap+w>width){lines.push({items:line,extent});line=[];extent=0;}
            const row={key:String(i),word:all[i],w,x:extent+(line.length?gap:0),y:0};
            extent=row.x+w;line.push(row);
        }
        if(line.length)lines.push({items:line,extent});
        for(let i=0;i<lines.length;i++)for(const row of lines[i].items){row.x+=(width-lines[i].extent)/2;row.y=i*lineSize;next.push(row);}
        lineCount=Math.max(1,lines.length);
        ModelDiff.reconcile(words,next,"key");
    }
    onTextChanged:sync()
    onWidthChanged:if(ready)Qt.callLater(sync)
    onFontChanged:if(ready)Qt.callLater(sync)
    onLineSizeChanged:if(ready)Qt.callLater(sync)
    Component.onCompleted:{ready=true;sync();}
    Repeater {
        model:words
        delegate:Item {
            id:word;required property var model
            property bool mounted:false
            x:model.x;y:model.y;width:model.w;height:root.lineSize
            Behavior on x {enabled:word.mounted&&root.animate&&!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:140;reversingMode:SmoothedAnimation.Immediate}}
            Behavior on y {enabled:word.mounted&&root.animate&&!Tokens.reducedMotion;SmoothedAnimation {velocity:-1;duration:160;reversingMode:SmoothedAnimation.Immediate}}
            function arrive():void {if(root.animate&&!Tokens.reducedMotion){reveal.restart();rise.restart();}}
            Component.onCompleted:{mounted=true;arrive();}
            PanelText {
                id:label;anchors.fill:parent;text:word.model.word;font:root.font;color:root.color
                verticalAlignment:Text.AlignVCenter
                onTextChanged:if(word.mounted)word.arrive()
                transform:Translate {id:lift;y:0}
            }
            OpacityAnimator {id:reveal;target:label;from:.35;to:1;duration:140;easing.type:Easing.OutCubic}
            NumberAnimation {id:rise;target:lift;property:"y";from:2;to:0;duration:160;easing.type:Easing.OutCubic}
        }
    }
}
