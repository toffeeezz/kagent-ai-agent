// [ame-chan] fixed: welcome/placeholder/thinking text use font.families (plural)
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../generic"
import "../theme"

CustomRect {
  id: root

  Layout.fillHeight: true
  Layout.fillWidth: true

  Text {
    id: welcomeText

    text: "Welcome " + controller.username + "\nOpen or create a session to get started"
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontXl
    color: Theme.surfaceOn
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    width: root.width
    height: root.height

    visible: controller.selectedSessionId < 0
  }

  Text {
    text: "Say hi to " + controller.selectedAgent
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fontXl
    color: Theme.surfaceOn
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    width: root.width
    height: root.height

    visible: controller.messageModel.count === 0 && !welcomeText.visible
  }

  ListView {
    id: list

    anchors.fill: parent
    leftMargin: Theme.spaceMd
    rightMargin: Theme.spaceMd
    clip: true
    spacing: Theme.spaceSm
    boundsBehavior: Flickable.StopAtBounds
    model: controller.messageModel

    displayMarginBeginning: 4000
    displayMarginEnd: 4000

    topMargin: Theme.spaceLg
    bottomMargin: Theme.spaceLg

    property bool stickToEnd: true
    property bool revealing: false
    readonly property int staggerStep: 25
    readonly property int revealDelay: 100
    readonly property bool userInteracting: vbar.pressed || dragging || flicking || moving

    ScrollBar.vertical: ScrollBar {
      id: vbar

      background: null

      contentItem: Rectangle {
        implicitWidth: 6
        implicitHeight: 40
        radius: width / 2
        color: Theme.outline
        opacity: vbar.pressed ? 0.8 : (vbar.hovered ? 0.65 : 0.5)

        Behavior on opacity {
          NumberAnimation {
            duration: 100
          }
        }
      }

      onPressedChanged: {
        if (pressed)
          list.stickToEnd = false;
        else
          list.stickToEnd = list.distanceFromEnd() < 4;
      }
    }

    function scrollToEnd() {
      if (userInteracting)
        return;
      const minY = originY - topMargin;
      const endY = originY + contentHeight + bottomMargin - height;
      contentY = Math.max(minY, endY);
    }

    function distanceFromEnd() {
      return (originY + contentHeight + bottomMargin - height) - contentY;
    }

    onContentHeightChanged: if (stickToEnd)
      scrollToEnd()
    onHeightChanged: if (stickToEnd)
      scrollToEnd()

    onContentYChanged: if (userInteracting)
      stickToEnd = distanceFromEnd() < 4
    onMovingChanged: if (!moving)
      stickToEnd = distanceFromEnd() < 4

    onCountChanged: {
      revealing = true;
      revealTimer.restart();
    }

    Timer {
      id: revealTimer
      interval: list.revealDelay
      onTriggered: list.revealing = false
    }

    Connections {
      target: controller

      function onSelectedSessionChanged() {
        list.revealing = true;
        revealTimer.restart();

        list.stickToEnd = true;
        list.forceLayout();
        list.scrollToEnd();
        Qt.callLater(list.scrollToEnd);
      }
    }
    Connections {
      target: controller.messageModel

      function onRowsAboutToBeInserted() {
        list.revealing = true;
        revealTimer.restart();
      }
    }

    delegate: MessageBubble {}

    footer: Item {
      id: thinkingFooter

      readonly property bool active: controller.isGenerating

      width: ListView.view.width
      height: active ? 36 : 0
      visible: active

      Row {
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.spaceXs

        Repeater {
          model: 3

          Rectangle {
            id: dot
            required property int index

            width: 8
            height: 8
            radius: Theme.radiusSm - 4
            color: Theme.textDimmed

            SequentialAnimation on opacity {
              running: thinkingFooter.active
              loops: Animation.Infinite
              PauseAnimation {
                duration: dot.index * Theme.animNormal
              }
              NumberAnimation {
                from: 0.25
                to: 1
                duration: 350
              }
              NumberAnimation {
                from: 1
                to: 0.25
                duration: 350
              }
              PauseAnimation {
                duration: (2 - dot.index) * Theme.animNormal
              }
            }
          }
        }

        Text {
          text: controller.thinkingLabel || "Thinking\u2026"
          font.family: Theme.fontFamily
          color: Theme.textDimmed
        }
      }
    }
  }
}
