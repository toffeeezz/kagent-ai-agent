// [ame-chan] stripped comments
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import "../generic"
import "../theme"

Item {
  id: root

  required property int index
  required property string text
  required property string role
  required property var attachments
  readonly property bool fromUser: role === "user"
  readonly property real toX: fromUser ? width - bubble.width : 0
  readonly property real fromX: fromUser ? width : -bubble.width - 20

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

    x: root.shown ? root.toX : root.fromX

    color: root.fromUser ? Theme.primaryContainer : Theme.surfaceContainerHigh
    radius: Theme.radiusLg

    Behavior on x {
      enabled: root.animateIn
      SequentialAnimation {
        PauseAnimation {
          duration: root.staggerDelay
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
      anchors.margins: Theme.spaceSm
      spacing: Theme.spaceSm

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
              font.pixelSize: Theme.fontMd
              textFormat: TextEdit.MarkdownText
              color: root.fromUser ? Theme.primaryContainerOn : Theme.surfaceOn
              readOnly: true
              selectByMouse: true
              wrapMode: TextEdit.Wrap
              onLinkActivated: link => Qt.openUrlExternally(link)
              Component.onCompleted: highlighter.setBlockSpacing(textDocument, 100, 25)
            }
          }

          Component {
            id: codeBlock

            Rectangle {
              color: Theme.bgCode
              radius: Theme.radiusMd
              implicitHeight: codeEdit.y + codeEdit.implicitHeight + 8

              Text {
                x: 8
                y: 6
                text: blockLoader.modelData.lang
                color: Theme.textDimmed
                font.pixelSize: Theme.fontSm
              }

              AppButton {
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.spaceXs
                variant: "text"
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
                color: Theme.textCode
                wrapMode: TextEdit.WrapAnywhere

                Component.onCompleted: {
                  highlighter.attach(textDocument, blockLoader.modelData.lang);
                  highlighter.setBlockSpacing(textDocument, 100, 5);
                }
              }
            }
          }
        }
      }

      Flow {
        width: content.width
        spacing: Theme.spaceXs
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
              radius: Theme.radiusSm
              color: Theme.bgAttachmentFallback
              visible: !att.modelData.isImage || thumb.status === Image.Error

              Text {
                anchors.centerIn: parent
                width: parent.width - 8
                text: att.modelData.name
                elide: Text.ElideMiddle
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: Theme.fontSm
                color: Theme.textMuted
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
      root.staggerDelay = Math.max(0, ((view.count - 1) - root.index) * view.staggerStep);

    shown = true;
  }
}
