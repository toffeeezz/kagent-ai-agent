pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import "../theme"

Text {
  id: root

  property string fieldLabel: ""

  text: root.fieldLabel
  font.family: Theme.fontFamily
  font.pixelSize: Theme.fontSm
  color: Theme.textMuted
  elide: Text.ElideRight
  Layout.fillWidth: true
}