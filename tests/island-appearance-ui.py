#!/usr/bin/env python3
import json
from pathlib import Path
import sys
import tempfile

from PIL import Image
from settings import run, workspace


SOURCE = '''import QtQuick
import QtTest
import Quickshell
import Quickshell.Io
import "modules/island" as Island
import "modules/settings" as Settings
import qs.services
import qs.theme

ShellRoot {
    Settings.SettingsWindow { id: settings }
    FileView {
        id: savedAppearance
        path: Theme.stateDir + "/appearance.json"
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
    }
    FloatingWindow {
        id: window
        visible: true
        implicitWidth: 820
        implicitHeight: 540
        Island.IslandSurface {
            id: island
            anchors.horizontalCenter: parent.horizontalCenter
            y: 30
            availableWidth: parent.width
            availableHeight: parent.height - y
            Keys.onEscapePressed: IslandState.dismissCurrent()
        }
        TestCase { id: input; when: false }
    }
    function check(ok, message) { if (!ok) throw new Error(message); }
    function editor(name) {
        let field;
        input.tryVerify(() => {
            field = input.findChild(window.contentItem, name);
            return !!field?.activeFocus;
        }, 3500, name + " did not take keyboard focus");
        return field;
    }
    function settle() { input.tryVerify(() => !SystemInfo.busy, 5000, "Wallpaper request did not settle"); }
    function stored(palette) {
        input.tryVerify(() => {
            try { return JSON.parse(savedAppearance.text()).paletteName === palette; }
            catch (error) { return false; }
        }, 5000, "Palette was not persisted: " + palette);
    }
    function checkThemeMotion(field) {
        const panel = input.findChild(window.contentItem, "themesPanel");
        const list = input.findChild(panel, "themeList");
        const counter = input.findChild(panel, "themePosition");
        const appliedRow = input.findChild(panel, "themeRow-midnight");
        input.tryVerify(() => {
            const top = appliedRow.mapToItem(list, 0, 0).y;
            return top >= 0 && top + appliedRow.height <= list.height + 1 && appliedRow.height > 60;
        }, 1500, "Themes opened with the applied theme outside the viewport");
        field.text = "ever";
        const first = input.findChild(panel, "themeRow-everblush");
        const second = input.findChild(panel, "themeRow-everforest");
        const from = input.findChild(first, "themeSwatches");
        const to = input.findChild(second, "themeSwatches");
        check(from.x < to.x && first.height > second.height, "Expected expanded and compact starting rows");
        const left = from.x;
        const right = to.x;
        const applied = Theme.paletteName;
        Preferences.motion = "gentle";
        const counterX = counter.x;
        input.keyClick(Qt.Key_Down);
        check(counter instanceof Text && counter.text === "2/2" && counter.x === counterX,
            "Theme position did not update as a stationary label");
        input.tryVerify(() => from.x > left + 12 && from.x < right - 12
                           && to.x > left + 12 && to.x < right - 12, 2000, "Both swatch strips must travel");
        check(first.y < second.y, "Rows changed order while expanding");
        check(input.findChild(first, "themeSwatches") === from && input.findChild(second, "themeSwatches") === to,
              "Focus replaced swatch items");
        input.keyClick(Qt.Key_Up);
        input.tryVerify(() => Math.abs(from.x - left) < 1 && Math.abs(to.x - right) < 1, 2000, "Rapid reversal did not settle");

        input.mouseMove(second, second.width / 2, second.height / 2);
        input.tryVerify(() => panel.diagnostics().selected === 1 && to.x < left + 1, 2000, "Pointer preview did not settle");
        input.wait(130);
        check(panel.diagnostics().selected === 1 && Theme.paletteName === applied,
              "Stationary pointer changed selection or applied a theme");
        Preferences.motion = "instant";
        input.keyClick(Qt.Key_Up);
        input.tryVerify(() => Math.abs(from.x - left) < 1 && Math.abs(to.x - right) < 1, 200,
                        "Instant mode left swatches in flight " + JSON.stringify([from.x, to.x, left, right, panel.diagnostics()]));
        input.mouseMove(window.contentItem, 4, 4);
        field.clear();
        Preferences.motion = "gentle";
        const view = input.findChild(panel, "themeList");
        for (let i = 0; i < panel.diagnostics().count; i++) input.keyClick(Qt.Key_Down);
        const last = input.findChild(panel, "themeRow-rose");
        input.tryVerify(() => {
            const top = last.mapToItem(view, 0, 0).y;
            return top >= 0 && top + last.height <= view.height + 1 && last.height > 60;
        }, 2000, "Keyboard scroll clipped the expanded row");
        check(Theme.paletteName === applied, "Keyboard browsing applied a theme");
        Preferences.motion = "instant";
    }
    function checkWallpaperMotion(carousel, initial) {
        const panel = input.findChild(window.contentItem, "wallpapersPanel");
        const counter = input.findChild(panel, "wallpaperPosition");
        const name = input.findChild(panel, "wallpaperName");
        const startingCard = carousel.currentItem;
        const dot = input.findChild(startingCard, "wallpaperAppliedMarker");
        const nextIndex = (carousel.currentIndex + 1) % carousel.count;
        const farIndex = (carousel.currentIndex + 2) % carousel.count;
        const near = carousel.itemAtIndex(nextIndex);
        const far = carousel.itemAtIndex(farIndex);
        check(dot.visible && startingCard.height - dot.y - dot.height > dot.y && dot.y >= dot.width,
            "Applied wallpaper dot was clipped or too close to the corner");
        check(startingCard.opacity > near.opacity && near.opacity > far.opacity && far.opacity < .5,
            "Carousel lost its center-to-edge fade");
        Preferences.motion = "gentle";
        const counterX = counter.x;
        input.keyClick(Qt.Key_Right);
        check(counter instanceof Text && counter.text === (nextIndex + 1) + "/" + carousel.count && counter.x === counterX,
            "Wallpaper position did not update as a stationary label");
        input.tryVerify(() => name.travel > 0 && name.travel < 1, 1000, "Wallpaper filename did not animate");
        check(dot.visible && !input.findChild(near, "wallpaperAppliedMarker").visible,
            "Applied wallpaper marker moved to a preview");
        input.tryVerify(() => Math.abs(carousel.offset - Math.round(carousel.offset)) > .035, 1500,
            "Wallpaper carousel jumped to the next card");
        check(!SystemInfo.previewWallpaperPath && SystemInfo.wallpaper === initial,
            "Default browsing changed the desktop");
        input.keyClick(Qt.Key_Left);
        input.tryVerify(() => carousel.currentItem?.path === initial &&
            Math.abs(carousel.offset - Math.round(carousel.offset)) < .003, 1500, "Carousel reversal lost the starting image");
        const center = carousel.currentItem;
        const point = center.mapToItem(carousel, center.width / 2, center.height / 2);
        check(Math.abs(point.x - carousel.width / 2) < 1 && center.scale > .99, "Selected wallpaper missed the center");
        Preferences.motion = "instant";
        const index = carousel.currentIndex;
        const x = carousel.width / 2, y = carousel.height / 2;
        input.mouseWheel(carousel, x, y, 0, -30);
        check(carousel.currentIndex === index, "Partial wheel motion skipped a wallpaper");
        input.mouseWheel(carousel, x, y, 0, -90);
        check(carousel.currentIndex === (index + 1) % carousel.count, "Wheel motion did not accumulate");
        input.mouseWheel(carousel, x, y, 120, 0);
        check(carousel.currentIndex === index, "Horizontal wheel reversal missed the current wallpaper");
        Preferences.set("wallpaperLivePreview", true);
    }
    function setting(name) {
        let item;
        input.tryVerify(() => {
            item = input.findChild(settings.contentItem, name);
            return !!item?.visible;
        }, 3000, "Settings control missing " + name);
        return item;
    }
    function clickSetting(name) {
        const item = setting(name);
        check(item.enabled, "Disabled Settings control " + name);
        input.wait(35);
        setting("settings-root").keepVisible(item);
        input.mouseClick(item, item.width / 2, item.height / 2);
    }
    function openThemesSettings() {
        IslandState.closeMenu();
        IslandState.settingsOpen = true;
        setting("settings-root").navigate("appearance", "themes", "new-theme");
    }
    function openThemePicker() {
        IslandState.settingsOpen = false;
        window.contentItem.Window.window.requestActivate();
        IslandState.openMenu("themes");
        return editor("themeSearch");
    }
    function source(value) {
        const choice = setting("custom-theme-source");
        const index = choice.indexOfValue(value);
        clickSetting("custom-theme-source");
        input.tryVerify(() => choice.popup.opened, 1000, "Palette popup did not open");
        const list = choice.popup.contentItem;
        list.positionViewAtIndex(index, ListView.Contain);
        input.tryVerify(() => !!list.itemAtIndex(index), 1000, "Palette option did not load");
        const option = list.itemAtIndex(index);
        input.mouseClick(option, option.width / 2, option.height / 2);
        check(choice.currentValue === value, "Palette source unavailable " + value);
    }
    function checkCustomThemes() {
        openThemesSettings();
        clickSetting("custom-new-theme");
        setting("custom-theme-name").text = "Evening tint";
        source("nord");
        clickSetting("custom-theme-save");
        check(Theme.customThemes.length === 1, "Preset theme was not saved");
        const id = Theme.customThemes[0].id;
        check(Theme.paletteName === "wallpaper", "Saving applied a theme without selection");
        openThemePicker().text = "Evening tint";
        input.keyClick(Qt.Key_Return);
        check(Theme.paletteName === id && Theme.pal.accent === Theme.resolvePalette("nord").accent,
            "Saved preset was not selectable from the island");

        openThemesSettings();
        clickSetting("edit-" + id);
        setting("custom-theme-name").text = "Rose evening";
        source("rose");
        clickSetting("custom-theme-save");
        check(Theme.customThemes.length === 1 && Theme.customThemes[0].id === id
            && Theme.pal.accent === Theme.resolvePalette("rose").accent, "Editing lost the active theme");

        clickSetting("custom-new-theme");
        setting("custom-theme-name").text = "Ocean colors";
        clickSetting("custom-theme-save");
        input.tryVerify(() => {
            const error = input.findChild(settings.contentItem, "custom-theme-error");
            check(!error?.visible, error?.text);
            return Theme.customThemes.some(theme => theme.label === "Ocean colors");
        }, 5000, "Wallpaper theme was not saved");
        const captured = Theme.customThemes.find(theme => theme.label === "Ocean colors");
        check(Theme.validVariants(captured.variants), "Wallpaper capture lacks both modes");

        clickSetting("custom-new-theme");
        setting("custom-theme-name").text = "Ocean expressive";
        source("scheme-expressive");
        clickSetting("custom-theme-preview");
        input.tryVerify(() => setting("custom-theme-preview").text === "Refresh colors", 5000, "Scheme preview was not generated");
        clickSetting("custom-theme-save");
        const generated = Theme.customThemes.find(theme => theme.label === "Ocean expressive");
        check(generated && generated.variants.dark.accent === "#ff8ec3"
            && generated.variants.dark.accent !== captured.variants.dark.accent, "Wrong Matugen scheme captured");
        openThemePicker().text = generated.label;
        input.keyClick(Qt.Key_Return);
        const color = Theme.pal.accent;
        SystemInfo.applyWallpaper(SystemInfo.wallpapers.find(wall => wall.path.endsWith("/Forest.png")).path);
        input.tryVerify(() => SystemInfo.wallpaper.endsWith("/Forest.png"), 5000);
        settle();
        check(Theme.paletteName === generated.id && Theme.pal.accent === color, "Wallpaper change replaced saved colors");
        stored(generated.id);
    }
    function checkRestoredThemes() {
        const generated = Theme.customThemes.find(theme => theme.label === "Ocean expressive");
        check(Theme.customThemes.length === 3 && generated && Theme.paletteName === generated.id
            && generated.variants.dark.accent === "#ff8ec3", "Saved themes or active selection did not survive reload");
        openThemesSettings();
        clickSetting("edit-" + generated.id);
        clickSetting("custom-theme-delete");
        check(Theme.paletteName === generated.id, "Opening confirmation deleted the theme");
        clickSetting("custom-theme-confirm-delete");
        check(Theme.customThemes.length === 2 && Theme.paletteName === "wallpaper", "Deleting active theme missed default fallback");
        clickSetting("use-" + Theme.customThemes[0].id);
        openThemePicker().text = "default";
        input.keyClick(Qt.Key_Return);
        check(Theme.paletteName === "wallpaper" && Preferences.wallpaperColors, "Picker could not restore wallpaper colors");
        stored("wallpaper");
    }
    Timer {
        interval: 120
        running: true
        onTriggered: {
            try {
                input.tryVerify(() => SystemInfo.wallpapers.length >= 4 && SystemInfo.wallpaper.endsWith("/Forest.png"), 5000);
                input.tryVerify(() => Theme.appearanceReady, 5000, "Saved appearance did not load");
                if (Quickshell.env("MODESTY_RESTORE_THEMES") === "1") {
                    checkRestoredThemes();
                    console.log("ISLAND THEME RELOAD PASS");
                    Qt.quit();
                    return;
                }
                const initial = SystemInfo.wallpaper;
                IslandState.openMenu("wallpapers");
                const walls = editor("wallpaperSearch");
                const carousel = input.findChild(window.contentItem, "wallpaperCarousel");
                checkWallpaperMotion(carousel, initial);
                input.keyClick(Qt.Key_Right);
                input.tryVerify(() => SystemInfo.previewWallpaperPath.endsWith("/Ocean.png"));
                input.keyClick(Qt.Key_Left);
                input.tryVerify(() => !SystemInfo.previewWallpaperPath);
                walls.text = "absent wallpaper";
                input.tryVerify(() => carousel.count === 0);
                input.keyClick(Qt.Key_Return);
                check(SystemInfo.wallpaper === initial, "Empty wallpaper search applied a result");
                walls.text = "ocean";
                input.tryVerify(() => SystemInfo.previewWallpaperPath.endsWith("/Ocean.png"));
                check(SystemInfo.wallpaper === initial, "Wallpaper browse changed saved selection");
                input.keyClick(Qt.Key_Escape);
                check(!SystemInfo.previewWallpaperPath, "Wallpaper preview survived dismissal");

                IslandState.openMenu("themes");
                const themes = editor("themeSearch");
                checkThemeMotion(themes);
                themes.text = "dracula";
                input.keyClick(Qt.Key_Return);
                check(Theme.paletteName === "dracula" && SystemInfo.wallpaper === initial, "Palette-only selection changed wallpaper");
                stored("dracula");
                themes.text = "earth at night";
                input.keyClick(Qt.Key_Return);
                input.tryVerify(() => SystemInfo.error === "Fixture rejected the wallpaper");
                settle();
                check(Theme.paletteName === "dracula" && SystemInfo.wallpaper === initial, "Failed theme changed applied state");
                themes.text = "blue marble";
                input.keyClick(Qt.Key_Return);
                input.tryVerify(() => SystemInfo.wallpaper.endsWith("nasa-blue-marble.jpg") && Theme.paletteName === "nord", 5000);
                settle();
                stored("nord");

                Preferences.motion = "gentle";
                IslandState.openMenu("wallpapers");
                input.tryVerify(() => {
                    const panes = island.clockStage.diagnostics().entries;
                    return panes.find(pane => pane.name === "themes").opacity > .03 &&
                        panes.find(pane => pane.name === "wallpapers").opacity > .03;
                }, 1000, "Theme and wallpaper picker switch left a blank interval");
                const reopened = editor("wallpaperSearch");
                Preferences.motion = "instant";
                reopened.text = "ocean";
                input.tryVerify(() => SystemInfo.previewWallpaperPath.endsWith("/Ocean.png"));
                const card = input.findChild(window.contentItem, "wallpaperCarousel").currentItem;
                input.mouseClick(card, card.width / 2, card.height / 2);
                input.tryVerify(() => SystemInfo.wallpaper.endsWith("/Ocean.png") && Theme.paletteName === "wallpaper", 5000);
                settle();
                check(!SystemInfo.previewWallpaperPath, "Applied wallpaper remained a preview");
                stored("wallpaper");
                checkCustomThemes();
                console.log("ISLAND APPEARANCE PASS");
                Qt.quit();
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
'''

