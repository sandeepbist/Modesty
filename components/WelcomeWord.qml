import QtQuick
import qs.theme

// The pen follows a continuous cursive path. Painting stops with the animation.
Canvas {
    id:root
    property real progress:1
    property color ink:Theme.text
    property var strokes:[]
    property real length:0
    property rect inkBounds:Qt.rect(0,0,116,34)
    antialiasing:true
    readonly property var curves:[
        [[2,9],[4,3,9,1,8,6],[7,13,4,22,6,27],[9,30,14,12,16,7],[15,15,11,25,15,28],[19,29,24,14,26,5],[28,0,32,1,28,8]],
        [[24,23],[29,17,34,16,33,21],[32,25,26,25,27,23],[24,28,31,32,36,27],
         [43,18,48,5,43,3],[38,1,36,13,38,22],[38,30,44,31,48,26],
         [54,19,58,16,59,20],[55,15,50,20,50,25],[50,32,57,31,62,26],
         [65,18,73,18,73,23],[73,30,64,32,64,25],[64,19,69,17,73,21],[73,26,77,25,80,21],
         [79,23,78,27,79,28],[83,17,88,16,86,23],[85,25,84,27,85,28],[89,17,96,16,93,24],[92,30,97,29,100,25],
         [103,17,110,17,108,22],[106,25,101,25,101,23],[99,29,106,32,114,25]]
    ]
    function trace():void {
        const output=[];
        let distance=0;
        for(const path of curves){
            let previous=path[0];
            const points=[{x:previous[0],y:previous[1],d:distance}];
            for(let c=1;c<path.length;c++){
                const curve=path[c],start=previous;
                for(let step=1;step<=24;step++){
                    const t=step/24,u=1-t;
                    const x=u*u*u*start[0]+3*u*u*t*curve[0]+3*u*t*t*curve[2]+t*t*t*curve[4];
                    const y=u*u*u*start[1]+3*u*u*t*curve[1]+3*u*t*t*curve[3]+t*t*t*curve[5];
                    const last=points[points.length-1];
                    distance+=Math.hypot(x-last.x,y-last.y);
                    points.push({x,y,d:distance});
                }
                previous=[curve[4],curve[5]];
            }
            output.push(points);
        }
        const points=[].concat.apply([],output);
        const xs=points.map(p=>p.x),ys=points.map(p=>p.y),halfStroke=1.05;
        const left=Math.min(...xs)-halfStroke,top=Math.min(...ys)-halfStroke;
        inkBounds=Qt.rect(left,top,Math.max(...xs)+halfStroke-left,Math.max(...ys)+halfStroke-top);
        length=distance;strokes=output;requestPaint();
    }
    Component.onCompleted:trace()
    onProgressChanged:requestPaint()
    onInkChanged:requestPaint()
    onWidthChanged:requestPaint()
    onHeightChanged:requestPaint()
    onPaint:{
        const ctx=getContext("2d");
        ctx.reset();ctx.clearRect(0,0,width,height);
        const fit=Math.min(width/inkBounds.width,height/inkBounds.height);
        ctx.translate((width-inkBounds.width*fit)/2-inkBounds.x*fit,(height-inkBounds.height*fit)/2-inkBounds.y*fit);
        ctx.scale(fit,fit);ctx.strokeStyle=ink;ctx.lineWidth=2.1;ctx.lineCap="round";ctx.lineJoin="round";
        const end=length*Math.max(0,Math.min(1,progress));
        ctx.beginPath();
        for(const points of strokes){
            if(!points.length||points[0].d>=end)break;
            ctx.moveTo(points[0].x,points[0].y);
            for(let i=1;i<points.length;i++){
                const a=points[i-1],b=points[i];
                if(b.d<=end)ctx.lineTo(b.x,b.y);
                else {
                    const t=(end-a.d)/Math.max(.001,b.d-a.d);
                    ctx.lineTo(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t);break;
                }
            }
        }
        ctx.stroke();
    }
}
