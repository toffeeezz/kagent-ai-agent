pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../generic"

CustomRect {
  id: root

  Layout.fillHeight: true
  Layout.fillWidth: true

  Text {
    id: welcomeText

    text: "Welcome " + controller.username + "\nOpen or create a session to get started"
    font.pixelSize: 30
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    width: root.width
    height: root.height

    visible: controller.selectedSessionId < 0
  }

  Text {
    text: "Say hi to " + controller.selectedAgent
    font.pixelSize: 30
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    width: root.width
    height: root.height

    visible: controller.messageModel.count === 0 && !welcomeText.visible
  }

  ListView {
    id: list

    anchors.fill: parent
    anchors.leftMargin: 12
    anchors.rightMargin: 12
    clip: true
    spacing: 8
    boundsBehavior: Flickable.StopAtBounds
    model: controller.messageModel

    displayMarginBeginning: 4000
    displayMarginEnd: 4000

    topMargin: 16
    bottomMargin: 16

    property bool stickToEnd: true
    property bool revealing: false
    readonly property bool userInteracting: vbar.pressed || dragging || flicking || moving

    ScrollBar.vertical: ScrollBar {
      id: vbar

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
      interval: 400
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
        spacing: 6

        Repeater {
          model: 3

          Rectangle {
            id: dot
            required property int index

            width: 8
            height: 8
            radius: 4
            color: "gray"

            SequentialAnimation on opacity {
              running: thinkingFooter.active
              loops: Animation.Infinite
              PauseAnimation {
                duration: dot.index * 150
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
                duration: (2 - dot.index) * 150
              }
            }
          }
        }

        Text {
          text: controller.thinkingLabel || "Thinking…"
          color: "gray"
        }
      }
    }
  }
}
