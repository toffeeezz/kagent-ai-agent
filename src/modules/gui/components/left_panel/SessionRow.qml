import QtQuick
import QtQuick.Layouts

import "../generic"

CustomRect {
  id: root
  required property int sessionId
  required property string title
  required property string agentName

  readonly property int bulletSize: 12

  color: controller.selectedSessionId == sessionId ? "red" : "white"

  radius: 15
  clip: true
  scale: 0.9

  Behavior on scale {
    NumberAnimation {
      duration: 100
      easing.type: Easing.InOutCubic
    }
  }

  RowLayout {
    anchors.fill: parent
    anchors.margins: 10
    spacing: 0

    CustomRect {
      Layout.preferredHeight: root.bulletSize
      Layout.preferredWidth: root.bulletSize
      radius: root.bulletSize
    }

    Text {
      text: root.title

      elide: Text.ElideRight
      Layout.fillWidth: true
      horizontalAlignment: Text.AlignHCenter
    }
  }

  MouseArea {
    id: mouseArea

    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onPressed: root.scale = 0.8
    onReleased: root.scale = 1
    onEntered: root.scale = 1
    onExited: root.scale = 0.9

    onClicked: controller.selectSession(root.sessionId, root.title)
  }
}
