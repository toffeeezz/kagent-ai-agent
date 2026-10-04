import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import "../generic"
import "../theme"

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
          font.pixelSize: Theme.fontLg
          color: Theme.surfaceOn
          Layout.fillWidth: true
          horizontalAlignment: Text.AlignHCenter
        }

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

    ColumnLayout {
      id: sessionList

      Layout.fillWidth: true
      Layout.fillHeight: true

      Text {
        text: "Sessions"
        font.pixelSize: Theme.fontMd
        color: Theme.surfaceOn
        Layout.fillWidth: true
        horizontalAlignment: Text.AlignHCenter
      }

      CustomRect {
        id: newSessionBtn

        readonly property int bulletSize: 12

        Layout.fillWidth: true
        Layout.preferredHeight: 40
        Layout.leftMargin: Theme.spaceMd
        Layout.rightMargin: Theme.spaceMd
        radius: Theme.radiusMd
        clip: true
        scale: 0.9

        Behavior on scale {
          NumberAnimation {
            duration: Theme.animFast
            easing.type: Easing.InOutCubic
          }
        }

        RowLayout {
          anchors.fill: parent
          anchors.margins: Theme.spaceMd
          spacing: 0

          CustomRect {
            Layout.preferredHeight: newSessionBtn.bulletSize
            Layout.preferredWidth: newSessionBtn.bulletSize
            radius: newSessionBtn.bulletSize
          }

          Text {
            text: "New Session"
            color: Theme.surfaceOn
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
          onPressed: newSessionBtn.scale = 0.8
          onReleased: newSessionBtn.scale = 1
          onEntered: newSessionBtn.scale = 1
          onExited: newSessionBtn.scale = 0.9
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

    CustomRect {
      id: settingsBar

      Layout.fillWidth: true
      Layout.preferredHeight: Theme.buttonHeight * 2 + Theme.spaceLg
    }
  }
}