import QtQuick
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Controls
import QtCore

import "../generic"

CustomRect {
  id: root

  readonly property int pad: 10
  readonly property int buttonSize: 40
  readonly property int minInputHeight: buttonSize + pad * 2    // 60: the button exactly fits at rest
  readonly property int maxInputHeight: 200
  radius: 10

  Layout.fillWidth: true
  Layout.preferredHeight: Math.max(minInputHeight, Math.min(input.implicitHeight + pad * 2, maxInputHeight))

  function submit() {
    if (controller.isGenerating)
      return;
    if (input.text.trim().length > 0) {
      controller.addMessage(input.text);
      input.clear();
    }
  }
  FileDialog {
    id: picker
    title: "Attach files"
    fileMode: FileDialog.OpenFiles
    nameFilters: ["Images (*.png *.jpg *.jpeg *.webp)", "All files (*)"]
    onAccepted: controller.attachmentModel.addUrls(selectedFiles)
  }

  RowLayout {
    id: inputRow
    anchors.fill: parent
    anchors.margins: root.pad
    spacing: 8

    Button {
      id: uploadBtn
      text: "+"
      font.pixelSize: 30
      Layout.preferredWidth: root.buttonSize
      Layout.preferredHeight: root.buttonSize
      Layout.alignment: Qt.AlignBottom
      background: null

      rotation: hover.hovered ? -90 : 0
      transformOrigin: Item.Center

      Behavior on rotation {
        NumberAnimation {
          duration: 150
          easing.type: Easing.OutCubic
        }
      }

      HoverHandler {
        id: hover
        cursorShape: Qt.PointingHandCursor
      }

      onClicked: picker.open()
    }

    ScrollView {
      id: scroll
      Layout.fillWidth: true
      Layout.fillHeight: true

      TextArea {
        id: input
        width: scroll.availableWidth
        height: Math.max(implicitHeight, scroll.availableHeight)
        verticalAlignment: Text.AlignVCenter
        placeholderText: "Message..."
        wrapMode: TextArea.Wrap
        textFormat: TextEdit.PlainText
        selectByMouse: true
        font.family: "monospace"
        background: null

        Keys.onPressed: event => {
          const isEnter = event.key === Qt.Key_Return || event.key === Qt.Key_Enter;
          if (isEnter && !(event.modifiers & Qt.ShiftModifier)) {
            event.accepted = true;
            if (text.trim().length > 0) {
              root.submit();
              clear();
            }
          }
        }
        Connections {
          target: controller

          function onRestoreInput(text) {
            // Don't clobber anything the user has already started typing
            if (input.text === "")
              input.text = text;
            input.forceActiveFocus();
          }
        }
      }
    }
    Button {
      id: sendBtn
      text: controller.isGenerating ? "■" : "➤"
      font.pixelSize: 22
      Layout.preferredWidth: root.buttonSize
      Layout.preferredHeight: root.buttonSize
      Layout.alignment: Qt.AlignBottom
      background: null

      // Dim the send arrow when there's nothing to send; Stop is always active
      enabled: controller.isGenerating || input.text.trim().length > 0
      opacity: enabled ? 1 : 0.4

      HoverHandler {
        cursorShape: Qt.PointingHandCursor
      }

      onClicked: {
        if (controller.isGenerating)
          controller.stopGeneration();
        else
          root.submit();
      }
    }
  }
}
