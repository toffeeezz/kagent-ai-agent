import QtQuick
import QtQuick.Layouts

import "../generic"

CustomRect {
  id: root
  required property string agentName
  required property string imagePath
  readonly property real avatarSize: 50

  implicitHeight: 70
  implicitWidth: parent.width

  radius: 15
  clip: true

  Behavior on scale {
    NumberAnimation {
      duration: 100
      easing.type: Easing.InOutSine
    }
  }
  scale: 0.9

  RowLayout {
    anchors.fill: parent
    anchors.margins: 10

    Avatar {
      source: root.imagePath
      Layout.preferredWidth: root.avatarSize
      Layout.preferredHeight: root.avatarSize
    }

    Text {
      text: root.agentName

      elide: Text.ElideRight
      Layout.fillWidth: true
      Layout.alignment: Qt.AlignVCenter
    }
  }

  MouseArea {
    id: mouseArea

    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor

    onPressed: root.scale = 0.8
    onReleased: root.scale = 1

    onClicked: controller.selectAgent(root.agentName)

    onEntered: root.scale = 1
    onExited: root.scale = 0.9
  }
}
