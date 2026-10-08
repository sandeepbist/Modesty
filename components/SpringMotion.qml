import QtQuick
import qs.services

// Keep the same damping ratio when animation speed changes.
SpringAnimation {
    spring: 4.5
    damping: (Preferences.motion === "gentle" ? .5 : .36) / Preferences.motionSpeed
    mass: 1 / (Preferences.motionSpeed * Preferences.motionSpeed)
    epsilon: .25
}
