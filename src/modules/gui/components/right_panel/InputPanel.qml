import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import "../generic"

CustomRect {
  id: root

  property bool isAttachment: false

  Layout.fillWidth: true
  Layout.margins: 20
  Layout.preferredHeight: content.implicitHeight + content.anchors.margins * 2

  ColumnLayout {
    id: content
    anchors.fill: parent
    anchors.margins: 8
    spacing: 0

    RowLayout {
      id: attachmentRow
      Layout.fillWidth: true
      Layout.preferredHeight: root.isAttachment ? 80 : 0
      clip: true

      Behavior on Layout.preferredHeight {
        NumberAnimation {
          duration: 100
          easing.type: Easing.InOutCubic
        }
      }

      CustomRect {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: "red"
      }
    }

    InputField {
      Layout.fillWidth: true
      onAttachmentEmbedded: root.isAttachment = !root.isAttachment
    }
  }
}
