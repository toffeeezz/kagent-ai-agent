// [ame-chan] fixed: button label fonts now use font.families (plural) so the
// Theme list actually resolves instead of being treated as one bogus family.
// [ame-chan] stripped comments
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import "../theme"

Button {
  id: root

  property string variant: "filled"
  property bool iconOnly: false

  readonly property color bgColor: {
    switch (root.variant) {
    case "filled":
      return Theme.primary;
    case "tonal":
      return Theme.secondaryContainer;
    case "outlined":
    case "text":
      return "transparent";
    case "danger":
      return Theme.errorContainer;
    default:
      return Theme.primary;
    }
  }

  readonly property color fgColor: {
    switch (root.variant) {
    case "filled":
      return Theme.primaryOn;
    case "tonal":
      return Theme.secondaryContainerOn;
    case "outlined":
    case "text":
      return Theme.primary;
    case "danger":
      return Theme.errorContainerOn;
    default:
      return Theme.primaryOn;
    }
  }

  leftPadding: root.iconOnly ? 0 : Theme.spaceLg
  rightPadding: root.iconOnly ? 0 : Theme.spaceLg

  implicitHeight: root.iconOnly ? Theme.iconButton : Theme.buttonHeight
  implicitWidth: root.iconOnly ? Theme.iconButton : Math.max(64, contentItem.implicitWidth + leftPadding + rightPadding)

  background: Rectangle {
    color: root.bgColor
    radius: root.iconOnly ? Theme.iconButton / 2 : height / 2

    border.color: Theme.outline
    border.width: root.variant === "outlined" ? 1 : 0

    Behavior on color {
      ColorAnimation {
        duration: Theme.animFast
      }
    }

    Rectangle {
      anchors.fill: parent
      radius: parent.radius
      color: root.fgColor
      opacity: !root.enabled ? 0 : (root.pressed ? 0.12 : (root.hovered ? 0.08 : 0))

      Behavior on opacity {
        NumberAnimation {
          duration: Theme.animFast
        }
      }
    }

    Rectangle {
      anchors.fill: parent
      anchors.margins: -2
      radius: parent.radius + 2
      color: "transparent"
      border.color: Theme.primary
      border.width: root.visualFocus ? 2 : 0

      Behavior on border.width {
        NumberAnimation {
          duration: Theme.animFast
        }
      }
    }
  }

  contentItem: Text {
    text: root.text
    font.family: Theme.fontFamily
    font.pixelSize: root.font.pixelSize > 0 ? root.font.pixelSize : Theme.fontMd
    color: root.fgColor
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    elide: Text.ElideRight
  }

  opacity: root.enabled ? 1 : 0.38

  HoverHandler {
    cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
  }
}
