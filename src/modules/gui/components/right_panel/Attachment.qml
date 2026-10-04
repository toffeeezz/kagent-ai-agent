pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import "../generic"

Item {
  id: root

  required property int index
  required property string path
  required property string url
  required property string mimeType
  required property string name
  required property bool isImage

  implicitWidth: image.width
  implicitHeight: image.height

  CustomRect {
    id: body

    property bool removing: false

    width: root.width
    height: root.height
    scale: 0

    Behavior on scale {
      enabled: !body.removing
      SpringAnimation {
        spring: 5
        damping: 0.25
      }
    }

    NumberAnimation {
      id: removeAnim
      target: body
      property: "scale"
      to: 0
      duration: 150
      easing.type: Easing.InCubic
      onFinished: controller.attachmentModel.removeAt(root.index)
    }

    CustomImage {
      id: image

      source: root.isImage ? root.url : ""
      visible: root.isImage
      radius: 10
      size: 70
    }

    Text {
      visible: !root.isImage
      text: root.name
      font.pixelSize: 8
      width: image.width
      height: image.height
      horizontalAlignment: Text.AlignHCenter
      verticalAlignment: Text.AlignVCenter
    }

    Button {
      id: removeBtn
      text: "X"
      implicitWidth: 20
      implicitHeight: 20
      anchors.right: parent.right
      anchors.top: parent.top
      onClicked: {
        body.removing = true;
        removeAnim.start();
      }
    }

    Component.onCompleted: scale = 1
  }
}
