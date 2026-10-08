const fs=require('fs'),vm=require('vm'),assert=require('assert');
const palette={};vm.createContext(palette);
vm.runInContext(fs.readFileSync('theme/Palette.js','utf8').replace(/^\.pragma library\s*/,''),palette);
const accents=['#c7c7c7','#bdc7dd','#e5b4ff','#67b7b5','#f5dc48','#ea5545','#505050'];
for(const mode of ['dark','light'])for(const accent of accents){
    const background=mode==='dark'?'#101013':'#f5f6fa',surface=mode==='dark'?'#18181c':'#e9edf5';
    const source={bg:background,bgSolid:background,surface:surface,surfaceSolid:surface,
        text:mode==='dark'?'#898989':'#777777',subtext:'#888888',accent,green:accent,yellow:accent,red:accent};
    const refined=palette.refine(source);
    for(const base of [background,surface,palette.blend(background,refined.accent,.18),palette.blend(surface,refined.accent,.18)])
        for(const role of ['text','subtext'])assert(palette.contrast(refined[role],base)>=4.5,`${mode}/${accent}/${role}`);
    assert(palette.contrast(refined.accentText,refined.accent)>=4.5,`${mode}/${accent}/accent text`);
    const twice=palette.refine(refined);
    assert.equal(JSON.stringify(twice),JSON.stringify(refined),'Refinement must settle, not drift on repeated palette updates');
}
const sources=process.argv[2]?JSON.parse(fs.readFileSync(process.argv[2],'utf8')):[];
for(const {label,colors} of sources){
    const p=palette.refine(colors);
    for(const base of [p.bgSolid,p.surfaceSolid,palette.blend(p.bgSolid,p.accent,.18),palette.blend(p.surfaceSolid,p.accent,.18)])
        for(const role of ['text','subtext'])assert(palette.contrast(p[role],base)>=4.5,`${label}/${role}`);
    assert(palette.contrast(p.accentText,p.accent)>=4.5,`${label}/accent text`);
}
for(const name of Object.keys(palette.light)){
    const p=palette.lightPalette(name);
    assert(palette.contrast(p.text,p.bgSolid)>=4.5&&palette.contrast(p.accentText,p.accent)>=4.5,name);
}
if(sources.length)console.log(`PASS ${sources.length} actual Matugen wallpaper palette variants`);
console.log('PASS palette contrast on neutral/saturated dark/light surfaces, selection tints, accent labels and stable refinement');
