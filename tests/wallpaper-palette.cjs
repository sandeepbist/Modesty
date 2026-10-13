#!/usr/bin/env node
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../services/SystemInfo.qml'), 'utf8');

function method(text, name) {
    const match = text.match(new RegExp('    function ' + name + '\\(([^\\n]*)\\)\\s*:\\s*\\w+ \\{([\\s\\S]*?)\\n    \\}'));
    assert(match, 'extract actual ' + name + ' body');
    return 'function ' + name + '(' + match[1].replace(/:\s*\w+/g, '') + '){' + match[2] + '\n}';
}

const full = {
    colors: {primary: {dark: {color: '#102030'}, light: {color: '#e0d0c0'}}},
    modesty: {automatic: false, scheme: 'scheme-fidelity', contrast: .25, sourceIndex: 2, sample: 'preview'},
    unknown: {unicode: '森 雪 café 🙂', nested: [null, true, 2.5, {x: 'a\\b\n"c"'}]},
    future: [{retained: {key: '値'}}]
};
const palette = {dark: {accent: '#102030'}, light: {accent: '#e0d0c0'}};
const plain = value => JSON.parse(JSON.stringify(value));

function load() {
    const calls = [];
    const json = Object.create(JSON);
    let parses = 0;
    json.parse = function (...args) { parses++; return JSON.parse(...args); };
    const context = {
        JSON: json,
        preview: false,
        wallpaper: '/wall/雪.png',
        wallpapers: [{path: '/wall/雪.png', displayUrl: 'file:///wall/display.png'}],
        matugenAvailable: true,
        Preferences: {wallpaperColors: true, matugenAutomatic: false, matugenScheme: 'scheme-fidelity', matugenContrast: .25, matugenSource: 2},
        previewPaletteCache: {},
        paletteKey: '',
        pendingPalette: null,
        wallpaperWarning: '',
        paletteProc: {running: false},
        paletteDelay: {stops: 0, restarts: 0, stop() { this.stops++; }, restart() { this.restarts++; }},
        wallProc: {running: false, command: []},
        script: path.join(__dirname, '../scripts/system.py'),
        Theme: {
            wallpaperData: null,
            wallpaperVariants: null,
            installWallpaperData(palette, raw) {
                calls.push({method: 'installWallpaperData', palette, raw});
                this.wallpaperData = raw;
                this.wallpaperVariants = palette;
            },
            setPalette(...args) { calls.push({method: 'setPalette', args}); },
            showWallpaperPreview(...args) { calls.push({method: 'showWallpaperPreview', args}); },
            clearWallpaperPreview(...args) { calls.push({method: 'clearWallpaperPreview', args}); }
        }
    };
    context.root = context;
    vm.createContext(context);
    vm.runInContext(['storePalette', 'paletteRequest', 'recolor', 'scanWallpapers'].map(name => method(source, name)).join('\n'), context);
    return {context, calls, parses: () => parses};
}

function selectedKey(context) {
    return JSON.stringify(context.paletteRequest(context.wallpaper));
}

const selected = load();
const context = selected.context;
context.scanWallpapers();
assert.equal(context.wallProc.running, true);
assert.deepEqual(JSON.parse(context.wallProc.command[3]), {
    automatic: false, scheme: 'scheme-fidelity', contrast: .25, source: 2, paletteDataFormat: 'json'
});
assert(!selectedKey(context).includes('paletteDataFormat'), 'transport format is absent from palette keys');
const key = selectedKey(context);
context.storePalette({key: 'before', palette, raw: {retained: true}});
context.storePalette({key, palette, raw: JSON.stringify(full)});
context.storePalette({key: 'after', palette, raw: {retained: true}});
const cache = context.previewPaletteCache;
const entry = cache[key];
const order = Object.keys(cache);
const before = cache.before;
const after = cache.after;
context.pendingPalette = {old: 'request'};
context.wallpaperWarning = "Couldn't generate wallpaper colors";
context.recolor();
assert.equal(selected.parses(), 1, 'selected string parses once');
assert.equal(selected.calls.length, 1);
assert.equal(selected.calls[0].method, 'installWallpaperData');
assert.equal(selected.calls[0].palette, palette, 'selected palette retains identity');
assert.deepEqual(plain(selected.calls[0].raw), full, 'Theme receives full raw metadata');
assert.equal(typeof selected.calls[0].raw, 'object');
assert.equal(selected.calls[0].raw, entry.raw, 'Theme receives the cached decoded object');
assert.equal(context.previewPaletteCache, cache, 'decode does not replace the cache');
assert.equal(cache[key], entry, 'decode does not replace the cache entry');
assert.equal(cache.before, before);
assert.equal(cache.after, after);
assert.deepEqual(Object.keys(cache), order, 'decode does not change recency');
assert.equal(entry.palette, palette);
assert.equal(context.pendingPalette, null);
assert.equal(context.paletteDelay.restarts, 0, 'cached decode does not fetch');
assert.equal(context.wallpaperWarning, "Couldn't generate wallpaper colors", 'cached install preserves unrelated warnings');
context.recolor();
assert.equal(selected.parses(), 1, 'repeat recolor does not parse again');
assert.equal(selected.calls.length, 1, 'repeat decoded identity does not install again');
assert.equal(context.Theme.wallpaperData, entry.raw);
assert.equal(context.wallpaperWarning, "Couldn't generate wallpaper colors", 'cached identity reuse preserves unrelated warnings');

