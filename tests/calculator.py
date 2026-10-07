#!/usr/bin/env python3
"""Exercise production search bindings and calculator workers without a compositor."""
from pathlib import Path
import tempfile
from qml import run

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='modesty-calculator-') as directory:
    workspace = Path(directory)
    canvas = workspace / 'modules/canvas'
    canvas.mkdir(parents=True)
    for source in (ROOT / 'modules/canvas').iterdir():
        (canvas / source.name).symlink_to(source)
    for name in ('services', 'scripts'):
        (workspace / name).symlink_to(ROOT / name, target_is_directory=True)
    source = (ROOT / 'modules/canvas/CommandCanvas.qml').read_text()
    # Replace only the layer-shell/focus facade. Keep production input, query,
    # scope bindings, timers, workers and result delegates unchanged.
    imports = source[:source.index('PanelWindow {')]
    body = source[source.index('    property Item originItem'):]
    (canvas / 'CalculatorCanvas.qml').write_text(imports + '''FloatingWindow {
        id:window
        property bool acquireFocus:false
        implicitWidth:1920;implicitHeight:1080
        visible:CanvasState.opened
    ''' + body)
    run('''import QtQuick
import Quickshell
import "MODULE" as Canvas
import qs.services
ShellRoot {
    id:root
    property int stage:0
    property int ticks:0
    Canvas.CalculatorCanvas {id:canvas}
    function check(ok,label) {if(!ok)throw new Error(label);}
    Timer {interval:50;repeat:true;running:true;onTriggered:{
        try {
            check(++root.ticks<100,"Calculator never finished: "+JSON.stringify(canvas.diagnostics()));
            const state=canvas.diagnostics();
            if(root.stage===0){CanvasState.show();canvas.search("=2+2");root.stage++;}
            else if(root.stage===1&&state.results.some(r=>r.kind==="calculation"&&r.title==="4")){
                check(!state.aiRunning&&!state.answerRunning,"Calculation submitted an AI request");
                canvas.search("=3+7");root.stage++;
            } else if(root.stage===2&&state.results.some(r=>r.kind==="calculation"&&r.title==="10")){
                canvas.search("=5+6");canvas.search("=8+9");root.stage++;
            } else if(root.stage===3&&state.results.some(r=>r.kind==="calculation"&&r.title==="17")){
                canvas.search("=12*13");root.stage++;
            } else if(root.stage===4&&state.calculatorPending){
                CanvasState.close();
                check(!canvas.diagnostics().calculatorPending,"Closing search retained a queued calculation");
                root.stage++;
            } else if(root.stage===5&&!state.open&&!state.query){
                CanvasState.show();canvas.search("=6*7");root.stage++;
            } else if(root.stage===6&&state.results.some(r=>r.kind==="calculation"&&r.title==="42")){
                console.log("CALCULATOR CHECK PASS");Qt.quit();
            }
        } catch(error){console.error(error);Qt.exit(1);}
    }}
}
'''.replace('MODULE', canvas.as_uri()), 'CALCULATOR CHECK PASS')
