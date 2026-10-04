// [ame-chan] fixed: agent name now uses font.families so Theme list resolves
// [ame-chan] restyled: rest-state chip so unselected agent rows have a visible shape
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

import "../generic"
import "../theme"

CustomRect {
  id: root

  required property string agentName
  required property string imagePath

  readonly property real avatarSize: 50
  readonly property bool selected: controller.selectedAgent === agentName

  implicitHeight: 70
  implicitWidth: parent ? parent.width : 0

  color: selected ? Theme.secondaryContainer : (hover.hovered ? Theme.surfaceContainerHigh : Theme.surfaceContainer)
  radius: Theme.radiusMd
  scale: tap.pressed ? 0.97 : 1

  Behavior on color {
    ColorAnimation {
      duration: Theme.animFast
    }
  }

  Behavior on scale {
    NumberAnimation {
      duration: Theme.animFast
      easing.type: Easing.InOutSine
    }
  }

  HoverHandler {
    id: hover
    cursorShape: Qt.PointingHandCursor
  }

  TapHandler {
    id: tap
    onTapped: controller.selectAgent(root.agentName)
  }

  RowLayout {
    anchors.fill: parent
    anchors.margins: Theme.spaceMd
    spacing: Theme.spaceMd

    Item {
      id: avatarContainer
      Layout.preferredWidth: root.avatarSize
      Layout.preferredHeight: root.avatarSize

      CustomImage {
        id: avatarImage
        source: root.imagePath
        anchors.fill: parent
      }

      Rectangle {
        anchors.fill: parent
        anchors.margins: -1
        radius: width / 2
        color: "transparent"
        border.width: root.selected ? 2 : 0
        border.color: Theme.primary
      }
    }

    Text {
      Layout.fillWidth: true
      Layout.alignment: Qt.AlignVCenter
      text: root.agentName
      color: Theme.surfaceOn
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontMd
      elide: Text.ElideRight
    }
  }
}
