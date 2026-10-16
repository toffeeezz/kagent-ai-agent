import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import "../generic"
import "../theme"

CustomRect {
  id: root
  Layout.fillHeight: true
  Layout.minimumWidth: 225

  NewAgentDialog {
    id: newAgentDialog
    modelList: ["deepseek/deepseek-v4-flash", "deepseek/deepseek-v4.1-flash", "deepseek/deepseek-v3.1", "openai/gpt-4.1", "openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash", "meta-llama/llama-3.3-70b-instruct"]
  }

  ColumnLayout {
    id: column
    anchors.fill: parent
    spacing: 0

    Text {
      text: "Agents"
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontMd
      font.weight: Font.DemiBold
      color: Theme.surfaceOn
      Layout.fillWidth: true
      Layout.leftMargin: Theme.spaceMd
      Layout.topMargin: Theme.spaceLg
      Layout.bottomMargin: Theme.spaceSm
      horizontalAlignment: Text.AlignLeft
    }

    NewAgentCard {
      id: newAgentCard
      onClicked: newAgentDialog.open()
    }

    Item {
      id: agentMenu

      Layout.fillWidth: true
      Layout.preferredHeight: 225

      ColumnLayout {
        id: agentMenuColumn

        anchors.fill: parent

        ListView {
          Layout.fillHeight: true
          Layout.fillWidth: true

          Layout.leftMargin: Theme.spaceMd
          Layout.rightMargin: Theme.spaceMd
          clip: true
          spacing: 0
          model: controller.agentModel

          delegate: AgentRow {}
        }
      }
    }

    Rectangle {
      Layout.fillWidth: true
      Layout.preferredHeight: 1
      Layout.leftMargin: Theme.spaceMd
      Layout.rightMargin: Theme.spaceMd
      color: Theme.outlineVariant
    }

    ColumnLayout {
      id: sessionList

      Layout.fillWidth: true
      Layout.fillHeight: true

      Text {
        text: "Sessions"
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontMd
        font.weight: Font.DemiBold
        color: Theme.surfaceOn
        Layout.fillWidth: true
        Layout.leftMargin: Theme.spaceMd
        Layout.topMargin: Theme.spaceLg
        Layout.bottomMargin: Theme.spaceSm
        horizontalAlignment: Text.AlignLeft
      }

      CustomRect {
        id: newSessionBtn

        readonly property int iconSlot: 12

        Layout.fillWidth: true
        Layout.preferredHeight: Theme.buttonHeight
        Layout.leftMargin: Theme.spaceMd
        Layout.rightMargin: Theme.spaceMd
        Layout.bottomMargin: Theme.spaceSm
        color: mouseArea.containsMouse ? Theme.surfaceContainerHighest : Theme.surfaceContainerHigh
        radius: Theme.radiusMd
        scale: mouseArea.pressed ? 0.98 : 1
        clip: true

        Behavior on color {
          ColorAnimation {
            duration: Theme.animFast
          }
        }

        Behavior on scale {
          NumberAnimation {
            duration: Theme.animFast
            easing.type: Easing.InOutCubic
          }
        }

        RowLayout {
          anchors.fill: parent
          anchors.margins: Theme.spaceMd
          spacing: Theme.spaceMd

          Item {
            Layout.preferredWidth: newSessionBtn.iconSlot
            Layout.preferredHeight: newSessionBtn.iconSlot
            Layout.alignment: Qt.AlignVCenter

            Text {
              anchors.centerIn: parent
              text: "+"
              color: Theme.primary
              font.family: Theme.fontFamily
              font.pixelSize: Theme.fontMd
            }
          }

          Text {
            text: "New Session"
            color: Theme.surfaceOn
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontMd
            elide: Text.ElideRight
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
          }
        }

        MouseArea {
          id: mouseArea

          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          onClicked: controller.createSession()
        }
      }

      ListView {
        Layout.fillHeight: true
        Layout.fillWidth: true

        Layout.leftMargin: Theme.spaceMd
        Layout.rightMargin: Theme.spaceMd
        clip: true
        spacing: Theme.spaceXs
        model: controller.sessionModel

        delegate: SessionRow {
          implicitHeight: 35
          implicitWidth: parent.width
        }
      }
    }

    Rectangle {
      Layout.fillWidth: true
      Layout.preferredHeight: 1
      Layout.leftMargin: Theme.spaceMd
      Layout.rightMargin: Theme.spaceMd
      color: Theme.outlineVariant
    }

    Item {
      id: settingsBar

      Layout.fillWidth: true
      Layout.preferredHeight: Theme.buttonHeight
    }
  }
}