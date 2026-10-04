// [ame-chan] stripped comments
pragma ComponentBehavior: Bound
import QtQuick
import "../theme"

Rectangle {
  id: root
  color: Theme.surfaceContainerLow
  radius: Theme.radiusLg

  property bool debugVisible: true

  Rectangle {
    id: debugBorder
    anchors.fill: parent
    border.color: Theme.debugOutline
    border.width: 2
    color: "transparent"
    visible: root.debugVisible
  }
}
