pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import "../generic"
import "../theme"

Popup {
  id: root

  property alias modelList: modelCombo.model
  property bool showError: false

  parent: Overlay.overlay
  anchors.centerIn: parent
  width: Math.min(parent.width - 48, 720)
  height: Math.min(parent.height - 48, 680)
  padding: 0
  modal: true
  focus: true
  closePolicy: Popup.CloseOnEscape

  enter: Transition {
    NumberAnimation {
      property: "opacity"
      from: 0
      to: 1
      duration: Theme.animNormal
    }
  }
  exit: Transition {
    NumberAnimation {
      property: "opacity"
      to: 0
      duration: Theme.animFast
    }
  }

  background: Rectangle {
    color: Theme.surfaceContainerLow
    radius: Theme.radiusLg
    border.color: Theme.outlineVariant
  }

  contentItem: ColumnLayout {
    anchors.fill: parent
    anchors.margins: Theme.spaceLg
    spacing: Theme.spaceMd

    Text {
      text: "New Agent"
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontLg
      font.weight: Font.DemiBold
      color: Theme.surfaceOn
    }

    Text {
      text: "Agents are Markdown files with YAML frontmatter. Leave a field empty to use that parameter's default."
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontSm
      color: Theme.textMuted
      wrapMode: Text.Wrap
      Layout.fillWidth: true
    }

    ScrollView {
      id: scroll
      Layout.fillWidth: true
      Layout.fillHeight: true
      clip: true
      contentWidth: scroll.availableWidth

      ColumnLayout {
        width: scroll.availableWidth
        spacing: Theme.spaceLg

        FieldLabel { fieldLabel: "Identity" ; font.weight: Font.DemiBold ; color: Theme.primary }

        FieldLabel { fieldLabel: "Name (unique, shown in the UI)" }
        AppTextField {
          id: nameInput
          Layout.fillWidth: true
          placeholderText: "e.g. Luna"
        }

        GridLayout {
          Layout.fillWidth: true
          columns: 2
          columnSpacing: Theme.spaceLg
          rowSpacing: Theme.spaceMd

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Type" }
            AppComboBox {
              id: typeCombo
              Layout.fillWidth: true
              model: ["complete", "basic"]
              onActivated: root.validate()
            }
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Language model (OpenRouter ID)" }
            AppComboBox {
              id: modelCombo
              Layout.fillWidth: true
              editable: true
              onActivated: root.validate()
            }
          }
        }

        FieldLabel { fieldLabel: "Avatar" ; font.weight: Font.DemiBold ; color: Theme.primary }

        RowLayout {
          Layout.fillWidth: true
          spacing: Theme.spaceMd

          CustomImage {
            id: avatarPreview
            Layout.preferredWidth: 56
            Layout.preferredHeight: 56
            visible: avatarFile.text !== ""
            source: avatarFile.text
            radius: Theme.radiusFull
          }

          AppTextField {
            id: avatarFile
            Layout.fillWidth: true
            readOnly: true
            placeholderText: "No avatar selected"
          }

          AppButton {
            text: "Browse"
            variant: "outlined"
            onClicked: avatarPicker.open()
          }
        }

        FieldLabel { fieldLabel: "Generation" ; font.weight: Font.DemiBold ; color: Theme.primary }

        GridLayout {
          Layout.fillWidth: true
          columns: 2
          columnSpacing: Theme.spaceLg
          rowSpacing: Theme.spaceMd

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Temperature (default 1.0)" }
            AppTextField {
              id: temperatureInput
              Layout.fillWidth: true
              placeholderText: "1.0"
              validator: DoubleValidator { bottom: 0.0; top: 2.0 }
            }
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Top P (default 1.0)" }
            AppTextField {
              id: topPInput
              Layout.fillWidth: true
              placeholderText: "1.0"
              validator: DoubleValidator { bottom: 0.0; top: 1.0 }
            }
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Frequency penalty (default 0.0)" }
            AppTextField {
              id: frequencyPenaltyInput
              Layout.fillWidth: true
              placeholderText: "0.0"
              validator: DoubleValidator { bottom: -2.0; top: 2.0 }
            }
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Presence penalty (default 0.0)" }
            AppTextField {
              id: presencePenaltyInput
              Layout.fillWidth: true
              placeholderText: "0.0"
              validator: DoubleValidator { bottom: -2.0; top: 2.0 }
            }
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Reasoning effort (optional)" }
            AppComboBox {
              id: reasoningCombo
              Layout.fillWidth: true
              model: ["(none)", "low", "medium", "high"]
              onCurrentTextChanged: root.validate()
            }
          }
        }

        FieldLabel { fieldLabel: "Advanced" ; font.weight: Font.DemiBold ; color: Theme.primary }

        GridLayout {
          Layout.fillWidth: true
          columns: 2
          columnSpacing: Theme.spaceLg
          rowSpacing: Theme.spaceMd

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Max tool loops (complete only, default 40)" }
            AppTextField {
              id: maxLoopInput
              Layout.fillWidth: true
              placeholderText: "40"
              visible: typeCombo.currentText === "complete"
              validator: IntValidator { bottom: 1; top: 10000 }
            }
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Max completion tokens (optional)" }
            AppTextField {
              id: maxTokensInput
              Layout.fillWidth: true
              placeholderText: "no limit"
              validator: IntValidator { bottom: 1; top: 100000000 }
            }
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Seed (optional)" }
            AppTextField {
              id: seedInput
              Layout.fillWidth: true
              placeholderText: "random"
              validator: IntValidator { bottom: 0; top: 2147483647 }
            }
          }

          ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            FieldLabel { fieldLabel: "Stop sequences (comma-separated)" }
            AppTextField {
              id: stopInput
              Layout.fillWidth: true
              placeholderText: "###, END"
            }
          }
        }

        CheckBox {
          id: jsonModeCheck
          Layout.fillWidth: true
          font.family: Theme.fontFamily
          font.pixelSize: Theme.fontMd

          indicator: Rectangle {
            width: 18
            height: 18
            radius: 4
            color: jsonModeCheck.checked ? Theme.primary : Theme.surfaceContainerHigh
            border.color: jsonModeCheck.checked ? Theme.primary : Theme.outline

            Text {
              anchors.centerIn: parent
              text: "\u2713"
              visible: jsonModeCheck.checked
              color: Theme.primaryOn
              font.family: Theme.fontFamily
              font.pixelSize: Theme.fontSm
              font.weight: Font.DemiBold
            }
          }

          contentItem: Text {
            text: "JSON mode (response_format: json_object)"
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontMd
            color: Theme.surfaceOn
            verticalAlignment: Text.AlignVCenter
            leftPadding: jsonModeCheck.indicator.width + Theme.spaceSm
          }
        }

        FieldLabel { fieldLabel: "Persona Prompt" ; font.weight: Font.DemiBold ; color: Theme.primary }

        Rectangle {
          Layout.fillWidth: true
          Layout.preferredHeight: 200
          radius: Theme.radiusMd
          color: Theme.surfaceContainer
          border.color: Theme.outlineVariant
          clip: true

          TextArea {
            id: personaInput
            anchors.fill: parent
            anchors.margins: Theme.spaceSm
            placeholderText: "Everything below the closing `---` becomes the persona prompt. E.g.\n\nYou are Luna, a calm and curious study companion..."
            wrapMode: TextArea.Wrap
            color: Theme.surfaceOn
            placeholderTextColor: Theme.textMuted
            selectByMouse: true
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontMd
            background: null
          }
        }

        Text {
          id: errorLabel
          Layout.fillWidth: true
          text: ""
          visible: root.showError
          color: Theme.error
          font.family: Theme.fontFamily
          font.pixelSize: Theme.fontSm
          wrapMode: Text.Wrap
        }
      }
    }

    FileDialog {
      id: avatarPicker
      title: "Choose avatar image"
      fileMode: FileDialog.OpenFile
      nameFilters: ["Images (*.png *.jpg *.jpeg *.webp *.gif)", "All files (*)"]
      onAccepted: avatarFile.text = selectedFile.toString()
    }

    RowLayout {
      Layout.fillWidth: true
      spacing: Theme.spaceMd

      Item {
        Layout.fillWidth: true
      }

      AppButton {
        text: "Cancel"
        variant: "text"
        onClicked: root.close()
      }

      AppButton {
        id: createBtn
        text: "Create Agent"
        variant: "filled"
        enabled: root.isValid
        onClicked: root.create()
      }
    }
  }

  readonly property bool isValid: {
    return nameInput.text.trim().length > 0
        && personaInput.text.trim().length > 0
        && modelCombo.editText.trim().length > 0;
  }

  function showErrorMsg(msg) {
    errorLabel.text = msg;
    root.showError = true;
  }

  function validate() {
    if (root.showError)
      root.showError = false;
  }

  function create() {
    if (!root.isValid) {
      root.showErrorMsg("Fill in name, model, and persona before creating.");
      return;
    }

    let maxLoop = typeCombo.currentText === "complete"
        ? (parseInt(maxLoopInput.text) || 40)
        : 0;

    let ok = controller.createAgent(
      nameInput.text.trim(),
      typeCombo.currentText,
      modelCombo.editText.trim(),
      personaInput.text,
      avatarFile.text,
      maxLoop,
      temperatureInput.text.trim(),
      topPInput.text.trim(),
      frequencyPenaltyInput.text.trim(),
      presencePenaltyInput.text.trim(),
      reasoningCombo.currentText === "(none)" ? "" : reasoningCombo.currentText,
      maxTokensInput.text.trim(),
      seedInput.text.trim(),
      stopInput.text.trim(),
      jsonModeCheck.checked
    );
    if (ok)
      root.close();
    else
      root.showErrorMsg("Could not create the agent. Check the log for details.");
  }

  onOpened: {
    root.showError = false;
    nameInput.forceActiveFocus();
  }
}