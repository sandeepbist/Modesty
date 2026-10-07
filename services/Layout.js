.pragma library
var shapes = {focus:[[1,1],[3,1]],recorder:[[1,1],[3,1]],appearance:[[1,1],[3,1]],awake:[[1,1],[3,1]],wifi:[[3,1],[4,1]],bluetooth:[[3,1],[4,1]],media:[[4,2],[2,2],[3,2]],display:[[7,1],[5,1],[1,2]],sound:[[7,1],[5,1],[1,2]],notifications:[[7,1],[7,2],[7,3],[7,4],[5,2]],peace:[[1,1],[3,1]],nightlight:[[1,1],[3,1]],lock:[[1,1]],power:[[1,1]]};
function defaults() { return [{id:'wifi',x:0,y:0,w:3,h:1},{id:'bluetooth',x:0,y:1,w:3,h:1},{id:'media',x:3,y:0,w:4,h:2},{id:'display',x:0,y:2,w:7,h:1},{id:'sound',x:0,y:3,w:7,h:1},{id:'notifications',x:0,y:4,w:7,h:2},{id:'appearance',x:0,y:6,w:1,h:1},{id:'awake',x:1,y:6,w:1,h:1},{id:'recorder',x:2,y:6,w:1,h:1},{id:'focus',x:3,y:6,w:1,h:1}]; }
function copy(v) { return JSON.parse(JSON.stringify(v)); }
function overlap(a,b) { return a.x < b.x+b.w && a.x+a.w > b.x && a.y < b.y+b.h && a.y+a.h > b.y; }
function validItem(a,columns) { return a && shapes[a.id] && ['x','y','w','h'].every(function(k){return Number.isInteger(a[k]);}) && a.x>=0 && a.y>=0 && a.x+a.w<=columns && a.y+a.h<=12 && a.w>=1 && a.h>=1 && a.h<=6; }
function validate(items,columns) { return Number.isInteger(columns)&&columns>=5&&columns<=9&&Array.isArray(items)&&items.length<=Object.keys(shapes).length&&items.every(function(a,i){return validItem(a,columns)&&items.slice(0,i).every(function(b){return a.id!==b.id&&!overlap(a,b);});}); }
function free(items,item,columns) { return validItem(item,columns)&&!items.some(function(a){return overlap(a,item);}); }
function firstSpace(items,item,columns) { for(var y=0;y<=12-item.h;y++)for(var x=0;x<=columns-item.w;x++){var a=Object.assign({},item,{x:x,y:y});if(free(items,a,columns))return a;}return null; }
function nearest(items,item,columns,preferred) {
    if(preferred){var swap=Object.assign({},item,{x:preferred.x,y:preferred.y});if(free(items,swap,columns))return swap;}
    var best=null,score=Infinity;
    for(var y=0;y<=12-item.h;y++)for(var x=0;x<=columns-item.w;x++){
        var a=Object.assign({},item,{x:x,y:y});
        var distance=Math.abs(x-item.x)+Math.abs(y-item.y)*1.1;
        if(distance<score&&free(items,a,columns)){best=a;score=distance;}
    }
    return best;
}
function place(items,item,columns) {
    if(!validItem(item,columns))return null;
    var original=items.find(function(a){return a.id===item.id;});
    var others=copy(items).filter(function(a){return a.id!==item.id;});
    var displaced=others.filter(function(a){return overlap(a,item);});
    var placed=others.filter(function(a){return !overlap(a,item);}).concat([copy(item)]);
    displaced.sort(function(a,b){return b.w*b.h-a.w*a.h;});
    for(var i=0;i<displaced.length;i++){
        var next=nearest(placed,displaced[i],columns,original);
        if(!next){
            // If fragmented free space cannot fit a neighbor, repack around the
            // selected tile, keeping it exactly where the user placed it.
            placed=[copy(item)];
            others.sort(function(a,b){return b.w*b.h-a.w*a.h;});
            for(var j=0;j<others.length;j++){var fit=nearest(placed,others[j],columns,null);if(!fit)return null;placed.push(fit);}
            break;
        }
        placed.push(next);
    }
    return items.map(function(a){return placed.find(function(b){return a.id===b.id;});}).filter(Boolean).concat(original?[]:[copy(item)]);
}
function tidy(items,columns) { var result=[]; for(var i=0;i<items.length;i++){var a=copy(items[i]);if(a.w>columns){a.w=columns;}a=firstSpace(result,a,columns);if(!a)return null;result.push(a);}return result; }
