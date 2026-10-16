pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import "../theme"

ComboBox {
  id: combo

  font.family: Theme.fontFamily
  font.pixelSize: Theme.fontMd

  leftPadding: Theme.spaceMd
  rightPadding: Theme.spaceMd * 2 + 14
  topPadding: 0
  bottomPadding: 0

  contentItem: TextInput {
    text: combo.editable ? combo.editText : combo.displayText
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontMd
    color: (combo.editable ? combo.editText : combo.displayText).length > 0 ? Theme.surfaceOn : Theme.textMuted
    readOnly: !combo.editable
    selectByMouse: true
    clip: true
    verticalAlignment: TextInput.AlignVCenter

    onTextEdited: {
      if (combo.editable)
        combo.editText = text
    }
  }

  delegate: ItemDelegate {
    required property var modelData
    required property int index

    width: combo.width
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontMd
    highlighted: combo.highlightedIndex === index

    contentItem: Text {
      text: String(modelData)
      color: combo.highlightedIndex === index ? Theme.primary : Theme.surfaceOn
      font.family: Theme.fontFamily
      font.pixelSize: Theme.fontMd
      elide: Text.ElideRight
      verticalAlignment: Text.AlignVCenter
      leftPadding: Theme.spaceMd
      rightPadding: Theme.spaceMd
    }

    background: Rectangle {
      color: combo.highlightedIndex === index ? Theme.surfaceContainerHighest : "transparent"
    }
  }

  indicator: Text {
    anchors.verticalCenter: parent.verticalCenter
    anchors.right: parent.right
    anchors.rightMargin: Theme.spaceMd
    text: "\u25BE"
    color: Theme.primary
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontSm
  }

  background: Rectangle {
    color: Theme.surfaceContainerHigh
    radius: Theme.radiusSm
    border.color: Theme.outlineVariant
    implicitWidth: 160
    implicitHeight: Theme.buttonHeight
  }

  popup: Popup {
    y: combo.height + 4
    width: combo.width
    implicitHeight: contentItem.implicitHeight
    padding: Theme.spaceXs

    enter: Transition {
      NumberAnimation {
        property: "opacity"
        from: 0
        to: 1
        duration: Theme.animFast
      }
      NumberAnimation {
        property: "y"
        from: combo.height - 8
        to: combo.height + 4
        duration: Theme.animFast
        easing.type: Easing.OutCubic
      }
    }

    exit: Transition {
      NumberAnimation {
        property: "opacity"
        from: 1
        to: 0
        duration: Theme.animFast
      }
    }

    contentItem: ListView {
      clip: true
      implicitHeight: contentHeight
      model: combo.popup.visible ? combo.delegateModel : null
      currentIndex: combo.highlightedIndex
      highlightMoveDuration: 0

      highlight: Rectangle {
        color: Theme.surfaceContainerHighest
        radius: Theme.radiusSm
      }

      delegate: combo.delegate
    }

    background: Rectangle {
      color: Theme.surfaceContainerHigh
      radius: Theme.radiusMd
      border.color: Theme.outlineVariant
    }
  }
}