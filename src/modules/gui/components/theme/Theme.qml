// [ame-chan] fixed: fontFamily/fontMono were comma-joined strings fed to the
// singular font.family, which Qt does NOT parse as a fallback list — it treated
// the whole string as one nonexistent family name and silently fell back to the
// system default, so no font change was ever visible. Now real string-lists
// consumed via font.families (plural), which Qt does resolve in order.
// Generic CSS names ("sans-serif"/"monospace") dropped — they aren't real Qt
// families; Qt falls back to the platform default on its own.
// [ame-chan] stripped comments
pragma ComponentBehavior: Bound
pragma Singleton
import QtQuick

QtObject {
  readonly property color primary: "#D0BCFF"
  readonly property color primaryOn: "#381E72"
  readonly property color primaryContainer: "#4F378B"
  readonly property color primaryContainerOn: "#EADDFF"

  readonly property color secondary: "#CCC2DC"
  readonly property color secondaryOn: "#332D41"
  readonly property color secondaryContainer: "#4A4458"
  readonly property color secondaryContainerOn: "#E8DEF8"

  readonly property color tertiary: "#EFB8C8"
  readonly property color tertiaryOn: "#492532"
  readonly property color tertiaryContainer: "#633B48"
  readonly property color tertiaryContainerOn: "#FFD8E4"

  readonly property color error: "#F2B8B5"
  readonly property color errorOn: "#601410"
  readonly property color errorContainer: "#8C1D18"
  readonly property color errorContainerOn: "#F9DEDC"

  readonly property color background: "#141218"
  readonly property color backgroundOn: "#E6E0E9"
  readonly property color surface: "#141218"
  readonly property color surfaceOn: "#E6E0E9"
  readonly property color surfaceVariant: "#49454F"
  readonly property color surfaceVariantOn: "#CAC4D0"
  readonly property color surfaceContainerLowest: "#0F0D13"
  readonly property color surfaceContainerLow: "#1D1B20"
  readonly property color surfaceContainer: "#211F26"
  readonly property color surfaceContainerHigh: "#2B2930"
  readonly property color surfaceContainerHighest: "#36343B"

  readonly property color outline: "#938F99"
  readonly property color outlineVariant: "#49454F"
  readonly property color inverseSurface: "#E6E0E9"
  readonly property color inverseSurfaceOn: "#322F35"
  readonly property color inversePrimary: "#6750A4"
  readonly property color scrim: "#000000"

  readonly property color success: "#81C995"

  readonly property color accentDefault: error
  readonly property color accentGreen: success
  readonly property color accentAlt: primary
  readonly property color bgToast: surfaceContainerHighest
  readonly property color bgCode: surfaceContainerLowest
  readonly property color bgAttachmentFallback: surfaceContainerHigh
  readonly property color textPrimary: surfaceOn
  readonly property color textCode: surfaceVariantOn
  readonly property color textMuted: outline
  readonly property color textDimmed: surfaceVariantOn
  readonly property color debugOutline: tertiary
  readonly property color selectedSessionBg: primaryContainer
  readonly property color sessionBg: surfaceContainer

  readonly property int fontXl: 30
  readonly property int fontLg: 22
  readonly property int fontMd: 14
  readonly property int fontSm: 11

  // [ame-chan] font families: ordered fallback lists, consumed via font.families.
  // Installed-only — nothing is bundled, so if Inter/JetBrains Mono are absent
  // these degrade to the OS faces below them.
  readonly property var fontFamily: ["Inter", "Segoe UI Variable", "Segoe UI"]
  readonly property var fontMono: ["JetBrains Mono", "Cascadia Code", "Cascadia Mono", "Consolas"]

  readonly property int radiusSm: 8
  readonly property int radiusMd: 12
  readonly property int radiusLg: 16
  readonly property int radiusXl: 28
  readonly property int radiusFull: 999

  readonly property int spaceXs: 4
  readonly property int spaceSm: 8
  readonly property int spaceMd: 12
  readonly property int spaceLg: 16
  readonly property int panelGap: 12

  readonly property int buttonHeight: 40
  readonly property int iconButton: 40

  readonly property int animFast: 100
  readonly property int animNormal: 200
}