with tempfile.TemporaryDirectory(prefix='modesty-island-appearance-') as temporary:
    root = Path(temporary)
    environment = workspace(root, preview=False)
    walls = root / 'wallpapers'
    walls.mkdir()
    for name, color in [('Forest', '#3c604a'), ('Ocean', '#2d6087'), ('Summit', '#73586b'), ('Twilight', '#3b364d')]:
        Image.new('RGB', (320, 200), color).save(walls / (name + '.png'))
    environment['MODESTY_WALLPAPERS'] = str(walls)
    settings = root / 'state/modesty'
    settings.mkdir()
    (settings / 'wallpaper.json').write_text(json.dumps({'path': str(walls / 'Forest.png'), 'backend': 'native'}))
    (settings / 'appearance.json').write_text(json.dumps({'paletteName': 'midnight', 'mode': 'dark'}))
    (settings / 'preferences.json').write_text(json.dumps({
        'motion': 'instant', 'wallpaperColors': True, 'themeGtk': False, 'themeQt': False,
        'themeFoot': False, 'themeFolders': False, 'themeSpotify': False,
    }))
    python = root / 'bin/python3'
    python.write_text('#!' + sys.executable + '\n' + '''import json, runpy, sys
from pathlib import Path
if sys.argv[1].endswith(('/system.py', '/appearance.py')):
    if sys.argv[1].endswith('/system.py') and sys.argv[2] == 'wallpaper':
        if json.loads(sys.argv[3])['path'].endswith('nasa-earth-at-night.png'):
            print(json.dumps(dict(ok=False, error='Fixture rejected the wallpaper')))
            sys.exit(1)
    sys.argv = sys.argv[1:]
    sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent))
    runpy.run_path(sys.argv[0], run_name='__main__')
else:
    print(json.dumps(dict(ok=True, desktopBindings=[], items=[])))
''')
    palette = Path(__file__).resolve().parents[1] / 'setup/state/modesty/wallpaper-data.json'
    matugen = root / 'bin/matugen'
    matugen.unlink()
    matugen.write_text('#!' + sys.executable + '\n' + f'''from pathlib import Path
import json, sys
data = json.loads(Path({str(palette)!r}).read_text())
if 'scheme-expressive' in sys.argv:
    data['colors']['primary']['dark']['color'] = '#ff8ec3'
print(json.dumps(data))
''')
    matugen.chmod(0o755)
    run(root, environment, SOURCE, 'ISLAND APPEARANCE PASS')
    assert json.loads((settings / 'wallpaper.json').read_text())['path'] == str(walls / 'Forest.png')
    run(root, dict(environment, MODESTY_RESTORE_THEMES='1'), SOURCE, 'ISLAND THEME RELOAD PASS')
    appearance = json.loads((settings / 'appearance.json').read_text())
    assert appearance['paletteName'] == 'wallpaper'
    assert [theme['label'] for theme in appearance['customThemes']] == ['Rose evening', 'Ocean colors']
