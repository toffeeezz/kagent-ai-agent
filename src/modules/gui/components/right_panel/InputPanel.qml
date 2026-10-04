// [ame-chan] stripped comments
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import "../generic"
import "../theme"

CustomRect {
  id: root

  color: Theme.surfaceContainerHigh
  radius: Theme.radiusXl

  Layout.fillWidth: true
  Layout.margins: Theme.panelGap
  Layout.preferredHeight: content.implicitHeight + content.anchors.margins * 2

  ColumnLayout {
    id: content
    anchors.fill: parent
    anchors.margins: Theme.spaceSm
    spacing: 0

    AttachmentPreview {}

    InputField {
      Layout.fillWidth: true
    }
  }
}
