pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import "../generic"

ListView {
  id: root

  orientation: ListView.Horizontal
  Layout.fillWidth: true
  Layout.preferredHeight: model.count > 0 ? 80 : 0
  clip: true
  spacing: 10

  Behavior on Layout.preferredHeight {
    NumberAnimation {
      duration: 100
      easing.type: Easing.InOutCubic
    }
  }

  model: controller.attachmentModel

  delegate: Attachment {}
}
