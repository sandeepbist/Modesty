const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const grid={};vm.createContext(grid);vm.runInContext(fs.readFileSync('services/Layout.js','utf8').replace('.pragma library',''),grid);
const original=grid.defaults();assert(grid.validate(original,7));
const displaced=grid.place(original,{id:'wifi',x:3,y:0,w:3,h:1},7);
assert(displaced&&grid.validate(displaced,7),'Resolve overlap by moving neighboring tiles');
assert.equal(displaced.length,original.length,'Collision resolution must retain every control');
assert.equal(JSON.stringify(displaced.find(a=>a.id==='wifi')),JSON.stringify({id:'wifi',x:3,y:0,w:3,h:1}),'Keep the selected tile at the requested position');
assert.equal(grid.place(original,{id:'wifi',x:-1,y:0,w:3,h:1},7),null);
assert(grid.validate(grid.place(original,{id:'wifi',x:0,y:0,w:3,h:2},7),7),'Allow sizes supported by the editor sliders');
assert.equal(grid.place(original,{id:'wifi',x:0,y:0,w:3,h:7},7),null,'Reject height outside editor bounds');
assert.equal(grid.place(original,{id:'unknown',x:0,y:0,w:1,h:1},7),null,'Reject unknown controls');
assert.equal(grid.validate(original.concat([original[0]]),7),false,'Reject duplicate controls');
for(const columns of [5,6,7,8,9]){
 const tidy=grid.tidy(original,columns);assert(grid.validate(tidy,columns));assert.equal(tidy.length,original.length);
 let full=tidy;for(const id of ['peace','nightlight','lock','power']){const s=grid.shapes[id][0];const item=grid.firstSpace(full,{id,w:s[0],h:s[1]},columns);assert(item);full=full.concat([item]);assert(grid.validate(full,columns));}
 for(let y=-1;y<13;y++)for(let x=-1;x<columns+1;x++){
  const moved=grid.place(full,{id:'wifi',x,y,w:3,h:1},columns);if(moved)assert(grid.validate(moved,columns));
 }
}
assert.equal(JSON.stringify(original),JSON.stringify(grid.defaults()),'Layout operations must not mutate saved history');
console.log('PASS layout: collision displacement, bounds, resizing, all five grid widths, additions, history immutability');
