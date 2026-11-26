#!/usr/bin/env python3
"""Exercise both lock layouts without locking the desktop or starting PAM."""
from pathlib import Path
import tempfile
from unittest.mock import patch

import qml


SESSION = '''pragma Singleton
import Quickshell
Singleton {
    property bool locked: true
    property bool authenticating: false
    property bool unlocking: false
    property bool responseVisible: false
    property string prompt: "Password"
    property string error: ""
    property string wallpaperSource: ""
    property int wallpaperDecodeWidth: 1920
    property int submissions: 0
    function submit(response: string): void {
        if (response.length) { submissions++; error = ""; authenticating = true; }
    }
}
'''

SCENE = '''import QtQuick
import QtTest
import Quickshell
import "modules/lock" as Lock
import qs.services
import qs.theme
import qs.components

ShellRoot {
    id: fixture
    property bool loaded: true
    property bool preview: false
    property bool narrow: false
    FloatingWindow {
        id: window
        visible: true
        implicitWidth: 960
        implicitHeight: 540
        Loader {
            id: screen
            width: fixture.narrow ? 330 : parent.width
            height: fixture.narrow ? 270 : parent.height
            active: fixture.loaded
            sourceComponent: Lock.LockContent { preview: fixture.preview }
        }
    }
    TestCase { id: input; when: false }
    function child(name) { return input.findChild(screen.item, name); }
    function check(ok, message) { if (!ok) throw new Error(message); }
    function center(item) { return item.mapToItem(screen.item, item.width / 2, item.height / 2); }
    function typeKey(field, key) { field.forceActiveFocus(); input.keyClick(key); }
    function waitFor(condition, message) {
        const deadline = Date.now() + 1800;
        while (!condition() && Date.now() < deadline) input.wait(10);
        check(condition(), message);
    }
    Timer {
        interval: 150; running: true
        onTriggered: { try {
            check(Preferences.lockScreenStyle === "legacy" && !child("modernLockClock"), "Legacy default missing");
            const legacyField = child("lockPassword");
            check(center(legacyField).y > screen.height * .55, "Legacy field moved");
            Session.authenticating = true;
            const legacyPrompt = legacyField.children.find(item => item instanceof PanelText);
            check(!legacyField.enabled && legacyPrompt?.text === "", "Legacy verification drew a message");
            Session.authenticating = false;
            Preferences.set("lockScreenStyle", "invalid");
            check(Preferences.lockScreenStyle === "legacy", "Invalid style accepted");

            fixture.loaded = false;
            Preferences.set("lockScreenStyle", "modern");
            Preferences.set("modernLockDuration", 360);
            fixture.loaded = true;
            const clock = child("modernLockClock"), capsule = child("modernLockCapsule"), field = child("lockPassword");
            check(clock && capsule && field && field.echoMode === TextInput.Password, "Modern view missing masked input");
            check(center(clock).y < screen.height * .25 && clock.scale < .25, "Clock did not start at the pill");
            waitFor(() => screen.item.arrival > .04 && screen.item.arrival < .96, "Clock arrival has no intermediate frame");
            check(center(clock).y > 20 && center(clock).y < screen.height * .5, "Clock does not travel toward center");
            waitFor(() => clock.scale === 1, "Clock did not settle");
            check(Math.abs(center(clock).y - screen.height * .493) < .6 && center(field).y < screen.height * .15,
                "Modern content missed its anchors");
            const digitRow = clock.children.find(item => item instanceof Row);
            clock.text = "88:48";
            check(clock.font.letterSpacing === 0 && digitRow.spacing < 0 && clock.width === digitRow.implicitWidth,
                "Clock tracking narrowed the digit clips or the frost texture");
            check(Tokens.lockTransitionDuration === Math.round(360 / Preferences.motionSpeed), "Modern transition duration mismatch");
            check(screen.item.clockDockedAt - Tokens.lockReturnLead === Tokens.lockTransitionDuration,
                "Entry and exit do not budget the same time for clock travel");
            check(Tokens.lockDepartureDuration > Tokens.lockTransitionDuration, "Modern unlock should have more time to settle");
            const rested = capsule.width;

            typeKey(field, Qt.Key_A);
            waitFor(() => capsule.width > rested + 5, "First character left the capsule stationary");
            for (let i = 0; i < 5; i++) typeKey(field, Qt.Key_A);
            check(field.length === 6 && field.color.a === 0 && !field.displayText.includes("a"), "Typing exposed the response");
            check(capsule.width < 100, "Capsule snapped to a new width");
            waitFor(() => capsule.width > rested + 40, "Capsule did not widen with typing");
            const dotsView = child("modernLockDots").children.find(item => item instanceof ListView);
            const dots = child("modernLockDots");
            waitFor(() => dotsView.count === 6 && dots.animatedSpan === 72 && dots.width >= 72,
                "Expanded capsule still hides masked dots");
            const firstX = dotsView.mapToItem(screen.item, 0, 0).x;
            typeKey(field, Qt.Key_A);
            check(Math.abs(dotsView.mapToItem(screen.item, 0, 0).x - firstX) < .1, "Existing dots snapped on insertion");
            waitFor(() => dotsView.mapToItem(screen.item, 0, 0).x < firstX - 3, "Existing dots did not glide on insertion");
            typeKey(field, Qt.Key_Backspace);
            waitFor(() => dots.animatedSpan === 72, "Backspace did not recenter the dots");
            typeKey(field, Qt.Key_Escape);
            waitFor(() => capsule.width === rested, "Escape did not restore the compact capsule");
            check(!field.length && Session.submissions === 0, "Escape submitted or retained a response");

            typeKey(field, Qt.Key_A);
            waitFor(() => capsule.width >= rested + 11.9, "Submitted capsule never widened");
            typeKey(field, Qt.Key_Return);
            check(Session.submissions === 1 && !field.length && !field.enabled, "Submission did not clear and gate input");
            check(child("modernLockPrompt").text === "", "Verification drew a message below the capsule");
            waitFor(() => dots.opacity < .75, "Submitted dots never dimmed during verification");
            check(dots.length === 1 && capsule.width >= rested + 11.9, "Verification collapsed the submitted dots early");
            Session.authenticating = false;
            Session.error = "Incorrect password. Try again.";
            check(field.enabled && dots.length === 1 && clock.scale === 1, "Failure did not preserve the capsule or permit a retry");
            waitFor(() => dots.length === 0 && child("modernLockPrompt").text === Session.error,
                "Failed attempt did not clear the dots and restore feedback");
            waitFor(() => capsule.width === rested && child("modernLockStatusIcon").opacity === 1,
                "Failed attempt did not settle back into the lock glyph");
            Session.responseVisible = true;
            Session.prompt = "Verification code";
            Session.error = "";
            check(field.echoMode === TextInput.Normal && child("modernLockPrompt").text === "Verification code",
                "PAM echo-on prompt missing");
            Session.responseVisible = false;
            typeKey(field, Qt.Key_B);
            typeKey(field, Qt.Key_Return);
            check(Session.submissions === 2, "Retry did not submit");
            SystemInfo.lockDesktopVisible = true;
            Session.authenticating = false;
            Session.unlocking = true;
            check(!field.enabled && !field.length && dots.length === 0 && clock.scale === 1
                && !child("modernLockStatusIcon").visible && capsule.border.width === 0,
                "Unlock did not clear the dots ahead of clock travel");
            waitFor(() => screen.item.clockDeparture > .02 && screen.item.clockDeparture < .98, "Unlock motion has no intermediate frame");
            check(clock.scale < 1 && center(clock).y < screen.height / 2, "Clock did not return toward the pill");
            check(child("modernLockStatusIcon").icon === "lock", "Unlock flashed a success checkmark");
            check(screen.item.desktopReveal === 0, "Desktop started appearing behind the traveling clock");
            waitFor(() => child("modernLockStatusIcon").opacity === 0, "Lock icon reappeared during unlock");
            waitFor(() => screen.item.clockDeparture > 1.002, "Clock did not rebound into the pill");
            check(Math.abs(center(clock).y - center(capsule).y) < .05, "Clock and pill separated during the rebound");
            waitFor(() => screen.item.desktopReveal > 0 && screen.item.desktopReveal < 1, "Desktop reveal has no intermediate frame");
            check(clock.opacity === 0 && screen.item.clockDeparture === 1, "Desktop revealed before the clock docked");
            waitFor(() => screen.item.departure === 1, "Unlock motion did not settle");
            check(clock.scale < .25 && center(clock).y < 50, "Clock missed the top pill on unlock");
            const compact = child("modernLockCompactClock");
            check(compact instanceof RollingText && compact.opacity === 1 && clock.opacity === 0
                && String(capsule.color) === String(Theme.bgSolid), "Unlock endpoint does not match the desktop pill");
            Session.unlocking = false;
            waitFor(() => screen.item.departure === 0 && field.enabled, "Relock did not restore the centered clock and input");

            fixture.loaded = false;
            Preferences.motion = "instant";
            fixture.preview = true;
            fixture.narrow = true;
            fixture.loaded = true;
            waitFor(() => screen.item.arrival === 1 && screen.width === 330, "Narrow reduced-motion preview missed its endpoint");
            const previewField = child("lockPassword");
            const previewPill = child("modernLockCapsule");
            const previewClock = child("modernLockClock");
            Preferences.set("lockClockSize", 80);
            const smallClock = previewClock.font.pixelSize;
            Preferences.set("lockClockSize", 160);
            check(previewClock.font.pixelSize > smallClock + 20, "Clock size does not respond on narrow displays");
            previewField.text = "a".repeat(64);
            check(previewPill.width <= screen.width - 24, "Long masked response overflows narrow display");
            typeKey(previewField, Qt.Key_Return);
            check(Session.submissions === 2 && Tokens.lockTransitionDuration === 0 && Tokens.lockDepartureDuration === 0,
                "Preview submitted or reduced motion animated");
            Preferences.set("lockScreenStyle", "legacy");
            waitFor(() => !child("modernLockClock") && child("lockPassword")?.length === 0, "Legacy switch retained a response");
            console.log("LOCK SCREEN UI PASS");
            Qt.quit();
        } catch (error) { console.error(error); Qt.exit(1); } }
    }
}
'''

with tempfile.TemporaryDirectory(prefix='modesty-lock-fixture-') as directory:
    source = Path(directory)
    for name in ('components', 'modules', 'assets', 'theme', 'scripts'):
        (source / name).symlink_to(qml.ROOT / name, target_is_directory=True)
    services = source / 'services'
    services.mkdir()
    for path in (qml.ROOT / 'services').iterdir():
        if path.name != 'Session.qml':
            (services / path.name).symlink_to(path, target_is_directory=path.is_dir())
    (services / 'Session.qml').write_text(SESSION)
    with patch.object(qml, 'ROOT', source):
        qml.run(SCENE, 'LOCK SCREEN UI PASS')
