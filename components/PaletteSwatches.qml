import QtQuick

Row {
    required property var scheme
    property real diameter: 7
    spacing: 4

    Repeater {
        model: scheme ? [scheme.red, scheme.yellow, scheme.green, scheme.accent,
            scheme.tertiary ?? scheme.subtext, scheme.text] : []
        Rectangle {
            required property color modelData
            width: parent.diameter
            height: width
            radius: width / 2
            color: modelData
            antialiasing: true
        }
    }
}
