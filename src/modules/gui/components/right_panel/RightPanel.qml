import QtQuick
import QtQuick.Layouts
import "../generic"

CustomRect {
  id: root
  Layout.fillHeight: true
  Layout.fillWidth: true

  ColumnLayout {

    anchors.fill: parent
    spacing: 0

    ChatPanel {}

    InputPanel {}
  }
}
