pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import "../theme"

TextField {
  id: root

  font.family: Theme.fontFamily
  font.pixelSize: Theme.fontMd
  color: Theme.surfaceOn
  selectByMouse: true
  placeholderTextColor: Theme.textMuted

  background: Rectangle {
    color: Theme.surfaceContainerHigh
    radius: Theme.radiusSm
    border.color: Theme.outlineVariant
  }
}