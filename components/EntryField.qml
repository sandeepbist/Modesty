import QtQuick
import QtQuick.Controls
import qs.theme

TextField {
    id: root

    implicitHeight: 38
    leftPadding: 12
    rightPadding: 12
    color: Theme.text
    placeholderTextColor: Theme.subtext
    selectionColor: Theme.accent
    selectedTextColor: Theme.accentText
    font.family: Tokens.font
    font.pixelSize: 13
    font.kerning:true
    font.preferTypoLineMetrics:true
    font.hintingPreference:Font.PreferVerticalHinting
    renderType: Tokens.textRenderType
    selectByMouse: true

    background: Rectangle {
        radius: Tokens.fieldRadius
        color: Theme.surfaceSolid
        border.width: 1
        border.color: root.activeFocus ? Theme.withAlpha(Theme.accent,.55) : Theme.withAlpha(Theme.text, Tokens.borderAlpha)
        SurfaceLighting {anchors.fill:parent;radius:parent.radius;focused:root.activeFocus}

        Behavior on border.color {
            ColorAnimation {
                duration: Tokens.animFast
            }

        }

    }

}
