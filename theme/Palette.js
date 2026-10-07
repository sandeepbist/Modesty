.pragma library
// Contrast corrections move only as far as necessary, preserving hue.
function rgb(hex) {return [1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);}
function luminance(hex) {return rgb(hex).map(v=>v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);}
function contrast(a,b) {const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
function blend(a,b,t) {const x=rgb(a),y=rgb(b);return "#"+x.map((v,i)=>Math.round((v+(y[i]-v)*t)*255).toString(16).padStart(2,"0")).join("");}
function readable(value,backgrounds,minimum) {
    if(backgrounds.every(b=>contrast(value,b)>=minimum))return value;
    const target=luminance(backgrounds[0])>.35?"#000000":"#ffffff";
    let low=0,high=1;
    for(let i=0;i<12;i++){const mid=(low+high)/2;const c=blend(value,target,mid);if(backgrounds.every(b=>contrast(c,b)>=minimum))high=mid;else low=mid;}
    return blend(value,target,high);
}
function refine(p) {
    const result=Object.assign({},p), backgrounds=[p.bgSolid,p.surfaceSolid];
    for(const key of ["text","subtext"])result[key]=readable(p[key],backgrounds,4.5);
    for(const key of ["accent","green","yellow","red"])result[key]=readable(p[key],backgrounds,3);
    return result;
}
var light={
    everblush:{bg:"#f4f7f5",surface:"#e7eeea",text:"#20312e",subtext:"#506660",accent:"#246d6a",green:"#386b36",yellow:"#7b611c",red:"#a53643"},
    midnight:{bg:"#f5f6fa",surface:"#e9edf5",text:"#242a38",subtext:"#5a6374",accent:"#365f9d",green:"#35683b",yellow:"#7e611f",red:"#aa3856"},
    nord:{bg:"#eceff4",surface:"#e0e5ed",text:"#2e3440",subtext:"#566278",accent:"#386c81",green:"#486f3c",yellow:"#806322",red:"#a13d49"},
    everforest:{bg:"#f5f3e8",surface:"#e9eadc",text:"#36443b",subtext:"#606c59",accent:"#526e38",green:"#4a6b38",yellow:"#826720",red:"#a44743"},
    gruvbox:{bg:"#fbf1c7",surface:"#eee3b9",text:"#3c3836",subtext:"#665c54",accent:"#936000",green:"#626c17",yellow:"#936000",red:"#af3126"},
    rose:{bg:"#faf4ed",surface:"#eee4df",text:"#403b52",subtext:"#71647b",accent:"#9b4560",green:"#376c70",yellow:"#896119",red:"#af3455"},
    dracula:{bg:"#f5f2fa",surface:"#e9e3f3",text:"#302a42",subtext:"#665b76",accent:"#7953a5",green:"#306d42",yellow:"#80651b",red:"#b43c52"}
};
function lightPalette(name) {const p=light[name];return p?refine(Object.assign({},p,{bgSolid:p.bg,surfaceSolid:p.surface})):null;}
