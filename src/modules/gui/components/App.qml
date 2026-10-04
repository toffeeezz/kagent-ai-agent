// [ame-chan] stripped comments
import QtQuick
import QtQuick.Layouts

import "left_panel"
import "right_panel"
import "generic"
import "theme"

Item {
  anchors.margins: Theme.panelGap

  RowLayout {
    anchors.fill: parent
    spacing: Theme.panelGap

    LeftPanel {}
    RightPanel {
      Layout.fillWidth: true
      Layout.fillHeight: true
    }
  }
}
