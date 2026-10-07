pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import qs.theme

Singleton {
    id: root
    property var tasks: []
    property var observed: []
    property var pending: []
    property bool available: false
    property bool seeded: false
    property bool startPending: false
    property bool pulse: false
    property int index: -1
    property string providerLabel: ""
    property string kind: "working"
    readonly property bool waiting: kind === "waiting"
    readonly property string statusLabel: ({working:"Working",waiting:"Reply",completed:"Done",error:"Issue",interrupted:"Stopped"})[kind] || "Working"
    readonly property string shownLabel: providerLabel + " " + statusLabel
    readonly property bool enabled: Preferences.agentActivity && Preferences.contextEvents && !Preferences.preview
    readonly property bool active: enabled && tasks.length > 0
    readonly property bool needsAttention: enabled && Preferences.agentFeedback && tasks.some(t=>t.waiting)
    readonly property bool canPresent: enabled && !IslandState.menuOpen && !IslandState.settingsOpen && !Context.active && !Notifications.popups.length && !Session.isLocked()
    signal feedback(string outcome)
    TextMetrics {id:providerMeasure;font.family:Tokens.font;font.pixelSize:13;font.weight:Font.DemiBold;text:root.providerLabel}
    readonly property real width: Math.max(Preferences.collapsedWidth,Math.min(240,Math.ceil(providerMeasure.advanceWidth)+48))
    function refresh(): void {if(enabled&&!reader.running)reader.running=true;}
    function endPulse(): void {if(pulse)settle.restart();pulse=false;duration.stop();}
    function enqueue(provider, outcome): void {
        if(!Preferences.agentFeedback)return;
        pending=pending.filter(e=>e.until>Date.now()&&!(e.provider===provider&&e.kind===outcome)).concat([{provider,kind:outcome,until:Date.now()+60000}]).slice(-4);
        feedback(outcome);
    }
    function receive(result): void {
        if(!enabled)return;
        if(!result.available){available=false;tasks=[];observed=[];pending=[];seeded=false;startPending=false;endPulse();return;}
        const next=result.tasks||[];
        const wasActive=tasks.length>0;
        const unresolved=[];
        if(seeded){
            for(const previous of observed){
                if(next.some(t=>t.id===previous.id&&t.turn===previous.turn))continue;
                const ended=(result.recent||[]).find(t=>t.id===previous.id&&t.turn===previous.turn);
                if(ended)enqueue(previous.provider,ended.state);
                else if(!previous.missingUntil||previous.missingUntil>Date.now())unresolved.push(Object.assign({},previous,{missingUntil:previous.missingUntil||Date.now()+10000}));
            }
        }
        for(const task of next)if(task.waiting&&!observed.some(t=>t.id===task.id&&t.turn===task.turn&&t.waiting))enqueue(task.provider,"waiting");
        available=true;tasks=next;observed=next.concat(unresolved);seeded=true;
        if(!wasActive&&next.length&&!next.some(t=>t.waiting)){startPending=true;started.restart();}
        if(!next.length)startPending=false;
        if(!tasks.length&&kind==="working")endPulse();
        if(kind==="waiting"&&!needsAttention)endPulse();
    }
    function present(provider,outcome): void {providerLabel=provider;kind=outcome;pulse=true;duration.restart();}
    function focusT3(): void {
        const client=Hyprland.toplevels.values.find(t=>/t3code/i.test(t.lastIpcObject.class||""));
        if(!client)return;
        IslandState.closeMenu();endPulse();
        const address=client.address.replace(/^0x/,"");
        if(/^[0-9a-f]+$/i.test(address))Quickshell.execDetached(["hyprctl","eval","hl.dispatch(hl.dsp.focus({window='address:0x"+address+"'}))"]);
    }
    onEnabledChanged: {if(enabled)refresh();else{tasks=[];observed=[];pending=[];available=false;seeded=false;startPending=false;endPulse();}}
    onCanPresentChanged: {if(!canPresent)endPulse();else if(startPending)started.restart();}
    Connections {target:Preferences;function onAgentFeedbackChanged(){if(!Preferences.agentFeedback){root.pending=[];if(root.kind!=="working")root.endPulse();}}}
    Component.onCompleted: refresh()
    Timer {interval:root.available?2500:10000;running:root.enabled;repeat:true;onTriggered:root.refresh()}
    Process {
        id:reader
        command:["python3",Qt.resolvedUrl("../scripts/t3-status.py").toString().replace("file://","")]
        stdout:StdioCollector {onStreamFinished:{try{root.receive(JSON.parse(text));}catch(e){root.receive({available:false});}}}
        onExited:code=>{if(code!==0)root.receive({available:false});}
    }
    Timer {
        interval:300;running:root.canPresent&&!root.pulse&&!settle.running&&root.pending.length>0
        onTriggered:{
            const queue=root.pending.filter(e=>e.until>Date.now()&&(e.kind!=="waiting"||root.tasks.some(t=>t.provider===e.provider&&t.waiting)));
            root.pending=queue.slice(1);
            if(queue.length)root.present(queue[0].provider,queue[0].kind);
        }
    }
    Timer {
        id:started
        interval:400
        onTriggered: {
            if(!root.canPresent)return;
            root.startPending=false;
            if(!root.active||root.pulse||root.pending.length)return;
            const provider=root.tasks[0].provider, count=root.tasks.filter(t=>t.provider===provider).length;
            root.present(provider+(count>1?" ×"+count:""),"working");
        }
    }
    Timer {
        interval:Preferences.agentActivityInterval*1000
        running:root.canPresent&&root.active&&!root.pulse&&!settle.running&&!root.pending.length
        repeat:true
        onTriggered:{
            const providers=[...new Set(root.tasks.map(t=>t.provider))];
            root.index=(root.index+1)%providers.length;
            const provider=providers[root.index], matching=root.tasks.filter(t=>t.provider===provider);
            root.present(provider+(matching.length>1?" ×"+matching.length:""),Preferences.agentFeedback&&matching.some(t=>t.waiting)?"waiting":"working");
        }
    }
    Timer {id:settle;interval:Tokens.morphDuration+Tokens.collapseDuration+60}
    Timer {id:duration;interval:root.kind==="working"?2400:3800;onTriggered:root.endPulse()}
}
