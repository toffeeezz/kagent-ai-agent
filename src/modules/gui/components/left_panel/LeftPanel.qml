import QtQuick
import QtQuick.Layouts

import "../generic"

CustomRect {
  id: root
  Layout.fillHeight: true
  Layout.minimumWidth: 225

  ColumnLayout {
    id: column
    anchors.fill: parent
    spacing: 0

    CustomRect {
      id: agentMenu

      Layout.fillWidth: true
      Layout.preferredHeight: 225

      ColumnLayout {
        id: agentMenuColumn

        anchors.fill: parent

        Text {
          text: "Agents"
          font.pixelSize: 20
          Layout.fillWidth: true
          horizontalAlignment: Text.AlignHCenter
        }

        ListView {

          Layout.fillHeight: true
          Layout.fillWidth: true

          Layout.leftMargin: 10
          Layout.rightMargin: 10
          clip: true
          spacing: 0
          model: controller.agentModel

          delegate: AgentRow {}
        }
      }
    }

    ColumnLayout {
      id: sessionList

      Layout.fillWidth: true
      Layout.fillHeight: true

      Text {
        text: "Sessions"
        font.pixelSize: 16
        Layout.fillWidth: true
        horizontalAlignment: Text.AlignHCenter
      }

      ListView {

        Layout.fillHeight: true
        Layout.fillWidth: true

        Layout.leftMargin: 10
        Layout.rightMargin: 10
        clip: true
        spacing: 5
        model: controller.sessionModel

        delegate: SessionRow {
          implicitHeight: 35
          implicitWidth: parent.width
        }
      }
    }

    CustomRect {
      id: settingsBar

      Layout.fillWidth: true
      Layout.preferredHeight: 100
    }
  }
}
