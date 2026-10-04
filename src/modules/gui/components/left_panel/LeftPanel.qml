// [ame-chan] fixed: section headers + New Session row now use font.families (plural)
// [ame-chan] refactored: single-card left panel, outlineVariant dividers between sections, consistent left-aligned headers, rest-state chip on New Session
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

        // [ame-chan] fixed: "+" was a bare fontLg Text that overflowed the 16px content box and
        // rode high vs. the label. Now it lives in a fixed 12px slot (same as the SessionRow
        // bullet) with both children VCenter-aligned, so icon and label share a center line.
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
