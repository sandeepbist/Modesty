#!/usr/bin/env python3
"""Exercise real conversation views, updates, rich text and role changes offline."""
from qml import run

run('''import QtQuick
import Quickshell
import "modules/canvas" as Canvas
import "services/ModelDiff.js" as ModelDiff
ShellRoot {
    id:root
    property int stage:0
    property int ticks:0
    property int expandedSignals:0
    property real userHeight:0
    property var firstWord:null
    ListModel {id:rows}
    FloatingWindow {
        visible:true;implicitWidth:620;implicitHeight:800
        Column {
            Repeater {id:turns;model:rows
                Canvas.ConversationTurn {width:600;animate:false;onExpanded:root.expandedSignals++}
            }
        }
        Canvas.VoiceTranscript {id:voice;y:600;width:280;text:"Hello from Modesty";animate:false}
    }
    function descendants(item,type) {
        let found=[];
        for(const child of item.children||[]){
            if(String(child).includes(type))found.push(child);
            found=found.concat(descendants(child,type));
        }
        return found;
    }
    function check(ok,label) {if(!ok)throw new Error(label);}
    Component.onCompleted:rows.append({key:"user",role:"user",text:"**Literal text**",presentation:"{}",citations:"[]",execution:"[]",fresh:false})
    Timer {interval:80;running:true;repeat:true;onTriggered:{
        try {
            check(++root.ticks<60,"Conversation check timed out");
            const user=turns.itemAt(0);
            if(root.stage===0&&user?.naturalHeight>0){
                check(descendants(user,"LumaDocument").length===0,"User message constructed an assistant document");
                const texts=descendants(user,"QQuickTextEdit");
                check(texts.length===1&&texts[0].text==="**Literal text**"&&texts[0].readOnly&&texts[0].selectByMouse,"User text lost plain text or selection");
                root.userHeight=user.naturalHeight;
                rows.setProperty(0,"text","Line one\\nLine two\\nLine three");
                root.stage++;
            } else if(root.stage===1&&user.naturalHeight>root.userHeight){
                check(descendants(user,"LumaDocument").length===0,"Updating user text constructed rich text");
                rows.append({key:"assistant",role:"assistant",text:"# Answer\\n\\n**Readable** text\\n\\n```sh\\nprintf hello\\n```",presentation:"{}",citations:JSON.stringify([{title:"Example",url:"https://example.com",snippet:"A source"}]),execution:JSON.stringify([{tool:{name:"example",purpose:"Example action"},result:{ok:true}}]),fresh:false});
                root.stage++;
            } else if(root.stage===2&&turns.itemAt(1)?.naturalHeight>0){
                const assistant=turns.itemAt(1);
                check(descendants(assistant,"LumaDocument").length===1,"Assistant document missing");
                check(descendants(assistant,"LumaSources")[0].sources.length===1,"Citations missing");
                check(descendants(assistant,"LumaActions")[0].entries.length===1,"Action receipts missing");
                const source=descendants(assistant,"LumaSources")[0];
                source.children[0].children.find(child=>String(child).includes("AbstractButton")).clicked();
                check(source.selected===0&&root.expandedSignals===1,"Citation preview stopped forwarding its expansion signal");
                const text=descendants(assistant,"QQuickTextEdit");
                check(text.some(t=>t.text==="printf hello"&&t.selectByMouse),"Code selection missing");
                check(text.some(t=>t.text.includes("Readable")),"Formatted prose missing");
                const kept=user;
                ModelDiff.reconcile(rows,[{key:"user",role:"user",text:"Line one\\nLine two\\nLine three",presentation:"{}",citations:"[]",execution:"[]",fresh:false},{key:"assistant",role:"assistant",text:"Updated answer",presentation:"{}",citations:"[]",execution:"[]",fresh:false}],"key");
                check(turns.itemAt(0)===kept,"Streaming update recreated an existing turn");
                root.stage++;
            } else if(root.stage===3&&descendants(turns.itemAt(1),"LumaDocument")[0].text==="Updated answer"){
                const sources=descendants(turns.itemAt(1),"LumaSources")[0];
                check(!sources.visible,"Removed citations remained visible");
                rows.setProperty(1,"role","user");
                root.stage++;
            } else if(root.stage===4&&descendants(turns.itemAt(1),"LumaDocument").length===0){
                check(descendants(turns.itemAt(1),"QQuickTextEdit").length===1,"Role switch retained unused assistant views");
                rows.append({key:"fresh",role:"assistant",text:"A new answer",presentation:"{}",citations:"[]",execution:"[]",fresh:true});
                root.stage++;
            } else if(root.stage===5){
                const fresh=turns.itemAt(2);
                check(fresh.arrival>0&&fresh.arrival<1&&fresh.height<fresh.naturalHeight,"New answer lost its entrance animation");
                root.stage++;
            } else if(root.stage===6&&turns.itemAt(2).arrival>.999){
                const words=voice.children.filter(child=>child.model?.word!==undefined);
                check(words.length===3,"Voice transcript lost words");
                root.firstWord=words[0];voice.text="Hello from Quickshell";root.stage++;
            } else if(root.stage===7){
                const words=voice.children.filter(child=>child.model?.word!==undefined);
                check(words[0]===root.firstWord&&words[2].model.word==="Quickshell","Transcript revision recreated unchanged words or lost the correction");
                voice.width=180;root.stage++;
            } else if(root.stage===8){
                const words=voice.children.filter(child=>child.model?.word!==undefined);
                check(words.every(word=>word.x>=0&&word.x+word.width<=voice.width+.01),"Transcript wrapping placed words outside the viewport");
                console.log("CONVERSATION CHECK PASS");Qt.quit();
            }
        } catch(error){console.error(error);Qt.exit(1);}
    }}
}
''', 'CONVERSATION CHECK PASS')
