// qml/Main.qml
import QtQuick

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
    }
  }
}
