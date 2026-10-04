pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../generic"

Item {
  id: root

  required property int index
  required property string text
  required property string role
  required property var attachments
  readonly property bool fromUser: role === "user"

  property bool shown: false
  property bool animateIn: true

  property int staggerDelay: 0

  readonly property var blocks: {
    const out = [];
    const re = /(`{3,})(\w*)\n([\s\S]*?)\1/g;
    let last = 0, message;
    while ((message = re.exec(text)) !== null) {
      if (message.index > last)
        out.push({
          type: "text",
          lang: "",
          body: text.slice(last, message.index).trim()
        });
      out.push({
        type: "code",
        lang: message[2],
        body: message[3].replace(/\n$/, "")
      });
      last = re.lastIndex;
    }
    if (last < text.length)
      out.push({
        type: "text",
        lang: "",
        body: text.slice(last).trim()
      });
    return out.filter(b => b.body.length > 0);
  }

  width: ListView.view.width
  height: bubble.height

  CustomRect {
    id: bubble
    width: Math.min(400, root.width * 0.75)
    height: content.implicitHeight + 16

    x: root.shown ? (root.fromUser ? root.width - width : 0) : (root.fromUser ? root.width : -width)

    radius: 10

    Behavior on x {
      enabled: root.animateIn
      SequentialAnimation {
        PauseAnimation {
          duration: root.staggerDelay // Uses our fixed snapshot delay
        }

        SpringAnimation {
          spring: 3
          damping: 0.2
        }
      }
    }

    Column {
      id: content
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.top: parent.top
      anchors.margins: 8
      spacing: 8

      Repeater {
        model: root.blocks

        delegate: Loader {
          id: blockLoader
          required property var modelData

          width: content.width
          sourceComponent: modelData.type === "code" ? codeBlock : textBlock

          Component {
            id: textBlock

            TextEdit {
              text: blockLoader.modelData.body
              textFormat: TextEdit.MarkdownText
              readOnly: true
              selectByMouse: true
              wrapMode: TextEdit.Wrap
              onLinkActivated: link => Qt.openUrlExternally(link)
            }
          }

          Component {
            id: codeBlock

            Rectangle {
              color: "#1e1e1e"
              radius: 6
              implicitHeight: codeEdit.y + codeEdit.implicitHeight + 8

              Text {
                x: 8
                y: 6
                text: blockLoader.modelData.lang
                color: "#888888"
                font.pixelSize: 11
              }

              Button {
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 4
                text: "Copy"
                onClicked: {
                  codeEdit.selectAll();
                  codeEdit.copy();
                  codeEdit.deselect();
                }
              }

              TextEdit {
                id: codeEdit
                x: 8
                y: 32
                width: parent.width - 16
                text: blockLoader.modelData.body
                readOnly: true
                selectByMouse: true
                font.family: "monospace"
                color: "#d4d4d4"
                wrapMode: TextEdit.WrapAnywhere

                Component.onCompleted: highlighter.attach(textDocument, blockLoader.modelData.lang)
              }
            }
          }
        }
      }

      Flow {
        width: content.width
        spacing: 6
        visible: root.attachments.length > 0

        Repeater {
          model: root.attachments

          delegate: Item {
            id: att
            required property var modelData

            width: 80
            height: 80

            Image {
              id: thumb
              anchors.fill: parent
              visible: att.modelData.isImage && status !== Image.Error
              source: att.modelData.isImage ? att.modelData.url : ""
              fillMode: Image.PreserveAspectCrop
              asynchronous: true
              sourceSize.width: 160
            }

            Rectangle {
              anchors.fill: parent
              radius: 6
              color: "#33000000"
              visible: !att.modelData.isImage || thumb.status === Image.Error

              Text {
                anchors.centerIn: parent
                width: parent.width - 8
                text: att.modelData.name
                elide: Text.ElideMiddle
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 11
              }
            }
          }
        }
      }
    }
  }

  Component.onCompleted: {
    const view = ListView.view;
    root.animateIn = view ? view.revealing : false;

    if (root.animateIn)
      root.staggerDelay = Math.max(0, ((view.count - 1) - root.index) * 100);

    shown = true;
  }
}
