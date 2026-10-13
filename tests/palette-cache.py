#!/usr/bin/env python3
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
subprocess.run(['node', '-e', r'''
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const root=process.argv[1];
const source=fs.readFileSync(root+'/theme/Palette.js','utf8').replace('.pragma library','');
function load(){const context={};vm.createContext(context);vm.runInContext(source,context);return context;}
const palette=load(),readable=palette.readable,blend=palette.blend;
function uncached(p){
    const result=Object.assign({},p),backgrounds=[p.bgSolid,p.surfaceSolid];
    for(const key of ['accent','green','yellow','red'])result[key]=readable(p[key],backgrounds,3);
    const textBackgrounds=backgrounds.concat(backgrounds.map(b=>blend(b,result.accent,.18)));
    for(const key of ['text','subtext'])result[key]=readable(p[key],textBackgrounds,4.5);
    result.accentText=readable(p.accentText||p.bgSolid,[result.accent],4.5);
    return result;
}
function equal(actual,expected,label){assert.equal(JSON.stringify(actual),JSON.stringify(expected),label);}
function check(p,label){
    const original=JSON.stringify(p),expected=uncached(p);
    const first=palette.refine(p),second=palette.refine(Object.assign({},p));
    equal(first,expected,label+' first result');equal(second,expected,label+' repeated result');
    assert.notEqual(first,second,label+' fresh result');
    first.accent='#010101';first.bgSolid='#020202';first.extra='caller mutation';
    equal(palette.refine(p),expected,label+' result mutation isolation');
    assert.equal(JSON.stringify(p),original,label+' input remains unchanged');
}
const themeSource=fs.readFileSync(root+'/theme/Theme.qml','utf8');
const theme={Palette:palette,mode:'dark',paletteName:'everblush',wallpaperVariants:{},previewWallpaperVariants:null,previewSyncPending:false,restoringPreview:false};
theme.root=theme;Object.defineProperty(theme,'light',{get(){return this.mode==='light';}});vm.createContext(theme);
theme.wallpaperPalette=vm.runInContext('('+themeSource.match(/property var wallpaperPalette: \((\{[^\n]+\})\)/)[1]+')',theme);
theme.palettes=vm.runInContext('('+themeSource.match(/readonly property var palettes: (\{[\s\S]*?\n    \})\n\n    \/\/ ---- Resolved colors/)[1]+')',theme);
const resolveBody=themeSource.match(/function resolvePalette\(name\): var \{([\s\S]*?)\n    \}/)[1];
const palExpression=themeSource.match(/readonly property var pal: ([^\n]+)/)[1];
vm.runInContext('function resolvePalette(name){'+resolveBody+'}\nfunction currentPalette(){return '+palExpression+';}',theme);
const validBody=themeSource.match(/function validPalette\(p\): bool \{([\s\S]*?)\n    \}/)[1];
const previewBody=themeSource.match(/function showWallpaperPreview\(palette\):void \{([\s\S]*?)\}(?=\n    function clearWallpaperPreview)/)[1];
const clearBody=themeSource.match(/function clearWallpaperPreview\(\):void \{([\s\S]*?)\n    \}/)[1];
theme.Qt={callLater(callback){callback();}};
vm.runInContext('function validPalette(p){'+validBody+'}\nfunction showWallpaperPreview(palette){'+previewBody+'}\nfunction clearWallpaperPreview(){'+clearBody+'}',theme);
function resolvedInput(name){
    const base=theme.palettes[name]??theme.palettes.everblush;
    if(name==='wallpaper'&&theme.wallpaperVariants[theme.mode])return theme.wallpaperVariants[theme.mode];
    const light=palette.light[name];
    return theme.light&&name!=='e-ink'&&light?Object.assign({},light,{bgSolid:light.bg,surfaceSolid:light.surface}):base;
}
for(const mode of ['dark','light','dark']){
    theme.mode=mode;
    for(const name of Object.keys(theme.palettes).concat('unknown')){
        const input=resolvedInput(name);check(input,name+' '+mode);
        const actual=theme.resolvePalette(name);equal(actual,uncached(input),name+' '+mode+' resolution');
        const backgrounds=[input.bgSolid,input.surfaceSolid];
        for(const key of ['accent','green','yellow','red'])
            assert(backgrounds.every(b=>palette.contrast(actual[key],b)>=3),name+' '+mode+' '+key+' contrast');
        const tinted=backgrounds.concat(backgrounds.map(b=>blend(b,actual.accent,.18)));
        for(const key of ['text','subtext'])
            assert(tinted.every(b=>palette.contrast(actual[key],b)>=4.5),name+' '+mode+' '+key+' contrast');
        assert(palette.contrast(actual.accentText,actual.accent)>=4.5,name+' '+mode+' accent text contrast');
    }
}
const variants=JSON.parse(fs.readFileSync(root+'/setup/state/modesty/wallpaper-palette.json','utf8'));
theme.paletteName='wallpaper';theme.wallpaperVariants=variants;
for(const mode of ['dark','light','dark']){
    theme.mode=mode;equal(theme.currentPalette(),uncached(variants[mode]),'wallpaper '+mode);
    const preview={dark:Object.assign({},variants.dark,{accent:'#a4d4c4'}),light:Object.assign({},variants.light,{accent:'#315e45'})};
    theme.previewWallpaperVariants=preview;
    equal(theme.currentPalette(),uncached(preview[mode]),'preview '+mode);
    variants[mode]=Object.assign({},variants[mode],{secondary:'#446688',tertiary:'#665544'});
    equal(theme.currentPalette(),uncached(preview[mode]),'preview during wallpaper revision '+mode);
    theme.previewWallpaperVariants=null;
    equal(theme.currentPalette(),uncached(variants[mode]),'preview restore '+mode);
}
const copy=value=>JSON.parse(JSON.stringify(value)),preview=copy(variants);
theme.showWallpaperPreview(preview);
assert.equal(theme.previewWallpaperVariants,preview,'first preview installs incoming palette');
theme.showWallpaperPreview(copy(preview));
assert.equal(theme.previewWallpaperVariants,preview,'equal deep copy retains preview reference');
const reorderedPreview=Object.fromEntries(Object.entries(preview).reverse().map(([mode,colors])=>[mode,Object.fromEntries(Object.entries(colors).reverse())]));
theme.showWallpaperPreview(reorderedPreview);
assert.equal(theme.previewWallpaperVariants,preview,'equal reordered own keys retain preview reference');
for(const mode of ['dark','light']){
    const changed=copy(theme.previewWallpaperVariants);
    changed[mode].accent=changed[mode].accent==='#010203'?'#040506':'#010203';
    theme.showWallpaperPreview(changed);
    assert.equal(theme.previewWallpaperVariants,changed,'changed '+mode+' installs incoming palette');
    for(const key of ['accentText','secondary','tertiary']){
        const removed=copy(theme.previewWallpaperVariants);delete removed[mode][key];
        theme.showWallpaperPreview(removed);
        assert.equal(theme.previewWallpaperVariants,removed,'removed '+mode+' '+key+' updates preview');
        const added=copy(removed);added[mode][key]='#123456';
        theme.showWallpaperPreview(added);
        assert.equal(theme.previewWallpaperVariants,added,'added '+mode+' '+key+' updates preview');
        const revised=copy(added);revised[mode][key]='#654321';
        theme.showWallpaperPreview(revised);
        assert.equal(theme.previewWallpaperVariants,revised,'changed '+mode+' '+key+' updates preview');
    }
}
const retainedPreview=theme.previewWallpaperVariants;
for(const mode of ['dark','light']){
    const invalid=copy(retainedPreview);invalid[mode].accent='invalid';
    theme.showWallpaperPreview(invalid);
    assert.equal(theme.previewWallpaperVariants,retainedPreview,'invalid '+mode+' ignores preview');
}
theme.paletteName='everblush';theme.showWallpaperPreview(copy(variants));theme.showWallpaperPreview(null);
assert.equal(theme.previewWallpaperVariants,retainedPreview,'non-wallpaper ignores preview');
theme.paletteName='wallpaper';theme.clearWallpaperPreview();
assert.equal(theme.previewWallpaperVariants,null,'clear preview removes palette');
const reopened=copy(retainedPreview);theme.showWallpaperPreview(reopened);
assert.equal(theme.previewWallpaperVariants,reopened,'reopen installs equal palette after clear');
theme.clearWallpaperPreview();
const revision=Object.assign({},variants.dark);
for(const key of Object.keys(revision)){
    check(revision,'wallpaper before '+key);revision[key]='#405060';check(revision,'wallpaper changed '+key);
}
const metadata=Object.assign({},variants.dark,{extra:{label:'one'},optional:undefined});
const firstMetadata=palette.refine(metadata);
const secondMetadata=palette.refine(Object.assign({},metadata,{extra:{label:'one'},optional:null}));
assert.equal(firstMetadata.optional,undefined);assert.equal(secondMetadata.optional,null);
assert.notEqual(firstMetadata.extra,secondMetadata.extra,'return current ancillary input object');
const cache=load();let corrections=0;const originalReadable=cache.readable;
cache.readable=function(...args){corrections++;return originalReadable(...args);};
const input=Object.assign({},variants.dark,{revision:0});
cache.refine(input);assert.equal(corrections,7,'first input requires seven contrast corrections');
const reordered=Object.fromEntries(Object.entries(input).reverse());
cache.refine(reordered);assert.equal(corrections,7,'same content and different key order use cache');
for(let revision=1;revision<=32;revision++)cache.refine(Object.assign({},input,{revision}));
assert.equal(corrections,33*7,'each revision recomputes corrections');
assert.equal(cache.refineCache.length,32,'retain at most 32 palettes');
cache.refine(Object.assign({},input,{revision:32}));assert.equal(corrections,33*7,'latest revision remains cached');
equal(cache.refine(input),uncached(input),'evicted result exact');
assert.equal(corrections,34*7,'oldest palette evicted at cache bound');
assert.equal(cache.refineCache.length,32,'cache remains bounded after eviction');
console.log('PASS palette cache: all builtins dark/light, exact colors and contrast, wallpaper revisions, preview dedupe/change/clear/reopen, fresh results, 32-entry bound');
''', str(ROOT)], check=True)
