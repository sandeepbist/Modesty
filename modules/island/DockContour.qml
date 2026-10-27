import QtQuick
import qs.theme
import qs.services

ShaderEffect {
    id: root
    required property var frames
    property real mergeProgress:1
    readonly property var activeFrames: frames.filter(f=>f.alpha>0)
    readonly property var boundsFrames: activeFrames.length?activeFrames:[frames[1]]
    readonly property real margin: 24
    readonly property real unionLeft: Math.min(...boundsFrames.map(f=>f.x))
    readonly property real unionTop: Math.min(...boundsFrames.map(f=>f.y))
    x: unionLeft-margin; y: unionTop-margin
    width: Math.max(...boundsFrames.map(f=>f.x+f.width))-unionLeft+margin*2
    height: Math.max(...boundsFrames.map(f=>f.y+f.height))-unionTop+margin*2
    function box(i): vector4d {const f=frames[i];return Qt.vector4d(f.x-x,f.y-y,f.width,f.height);}
    readonly property vector2d extent: Qt.vector2d(width,height)
    readonly property vector4d shapeA: box(0)
    readonly property vector4d shapeB: box(1)
    readonly property vector4d shapeC: box(2)
    readonly property vector3d radii: Qt.vector3d(frames[0].radius,frames[1].radius,frames[2].radius)
    readonly property vector3d alphas: Qt.vector3d(frames[0].alpha,frames[1].alpha,frames[2].alpha)
    readonly property color fillColor: Theme.bgSolid
    readonly property color edgeColor: Theme.withAlpha(Theme.text,.055)
    readonly property real shadowEnabled: Preferences.shadows?1:0
    fragmentShader: Qt.resolvedUrl("../../assets/shaders/dock-contour.frag.qsb")
}
