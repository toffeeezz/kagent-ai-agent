pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import "../generic"
import "../theme"

CustomRect {
  id: root

  required property string agentName
  required property string imagePath

  readonly property real avatarSize: 50
  readonly property bool selected: controller.selectedAgent === agentName
  readonly property int dialogPad: Theme.spaceLg + Theme.spaceMd

  implicitHeight: 70
  implicitWidth: parent ? parent.width : 0

  color: selected ? Theme.secondaryContainer : (hover.hovered ? Theme.surfaceContainerHigh : Theme.surfaceContainer)
  radius: Theme.radiusMd
  scale: tap.pressed ? 0.97 : 1

  Behavior on color {
    ColorAnimation {
      duration: Theme.animFast
    }
  }

  Behavior on scale {
    NumberAnimation {
      duration: Theme.animFast
      easing.type: Easing.InOutSine
    }
  }

  HoverHandler {
    id: hover
    cursorShape: Qt.PointingHandCursor
  }

  TapHandler {
    id: tap
    acceptedButtons: Qt.LeftButton
    onTapped: controller.selectAgent(root.agentName)
  }

  TapHandler {
    acceptedButtons: Qt.RightButton
    onTapped: {
      controller.selectAgent(root.agentName);
      menu.popup(root, 0, root.height);
    }
  }

  RowLayout {
    anchors.fill: parent
    anchors.margins: Theme.spaceMd
    spacing: Theme.spaceMd

    Item {
      id: avatarContainer
      Layout.preferredWidth: root.avatarSize
      Layout.preferredHeight: root.avatarSize

      CustomImage {
        id: avatarImage
        source: root.imagePath
        anchors.fill: parent
      }

      Rectangle {
        anchors.fill: parent
        anchors.margins: -1
        radius: width / 2
        color: "transparent"
        border.width: root.selected ? 2 : 0
        border.color: Theme.primary
      }
    }

    Text {
      Layout.fillWidth: true
      Layout.alignment: Qt.AlignVCenter
      text: root.agentName
      color: Theme.surfaceOn
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontMd
      elide: Text.ElideRight
    }
  }

  component RowMenuItem: MenuItem {
    id: item
    property color textColor: Theme.surfaceOn

    implicitHeight: 40
    leftPadding: Theme.spaceLg
    rightPadding: Theme.spaceLg

    contentItem: Text {
      text: item.text
      color: item.textColor
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontMd
      verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
      radius: Theme.radiusSm
      color: item.highlighted ? Theme.surfaceContainerHighest : "transparent"
    }
  }

  Menu {
    id: menu

    padding: Theme.spaceSm

    background: Rectangle {
      implicitWidth: 180
      color: Theme.surfaceContainerHigh
      radius: Theme.radiusMd
    }

    RowMenuItem {
      text: "Delete"
      textColor: Theme.error
      onTriggered: deleteDialog.open()
    }
  }

  Dialog {
    id: deleteDialog

    parent: Overlay.overlay
    anchors.centerIn: Overlay.overlay
    width: 360
    modal: true

    leftPadding: root.dialogPad
    rightPadding: root.dialogPad
    topPadding: Theme.spaceSm
    bottomPadding: Theme.spaceLg

    background: Rectangle {
      color: Theme.surfaceContainerHigh
      radius: Theme.radiusXl
    }

    header: Text {
      text: "Delete agent?"
      color: Theme.surfaceOn
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontLg
      leftPadding: root.dialogPad
      rightPadding: root.dialogPad
      topPadding: root.dialogPad
      bottomPadding: Theme.spaceSm
    }

    footer: Item {
      implicitHeight: Theme.buttonHeight + Theme.spaceLg

      RowLayout {
        anchors.fill: parent
        anchors.leftMargin: root.dialogPad
        anchors.rightMargin: root.dialogPad
        anchors.bottomMargin: Theme.spaceLg
        spacing: Theme.spaceSm

        Item {
          Layout.fillWidth: true
        }
        AppButton {
          text: "Cancel"
          variant: "text"
          onClicked: deleteDialog.reject()
        }
        AppButton {
          text: "Delete"
          variant: "danger"
          onClicked: deleteDialog.accept()
        }
      }
    }

    onAccepted: controller.deleteAgent(root.agentName)

    Text {
      width: deleteDialog.availableWidth
      text: "\"" + root.agentName + "\" and all of its sessions and memories will be permanently deleted."
      color: Theme.surfaceVariantOn
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontMd
      wrapMode: Text.Wrap
    }
  }
}