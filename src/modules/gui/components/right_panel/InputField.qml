// [ame-chan] stripped comments
import QtQuick
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Controls
import QtCore

import "../generic"
import "../theme"

CustomRect {
  id: root

  readonly property int pad: 10
  readonly property int buttonSize: 40
  readonly property int minInputHeight: buttonSize + pad * 2
  readonly property int maxInputHeight: 200
  radius: Theme.radiusMd

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
    spacing: Theme.spaceSm

    AppButton {
      id: uploadBtn
      variant: "text"
      iconOnly: true
      text: "+"

      rotation: hovered ? -90 : 0
      transformOrigin: Item.Center

      Behavior on rotation {
        NumberAnimation {
          duration: Theme.animNormal
          easing.type: Easing.OutCubic
        }
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
        color: Theme.surfaceOn
        placeholderTextColor: Theme.textMuted
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
            if (input.text === "")
              input.text = text;
            input.forceActiveFocus();
          }
        }
      }
    }

    AppButton {
      id: sendBtn
      variant: "filled"
      iconOnly: true
      text: controller.isGenerating ? "\u25a0" : "\u27a4"

      enabled: controller.isGenerating || input.text.trim().length > 0

      onClicked: {
        if (controller.isGenerating)
          controller.stopGeneration();
        else
          root.submit();
      }
    }
  }
}
