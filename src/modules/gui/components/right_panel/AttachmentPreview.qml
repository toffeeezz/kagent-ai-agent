pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import "../generic"
import "../theme"

ListView {
  id: root

  orientation: ListView.Horizontal
  Layout.fillWidth: true
  Layout.preferredHeight: model.count > 0 ? 80 : 0
  clip: true
  spacing: Theme.spaceMd

  Behavior on Layout.preferredHeight {
    NumberAnimation {
      duration: Theme.animFast
      easing.type: Easing.InOutCubic
    }
  }

  model: controller.attachmentModel

  delegate: Attachment {}
}