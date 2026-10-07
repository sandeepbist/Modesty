import QtQuick
import Quickshell
pragma Singleton

Singleton {
    id: root

    readonly property date date: clock.date
    readonly property int hours: clock.hours
    readonly property int minutes: clock.minutes
    readonly property int seconds: clock.seconds
    readonly property string timeStr: Qt.formatDateTime(clock.date, (Preferences.use24Hour ? "HH:mm" : "h:mm") + (Preferences.showSeconds ? ":ss" : ""))


    function format(fmt: string) : string {
        return Qt.formatDateTime(clock.date, fmt);
    }

    SystemClock {
        id: clock

        precision: Preferences.showSeconds ? SystemClock.Seconds : SystemClock.Minutes
    }

}
