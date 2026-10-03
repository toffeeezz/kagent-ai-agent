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

    visible: list.count === 0 && !welcomeText.visible
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

    ScrollBar.vertical: ScrollBar {}

    property bool stickToEnd: true

    property bool revealing: false

    onContentHeightChanged: if (stickToEnd)
      positionViewAtEnd()

    onMovingChanged: if (!moving)
      stickToEnd = atYEnd

    Connections {
      target: controller
      function onSelectedSessionChanged() {
        list.revealing = true;

        list.stickToEnd = true;
        list.forceLayout();
        list.positionViewAtEnd();
        Qt.callLater(list.positionViewAtEnd);
      }
    }

    delegate: MessageBubble {}
  }
}
