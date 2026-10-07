const fs=require('fs'),vm=require('vm'),assert=require('assert');
const fuzzy={};vm.createContext(fuzzy);vm.runInContext(fs.readFileSync('services/vendor/fuzzysort.js','utf8').replace(/^\.pragma library\s*/,''),fuzzy);
const apps=[{name:'Visual Studio Code',metadata:'code editor development'},{name:'Thunar File Manager',metadata:'browse files directories'},{name:'Discord',metadata:'chat voice messages'}].map(a=>({...a,nameSearch:fuzzy.prepare(a.name),metadataSearch:fuzzy.prepare(a.metadata)}));
for(const [q,want] of [['vsc','Visual Studio Code'],['dsc','Discord'],['files','Thunar File Manager'],['studio code','Visual Studio Code']]) {
 const result=fuzzy.go(q,apps,{keys:['nameSearch','metadataSearch'],threshold:.15,scoreFn:r=>Math.max(r[0].score,r[1].score*.72)});assert.equal(result[0].obj.name,want,q);
}
const diff={};vm.createContext(diff);vm.runInContext(fs.readFileSync('services/ModelDiff.js','utf8').replace(/^\.pragma library\s*/,''),diff);
let rows=[{id:'a'},{id:'b'},{id:'c'}],removed=[];
const model={get count(){return rows.length},get:i=>rows[i],remove:i=>removed.push(...rows.splice(i,1)),insert:(i,v)=>rows.splice(i,0,v),move:(a,b)=>rows.splice(b,0,...rows.splice(a,1)),set:(i,v)=>Object.assign(rows[i],v)};
const retained=rows[2];diff.reconcile(model,[{id:'c'},{id:'a'},{id:'d'}],'id');assert.deepEqual(rows.map(r=>r.id),['c','a','d']);assert.equal(rows[0],retained);assert.equal(removed.length,1);
console.log('PASS fuzzy abbreviations, metadata, multiword search; filtering retains existing delegates');
