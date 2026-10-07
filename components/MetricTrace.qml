import QtQuick
import qs.theme
Canvas {
    id: root
    property var values: []
    property color stroke: Theme.accent
    property real ceiling: 1
    onValuesChanged: requestPaint()
    onStrokeChanged: requestPaint()
    onCeilingChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        const ctx = getContext("2d"); ctx.reset();
        const points = values.slice(-30);
        if (!points.length || width <= 0 || height <= 0) return;
        const y = n => height-2-Math.max(0,Math.min(1,n/Math.max(.001,ceiling)))*(height-5);
        const step = width/29;
        const start = width-(points.length-1)*step;
        ctx.beginPath(); ctx.moveTo(start,y(points[0]));
        for(let i=1;i<points.length;i++)ctx.lineTo(start+i*step,y(points[i]));
        ctx.strokeStyle=stroke;ctx.lineWidth=1.6;ctx.lineJoin="round";ctx.lineCap="round";ctx.stroke();
        ctx.lineTo(width,height);ctx.lineTo(start,height);ctx.closePath();
        const gradient=ctx.createLinearGradient(0,0,0,height);
        gradient.addColorStop(0,Qt.rgba(stroke.r,stroke.g,stroke.b,.18));
        gradient.addColorStop(1,Qt.rgba(stroke.r,stroke.g,stroke.b,0));
        ctx.fillStyle=gradient;ctx.fill();
    }
}
