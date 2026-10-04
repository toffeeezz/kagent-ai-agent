pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import "../generic"

CustomRect {
  id: root

  Layout.fillWidth: true
  Layout.margins: 20
  Layout.preferredHeight: content.implicitHeight + content.anchors.margins * 2

  ColumnLayout {
    id: content
    anchors.fill: parent
    anchors.margins: 8
    spacing: 0

    AttachmentPreview {}

    InputField {
      Layout.fillWidth: true
    }
  }
}