for (const processName of ['paletteProc', 'previewProc']) {
    const legacy = load();
    const raw = plain(full);
    legacy.context.storePalette({key: selectedKey(legacy.context), palette, raw});
    legacy.context.recolor();
    assert.equal(legacy.parses(), 0, processName + ' legacy object needs no parse');
    assert.equal(legacy.calls.length, 1);
    assert.equal(legacy.calls[0].raw, raw, processName + ' legacy object retains identity');
    assert.equal(legacy.calls[0].palette, palette);
}

for (const raw of ['{broken', '[]', '[{"kept":true}]', 'null', '42', 'true', '"text"']) {
    const invalid = load();
    const oldData = {preserve: 'wallpaper'};
    const oldPalette = {preserve: 'colors'};
    invalid.context.Theme.wallpaperData = oldData;
    invalid.context.Theme.wallpaperVariants = oldPalette;
    const key = selectedKey(invalid.context);
    invalid.context.storePalette({key, palette, raw});
    const cache = invalid.context.previewPaletteCache;
    const entry = cache[key];
    invalid.context.recolor();
    assert.equal(invalid.parses(), 1);
    assert.equal(invalid.context.wallpaperWarning, "Couldn't read wallpaper colors");
    assert.equal(invalid.calls.length, 0, raw + ' must not change Theme');
    assert.equal(invalid.context.Theme.wallpaperData, oldData);
    assert.equal(invalid.context.Theme.wallpaperVariants, oldPalette);
    assert.equal(invalid.context.previewPaletteCache, cache);
    assert.equal(cache[key], entry);
    assert.equal(entry.raw, raw, 'failed decode retains original raw string');
    assert.equal(entry.palette, palette);
    assert.equal(invalid.context.paletteDelay.restarts, 0);
}

for (const raw of [JSON.stringify(full), plain(full)]) {
    const recovery = load();
    const context = recovery.context;
    const key = selectedKey(context);
    context.storePalette({key, palette, raw: '{broken'});
    context.recolor();
    assert.equal(context.wallpaperWarning, "Couldn't read wallpaper colors");
    assert.equal(recovery.calls.length, 0);
    context.storePalette({key, palette, raw});
    context.recolor();
    assert.deepEqual(plain(context.Theme.wallpaperData), full, 'valid string or legacy object restores full Theme data');
    assert.equal(context.Theme.wallpaperData, context.previewPaletteCache[key].raw);
    assert.equal(context.Theme.wallpaperVariants, palette);
    assert.equal(context.wallpaperWarning, '', 'valid cached install clears the earlier read warning');
    assert.equal(recovery.calls.length, 1);
    assert.equal(recovery.parses(), typeof raw === 'string' ? 2 : 1);
    context.wallpaperWarning = "Couldn't read wallpaper colors";
    context.recolor();
    assert.equal(context.wallpaperWarning, '', 'cached identity reuse also clears the read warning');
    assert.equal(recovery.calls.length, 1, 'recovery retains installed identity');
    assert.equal(recovery.parses(), typeof raw === 'string' ? 2 : 1, 'recovery does not parse again');
    assert.equal(context.paletteDelay.restarts, 0, 'recovery does not fetch');
}

const lru = load();
for (let index = 0; index < 32; index++) lru.context.storePalette({key: 'entry-' + index, palette, raw: {index}});
assert.deepEqual(Object.keys(lru.context.previewPaletteCache), Array.from({length: 32}, (_, index) => 'entry-' + index));
lru.context.storePalette({key: 'entry-0', palette, raw: {index: 'refreshed'}});
assert.deepEqual(Object.keys(lru.context.previewPaletteCache), Array.from({length: 31}, (_, index) => 'entry-' + (index + 1)).concat('entry-0'), 'ingestion refreshes existing key recency');
lru.context.storePalette({key: 'entry-32', palette, raw: {index: 32}});
assert.equal(Object.keys(lru.context.previewPaletteCache).length, 32, '33rd entry preserves 32-entry bound');
assert.equal(lru.context.previewPaletteCache['entry-1'], undefined, 'least recent entry is evicted');
assert.equal(lru.context.previewPaletteCache['entry-0'].raw.index, 'refreshed');
assert.deepEqual(Object.keys(lru.context.previewPaletteCache), Array.from({length: 30}, (_, index) => 'entry-' + (index + 2)).concat('entry-0', 'entry-32'));

const changes = load();
const changedKey = selectedKey(changes.context);
changes.context.storePalette({key: changedKey, palette, raw: JSON.stringify(full)});
changes.context.recolor();
for (const mode of ['dark', 'light']) {
    const changedPalette = plain(palette);
    changedPalette[mode].accent = '#345678';
    const changedRaw = plain(full);
    changedRaw.colors.primary[mode].color = '#345678';
    changedRaw.modesty.revision = mode;
    changes.context.storePalette({key: changedKey, palette: changedPalette, raw: JSON.stringify(changedRaw)});
    changes.context.recolor();
    assert.equal(changes.calls.at(-1).palette, changedPalette, 'changed ' + mode + ' palette is installed');
    assert.deepEqual(plain(changes.calls.at(-1).raw), changedRaw);
}
assert.equal(changes.calls.length, 3, 'real dark and light palette changes are not suppressed');
assert.equal(changes.parses(), 3);

console.log('PASS wallpaper palette: actual methods, JSON scan option, parse once and identity reuse, full metadata, legacy objects, malformed and nonobject rejection without Theme changes, valid string and legacy object recovery, selective warning clearing, cache order and 33-entry eviction, real dark/light palette changes');
