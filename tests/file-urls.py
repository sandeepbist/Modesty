#!/usr/bin/env python3
"""Load images with URL delimiters in filenames through the shared QML path helper."""
import json
from pathlib import Path
import tempfile
from PIL import Image
from qml import run

with tempfile.TemporaryDirectory(prefix='modesty-file-url-check-') as temporary:
    folder = Path(temporary)
    paths = [folder / name for name in ('preview #1.png', 'preview ?1.png', 'preview %20.png', '日本語 image.png')]
    for path in paths: Image.new('RGB', (8, 8), 'red').save(path)
    run('''import QtQuick
import Quickshell
import "services/FileUrls.js" as FileUrls
ShellRoot {
    property var paths: PATHS
    Item { Repeater { id: images;model:paths;Image { required property string modelData;source:FileUrls.fromPath(modelData) } } }
    property double deadline: Date.now()+3000
    Timer {interval:50;running:true;repeat:true;onTriggered:{try {
        if(Date.now()>deadline)throw new Error("Image path loading timed out");
        if(FileUrls.fromPath("")!=="")throw new Error("Empty path produced a URL");
        for(let i=0;i<images.count;i++) {
            const image=images.itemAt(i);
            if(image.status===Image.Error)throw new Error("Encoded image failed: "+image.modelData);
            if(image.status!==Image.Ready)return;
        }
        console.log("FILE URL CHECK PASS: delimiters, literal percent and Unicode image paths");Qt.quit();
    }catch(error){console.error(error);Qt.exit(1);}}}
}
'''.replace('PATHS', json.dumps([str(path) for path in paths])), 'FILE URL CHECK PASS: delimiters, literal percent and Unicode image paths')
