import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import "../generic"

CustomRect {
  id: root
  required property int sessionId
  required property string title
  required property string agentName

  readonly property int bulletSize: 12

  color: controller.selectedSessionId == sessionId ? "red" : "white"

  radius: 15
  clip: true
  scale: 0.9

  Behavior on scale {
    NumberAnimation {
      duration: 100
      easing.type: Easing.InOutCubic
    }
  }

  RowLayout {
    anchors.fill: parent
    anchors.margins: 10
    spacing: 0

    CustomRect {
      Layout.preferredHeight: root.bulletSize
      Layout.preferredWidth: root.bulletSize
      radius: root.bulletSize
    }

    Text {
      text: root.title

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
    onPressed: root.scale = 0.8
    onReleased: root.scale = 1
    onEntered: root.scale = 1
    onExited: root.scale = 0.9
    acceptedButtons: Qt.LeftButton | Qt.RightButton

    onClicked: mouse => {
      if (mouse.button === Qt.RightButton) {
        controller.selectSession(root.sessionId, root.title);
        menu.popup(root, 0, root.height);
      } else if (mouse.button === Qt.LeftButton)
        controller.selectSession(root.sessionId, root.title);
    }
  }

  Menu {
    id: menu

    MenuItem {
      text: "Edit name"
      onTriggered: {
        renameField.text = root.title;
        renameDialog.open();
      }
    }

    MenuSeparator {}

    MenuItem {
      text: "Delete"
      onTriggered: deleteDialog.open()
    }
  }

  Dialog {
    id: renameDialog

    title: "Edit name"
    parent: Overlay.overlay
    anchors.centerIn: Overlay.overlay
    width: 300
    modal: true
    standardButtons: Dialog.Ok | Dialog.Cancel

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
      anchors.left: parent.left
      anchors.right: parent.right
      onAccepted: renameDialog.accept()   // Enter confirms
    }
  }

  Dialog {
    id: deleteDialog

    title: "Delete session?"
    parent: Overlay.overlay
    anchors.centerIn: Overlay.overlay
    modal: true
    standardButtons: Dialog.Yes | Dialog.Cancel

    onAccepted: controller.deleteSession(root.sessionId)

    Text {
      text: "\"" + root.title + "\" will be permanently deleted."
    }
  }
}
