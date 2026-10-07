.pragma library
function key(date) {return String(date.getFullYear()).padStart(4,'0')+'-'+String(date.getMonth()+1).padStart(2,'0')+'-'+String(date.getDate()).padStart(2,'0');}
function parse(value) {const p=value.split('-').map(Number);const d=new Date(2000,p[1]-1,p[2],12);d.setFullYear(p[0]);return d;}
function add(value,days) {const d=parse(value);d.setDate(d.getDate()+days);return key(d);}
function schedule(entry) {
    const count=Math.max(1,Math.min(entry.count,entry.lead+1));
    const dates=[];
    for(let i=0;i<count;i++)dates.push(add(entry.date,-entry.lead+(count===1?0:Math.round(i*entry.lead/(count-1)))));
    return dates;
}
function timestamp(day,time) {const d=parse(day),p=time.split(':').map(Number);d.setHours(p[0],p[1],0,0);return d.getTime();}

function distance(a,b) {const x=parse(a),y=parse(b);return Math.round((Date.UTC(x.getFullYear(),x.getMonth(),x.getDate())-Date.UTC(y.getFullYear(),y.getMonth(),y.getDate()))/86400000);}
