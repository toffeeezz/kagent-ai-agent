// qml/Main.qml
import QtQuick
import QtQuick.Controls

Window {
  visible: true
  width: 1200
  height: 800
  title: "KAgent"

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
    property color accent: "#c0392b"

    parent: Overlay.overlay
    x: (parent.width - width) / 2
    y: 16
    padding: 12

    modal: false
    focus: false
    closePolicy: Popup.NoAutoClose   // the timer closes it, not outside clicks

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
        duration: 150
      }
    }

    background: Rectangle {
      radius: 8
      color: "#2a2a2a"
      border.color: toast.accent
    }

    contentItem: Text {
      id: label
      color: "white"
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
      accent = color !== undefined ? color : "#c0392b";
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
