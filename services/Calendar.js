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

function occurs(entry,value) {
    const repeat=entry.repeat||{kind:'none'};
    if(repeat.kind==='none')return entry.date===value;
    if(entry.done||value<entry.date)return false;
    const anchor=entry.startsOn||entry.date,interval=repeat.interval||1;
    if(repeat.kind==='daily')return distance(value,anchor)%interval===0;
    const current=parse(value),start=parse(anchor);
    if(repeat.kind==='weekly'){
        const iso=current.getDay()||7,startIso=start.getDay()||7;
        const weeks=Math.floor((distance(value,anchor)+startIso-1)/7);
        return (repeat.weekdays||[startIso]).includes(iso)&&weeks%interval===0;
    }
    const months=(current.getFullYear()-start.getFullYear())*12+current.getMonth()-start.getMonth();
    const last=new Date(current.getFullYear(),current.getMonth()+1,0).getDate();
    return months%interval===0&&current.getDate()===Math.min(repeat.anchorDay||start.getDate(),last);
}
function repeatLabel(entry) {
    const repeat=entry.repeat||{kind:'none'};
    if(repeat.kind==='none')return '';
    if(repeat.kind==='weekly'&&JSON.stringify(repeat.weekdays)==='[1,2,3,4,5]')return 'Weekdays';
    return repeat.interval>1?'Every '+repeat.interval+' '+({daily:'days',weekly:'weeks',monthly:'months'})[repeat.kind]:({daily:'Daily',weekly:'Weekly',monthly:'Monthly'})[repeat.kind];
}
