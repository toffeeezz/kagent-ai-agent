// [ame-chan] fixed: toast text was on font.family (singular) with a comma-joined
// token, which Qt resolved to nothing — now font.families + a real list.
// [ame-chan] stripped comments
import QtQuick
import QtQuick.Controls
import "theme"

Window {
  visible: true
  width: 1200
  height: 800
  title: "KAgent"

  color: Theme.background

  Loader {
    id: ui
    anchors.fill: parent
    source: "App.qml"
  }

  Connections {
    target: reloader
    function onReload() {
      ui.source = "";
      ui.source = "App.qml";
      toast.show("UI reloaded", "green");
    }
  }

  Popup {
    id: toast

    property alias text: label.text
    property color accent: Theme.accentDefault

    parent: Overlay.overlay
    x: (parent.width - width) / 2
    y: 16
    padding: Theme.spaceMd

    modal: false
    focus: false
    closePolicy: Popup.NoAutoClose

    enter: Transition {
      NumberAnimation {
        property: "y"
        from: -toast.height
        to: 16
        duration: 200
        easing.type: Easing.OutCubic
      }
      NumberAnimation {
        property: "opacity"
        from: 0
        to: 1
        duration: 200
      }
    }
    exit: Transition {
      NumberAnimation {
        property: "opacity"
        to: 0
        duration: Theme.animNormal
      }
    }

    background: Rectangle {
      radius: Theme.radiusSm
      color: Theme.bgToast
      border.color: toast.accent
    }

    contentItem: Text {
      id: label
      font.family: Theme.fontFamily
      color: Theme.textPrimary
      wrapMode: Text.Wrap
      width: Math.min(implicitWidth, 400)
    }

    Timer {
      id: hideTimer
      interval: 4000
      onTriggered: toast.close()
    }

    function show(message, color) {
      text = message;
      accent = color === "green" ? Theme.accentGreen : color !== undefined ? color : Theme.accentDefault;
      open();
      hideTimer.restart();
    }
    Connections {
      target: controller
      function onErrorOccurred(message) {
        toast.show(message);
      }
    }
  }
}
