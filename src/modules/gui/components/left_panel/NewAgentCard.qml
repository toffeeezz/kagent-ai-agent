pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

import "../generic"
import "../theme"

CustomRect {
  id: root

  signal clicked()

  Layout.fillWidth: true
  Layout.leftMargin: Theme.spaceMd
  Layout.rightMargin: Theme.spaceMd
  Layout.preferredHeight: Theme.buttonHeight
  color: mouseArea.containsMouse ? Theme.surfaceContainerHighest : Theme.surfaceContainerHigh
  radius: Theme.radiusMd
  scale: mouseArea.pressed ? 0.98 : 1
  clip: true

  Behavior on color {
    ColorAnimation {
      duration: Theme.animFast
    }
  }
  Behavior on scale {
    NumberAnimation {
      duration: Theme.animFast
      easing.type: Easing.InOutCubic
    }
  }

  MouseArea {
    id: mouseArea
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: root.clicked()
  }

  RowLayout {
    anchors.fill: parent
    anchors.margins: Theme.spaceMd
    spacing: Theme.spaceMd

    Item {
      Layout.preferredWidth: 14
      Layout.preferredHeight: 14
      Layout.alignment: Qt.AlignVCenter

      Text {
        anchors.centerIn: parent
        text: "+"
        color: Theme.primary
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontLg
      }
    }

    Text {
      text: "New Agent"
      color: Theme.surfaceOn
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontMd
      elide: Text.ElideRight
      Layout.fillWidth: true
      Layout.alignment: Qt.AlignVCenter
      horizontalAlignment: Text.AlignLeft
      verticalAlignment: Text.AlignVCenter
    }
  }
}