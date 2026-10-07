.pragma library
// Retain delegates for surviving entries so filtering can animate their positions.
function reconcile(model, next, key) {
    const wanted = new Set(next.map(row => row[key]));
    for (let i=model.count-1;i>=0;i--) if (!wanted.has(model.get(i)[key])) model.remove(i);
    for (let i=0;i<next.length;i++) {
        let found=-1;
        for(let j=i;j<model.count;j++) if(model.get(j)[key]===next[i][key]){found=j;break;}
        if(found<0)model.insert(i,next[i]);
        else {
            if(found!==i)model.move(found,i,1);
            const current=model.get(i);
            // Streaming changes the last row; leave the rest of the model alone.
            if(Object.keys(next[i]).some(role=>current[role]!==next[i][role]))model.set(i,next[i]);
        }
    }
}
