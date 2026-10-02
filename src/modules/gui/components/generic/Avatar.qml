pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Effects

Item {
    id: root
    property url source
    property real size: 50

    implicitWidth: size
    implicitHeight: size

    Image {
        id: img
        anchors.fill: parent
        source: root.source
        sourceSize: Qt.size(root.size * 2, root.size * 2)
        fillMode: Image.PreserveAspectCrop
        layer.enabled: true
        antialiasing: true
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: mask
        }
    }

    Item {
        id: mask
        anchors.fill: parent
        visible: false
        layer.enabled: true           
        Rectangle {
            anchors.fill: parent
            radius: width / 2
        }
    }
}
