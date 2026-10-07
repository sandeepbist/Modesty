import QtQuick
import qs.theme

Text {
    color: Theme.text
    font.family: Tokens.font
    font.pixelSize: Tokens.labelSize
    font.weight: Font.Normal
    font.kerning: true
    font.hintingPreference: Font.PreferVerticalHinting
    font.preferTypoLineMetrics: true
    renderType: Tokens.textRenderType
    textFormat: Text.PlainText
    elide: Text.ElideRight
}
