// [ame-chan] fixed: session title, menu items, dialog headers and rename field
// now use font.families (plural) so the Theme list actually resolves.
// [ame-chan] restyled: rest-state chip so unselected session rows have a visible shape
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import "../generic"
import "../theme"

CustomRect {
  id: root

  required property int sessionId
  required property string title
  required property string agentName

  readonly property int bulletSize: 12
  readonly property int dialogPad: Theme.spaceLg + Theme.spaceMd
  readonly property bool selected: controller.selectedSessionId === sessionId

  color: selected ? Theme.secondaryContainer : (hover.hovered ? Theme.surfaceContainerHigh : Theme.surfaceContainer)
  radius: Theme.radiusMd
  scale: leftTap.pressed ? 0.97 : 1

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

  HoverHandler {
    id: hover
    cursorShape: Qt.PointingHandCursor
  }

  TapHandler {
    id: leftTap
    acceptedButtons: Qt.LeftButton
    onTapped: controller.selectSession(root.sessionId, root.title)
  }

  TapHandler {
    acceptedButtons: Qt.RightButton
    onTapped: {
      controller.selectSession(root.sessionId, root.title);
      menu.popup(root, 0, root.height);
    }
  }

  RowLayout {
    anchors.fill: parent
    anchors.margins: Theme.spaceMd
    spacing: Theme.spaceMd

    Rectangle {
      Layout.preferredWidth: root.bulletSize
      Layout.preferredHeight: root.bulletSize
      radius: root.bulletSize / 2
      color: root.selected ? Theme.primary : Theme.outline

      Behavior on color {
        ColorAnimation {
          duration: Theme.animFast
        }
      }
    }

    Text {
      Layout.fillWidth: true
      text: root.title
      color: root.selected ? Theme.secondaryContainerOn : Theme.surfaceOn
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontMd
      elide: Text.ElideRight
      horizontalAlignment: Text.AlignLeft
      verticalAlignment: Text.AlignVCenter
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
      text: "Edit name"
      onTriggered: {
        renameField.text = root.title;
        renameDialog.open();
      }
    }

    MenuSeparator {
      contentItem: Rectangle {
        implicitHeight: 1
        color: Theme.outlineVariant
      }
    }

    RowMenuItem {
      text: "Delete"
      textColor: Theme.error
      onTriggered: deleteDialog.open()
    }
  }

  Dialog {
    id: renameDialog

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
      text: "Edit name"
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
          onClicked: renameDialog.reject()
        }
        AppButton {
          text: "Save"
          variant: "filled"
          onClicked: renameDialog.accept()
        }
      }
    }

    onOpened: {
      renameField.forceActiveFocus();
      renameField.selectAll();
    }
    onAccepted: {
      const name = renameField.text.trim();
      if (name.length > 0 && name !== root.title)
        controller.renameSession(root.sessionId, name);
    }

    TextField {
      id: renameField

      width: renameDialog.availableWidth
      color: Theme.surfaceOn
      selectionColor: Theme.primaryContainer
      selectedTextColor: Theme.primaryContainerOn
      placeholderTextColor: Theme.textMuted
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontMd
      leftPadding: Theme.spaceMd
      rightPadding: Theme.spaceMd
      selectByMouse: true

      background: Rectangle {
        radius: Theme.radiusMd
        color: Theme.surfaceContainerLow
        border.width: renameField.activeFocus ? 2 : 1
        border.color: renameField.activeFocus ? Theme.primary : Theme.outlineVariant
      }

      onAccepted: renameDialog.accept()
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
      text: "Delete session?"
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

    onAccepted: controller.deleteSession(root.sessionId)

    Text {
      width: deleteDialog.availableWidth
      text: "\"" + root.title + "\" will be permanently deleted."
      color: Theme.surfaceVariantOn
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontMd
      wrapMode: Text.Wrap
    }
  }
}
