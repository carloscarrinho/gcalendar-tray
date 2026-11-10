import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui

Panel {
  id: root
  moduleName: "caduco.gcalendar-tray"
  ipcTarget: "caduco.gcalendar-tray"
  manageIpc: true

  readonly property color foreground: bar ? bar.foreground : Commons.Color.foreground
  readonly property color dim: Qt.darker(foreground, 1.45)
  readonly property color urgent: bar ? bar.urgent : Commons.Color.urgent
  readonly property color accent: Commons.Color.accent
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Service {
    id: service
    settings: root.settings
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: service.barText
    active: service.barUrgent
    useActiveColor: true
    tooltipText: service.tooltip
    horizontalMargin: 8.5
    verticalPadding: 6
    pressFeedbackButtons: Qt.NoButton

    onPressed: function(b) {
      if (b === Qt.RightButton) {
        service.refresh()
      } else {
        root.toggle()
      }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: panel.loadedContent
    contentWidth: panel.fittedContentWidth(Style.space(390))
    contentHeight: panel.fittedContentHeight(panel.loadedContentHeight, Style.space(560))

    content: PanelKeyCatcher {
      id: keyCatcher
      implicitHeight: mainColumn.implicitHeight + Style.space(24)
      anchors.fill: parent

      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onTextKey: function(t) {
        if (t === "r" || t === "R") service.refresh()
        else if (t === "n" || t === "N") service.openNotionCalendar()
        else if (t === "g" || t === "G") service.openGoogleCalendar()
      }

      Flickable {
        id: panelFlick
        anchors.fill: parent
        anchors.margins: Style.space(12)
        contentWidth: width
        contentHeight: mainColumn.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        interactive: contentHeight > height
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        Column {
          id: mainColumn
          width: panelFlick.width
          spacing: Style.space(12)

          // ----------------------------------------------------
          // Notice Banner (if any calendar failed)
          // ----------------------------------------------------
          BorderSurface {
            visible: service.errors && service.errors.length > 0
            width: parent.width
            implicitHeight: errCol.implicitHeight + Style.space(16)
            color: Qt.rgba(root.urgent.r, root.urgent.g, root.urgent.b, 0.08)
            radius: Style.cornerRadius
            border.color: Qt.rgba(root.urgent.r, root.urgent.g, root.urgent.b, 0.35)
            border.width: 1

            Column {
              id: errCol
              anchors.fill: parent
              anchors.margins: Style.space(10)
              spacing: Style.space(4)

              Text {
                textFormat: Text.PlainText
                text: "Calendar Sync Notice"
                font.family: root.fontFamily
                font.bold: true
                font.pixelSize: Style.font.caption
                color: root.urgent
              }

              Repeater {
                model: service.errors
                Text {
                  required property var modelData
                  width: errCol.width
                  wrapMode: Text.Wrap
                  textFormat: Text.PlainText
                  text: modelData
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.caption * 0.95
                  color: root.dim
                }
              }
            }
          }

          // ----------------------------------------------------
          // Hero Card: Focus / Active Event
          // ----------------------------------------------------
          BorderSurface {
            visible: service.configured && service.focusEvent !== null
            width: parent.width
            implicitHeight: heroCol.implicitHeight + Style.space(24)
            color: service.focusEvent && service.focusEvent.is_now
                   ? Qt.rgba(root.urgent.r, root.urgent.g, root.urgent.b, 0.08)
                   : Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.06)
            radius: Style.cornerRadius
            border.color: service.focusEvent && service.focusEvent.is_now
                          ? Qt.rgba(root.urgent.r, root.urgent.g, root.urgent.b, 0.35)
                          : Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.25)
            border.width: 1

            Column {
              id: heroCol
              anchors.fill: parent
              anchors.margins: Style.space(12)
              spacing: Style.space(6)

              Row {
                width: parent.width
                spacing: Style.space(8)

                // Status Tag
                BorderSurface {
                  height: Style.space(20)
                  implicitWidth: tagText.implicitWidth + Style.space(12)
                  color: service.focusEvent && service.focusEvent.is_now ? root.urgent : root.accent
                  radius: Style.cornerRadius

                  Text {
                    id: tagText
                    anchors.centerIn: parent
                    textFormat: Text.PlainText
                    text: service.focusEvent && service.focusEvent.is_now ? "HAPPENING NOW" : "UP NEXT"
                    font.family: root.fontFamily
                    font.bold: true
                    font.pixelSize: Style.font.caption * 0.85
                    color: Commons.Color.background
                  }
                }

                // Relative time badge
                Text {
                  anchors.verticalCenter: parent.verticalCenter
                  textFormat: Text.PlainText
                  text: service.focusEvent ? service.focusEvent.relative : ""
                  font.family: root.fontFamily
                  font.bold: true
                  font.pixelSize: Style.font.caption
                  color: root.foreground
                }

                // Calendar Name Tag (if multiple calendars)
                BorderSurface {
                  visible: service.calendarCount > 1 && service.focusEvent && service.focusEvent.calendar_name !== ""
                  anchors.verticalCenter: parent.verticalCenter
                  height: Style.space(18)
                  implicitWidth: calTagText.implicitWidth + Style.space(10)
                  color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08)
                  radius: Style.cornerRadius

                  Text {
                    id: calTagText
                    anchors.centerIn: parent
                    textFormat: Text.PlainText
                    text: service.focusEvent ? service.focusEvent.calendar_name : ""
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.caption * 0.8
                    color: root.dim
                  }
                }
              }

              // Event Title
              Text {
                width: parent.width
                textFormat: Text.PlainText
                text: service.focusEvent ? service.focusEvent.title : ""
                font.family: root.fontFamily
                font.bold: true
                font.pixelSize: Style.font.heading
                color: root.foreground
                wrapMode: Text.Wrap
                maximumLineCount: 2
                elide: Text.ElideRight
              }

              // Event Timing & Video details
              Row {
                spacing: Style.space(6)
                Text {
                  textFormat: Text.PlainText
                  text: service.focusEvent ? (service.focusEvent.start_str + " – " + service.focusEvent.end_str) : ""
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.body
                  color: root.dim
                }

                Text {
                  visible: service.focusEvent && service.focusEvent.call_type !== ""
                  textFormat: Text.PlainText
                  text: service.focusEvent ? ("• " + service.focusEvent.call_type) : ""
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.body
                  color: root.accent
                }
              }

              // Action buttons row
              Row {
                width: parent.width
                spacing: Style.space(8)

                Button {
                  visible: service.focusEvent && service.focusEvent.call_url !== ""
                  text: service.focusEvent ? ("Join " + (service.focusEvent.call_type || "Call")) : "Join"
                  iconText: "󰕧"
                  active: true
                  bordered: true
                  onClicked: {
                    if (service.focusEvent && service.focusEvent.call_url) {
                      service.openUrl(service.focusEvent.call_url)
                      root.close()
                    }
                  }
                }

                Button {
                  text: "Notion Calendar"
                  iconText: "󰸗"
                  bordered: true
                  onClicked: {
                    service.openNotionCalendar()
                    root.close()
                  }
                }
              }
            }
          }

          // ----------------------------------------------------
          // Empty State (No more events today)
          // ----------------------------------------------------
          BorderSurface {
            visible: service.configured && service.todayEvents.length === 0 && (service.focusEvent === null || service.focusEvent.is_all_day)
            width: parent.width
            implicitHeight: emptyCol.implicitHeight + Style.space(24)
            color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.04)
            radius: Style.cornerRadius
            border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.10)
            border.width: 1

            Column {
              id: emptyCol
              anchors.fill: parent
              anchors.margins: Style.space(14)
              spacing: Style.space(6)

              Row {
                spacing: Style.space(8)
                Text {
                  textFormat: Text.PlainText
                  text: "󰸗"
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.body
                  color: root.accent
                }

                Text {
                  textFormat: Text.PlainText
                  text: "No more events today"
                  font.family: root.fontFamily
                  font.bold: true
                  font.pixelSize: Style.font.body
                  color: root.foreground
                }
              }

              Text {
                textFormat: Text.PlainText
                text: "Your schedule is clear for the rest of today."
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                color: root.dim
              }

              Row {
                spacing: Style.space(8)

                Button {
                  text: "Open Notion Calendar"
                  iconText: "󰸗"
                  bordered: true
                  onClicked: {
                    service.openNotionCalendar()
                    root.close()
                  }
                }
              }
            }
          }

          // ----------------------------------------------------
          // Today's Agenda
          // ----------------------------------------------------
          Column {
            visible: service.configured && service.todayEvents.length > 0
            width: parent.width
            spacing: Style.space(6)

            PanelSectionHeader {
              text: "Today's Agenda"
              foreground: root.foreground
              fontFamily: root.fontFamily
            }

            Repeater {
              model: service.todayEvents

              delegate: BorderSurface {
                required property var modelData
                width: mainColumn.width
                implicitHeight: itemRow.implicitHeight + Style.space(12)
                color: modelData.is_now
                       ? Qt.rgba(root.urgent.r, root.urgent.g, root.urgent.b, 0.08)
                       : Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.03)
                radius: Style.cornerRadius
                border.color: modelData.is_now
                              ? Qt.rgba(root.urgent.r, root.urgent.g, root.urgent.b, 0.3)
                              : Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08)
                border.width: 1

                RowLayout {
                  id: itemRow
                  anchors.fill: parent
                  anchors.margins: Style.space(8)
                  spacing: Style.space(10)

                  // Time indicator
                  Text {
                    Layout.preferredWidth: Style.space(50)
                    textFormat: Text.PlainText
                    text: modelData.start_str
                    font.family: root.fontFamily
                    font.bold: true
                    font.pixelSize: Style.font.body
                    color: modelData.is_now ? root.urgent : root.foreground
                  }

                  // Title & Video badge
                  ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    RowLayout {
                      spacing: Style.space(6)

                      Text {
                        Layout.fillWidth: true
                        textFormat: Text.PlainText
                        text: modelData.title
                        font.family: root.fontFamily
                        font.pixelSize: Style.font.body
                        color: root.foreground
                        elide: Text.ElideRight
                      }

                      // Calendar badge
                      BorderSurface {
                        visible: service.calendarCount > 1 && modelData.calendar_name !== ""
                        height: Style.space(16)
                        implicitWidth: rowCalText.implicitWidth + Style.space(8)
                        color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08)
                        radius: Style.cornerRadius

                        Text {
                          id: rowCalText
                          anchors.centerIn: parent
                          textFormat: Text.PlainText
                          text: modelData.calendar_name
                          font.family: root.fontFamily
                          font.pixelSize: Style.font.caption * 0.75
                          color: root.dim
                        }
                      }
                    }

                    Text {
                      visible: modelData.call_type !== "" || modelData.is_now
                      Layout.fillWidth: true
                      textFormat: Text.PlainText
                      text: modelData.is_now ? modelData.relative : modelData.call_type
                      font.family: root.fontFamily
                      font.pixelSize: Style.font.caption
                      color: modelData.is_now ? root.urgent : root.accent
                    }
                  }

                  // Quick Join button
                  Button {
                    visible: modelData.call_url !== ""
                    text: "Join"
                    iconText: "󰕧"
                    bordered: true
                    onClicked: {
                      service.openUrl(modelData.call_url)
                      root.close()
                    }
                  }
                }
              }
            }
          }

          // ----------------------------------------------------
          // Coming Up (Upcoming Days)
          // ----------------------------------------------------
          Column {
            visible: service.configured && service.upcomingEvents.length > 0
            width: parent.width
            spacing: Style.space(6)

            PanelSectionHeader {
              text: "Upcoming"
              foreground: root.foreground
              fontFamily: root.fontFamily
            }

            Repeater {
              model: service.upcomingEvents

              delegate: BorderSurface {
                required property var modelData
                width: mainColumn.width
                implicitHeight: upcomingRow.implicitHeight + Style.space(10)
                color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.02)
                radius: Style.cornerRadius
                border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.06)
                border.width: 1

                RowLayout {
                  id: upcomingRow
                  anchors.fill: parent
                  anchors.margins: Style.space(8)
                  spacing: Style.space(10)

                  Text {
                    Layout.preferredWidth: Style.space(90)
                    textFormat: Text.PlainText
                    text: modelData.date_str + " " + modelData.start_str
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.caption
                    color: root.dim
                  }

                  Text {
                    Layout.fillWidth: true
                    textFormat: Text.PlainText
                    text: modelData.title
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.body
                    color: root.foreground
                    elide: Text.ElideRight
                  }
                }
              }
            }
          }

          PanelSeparator {
            foreground: root.foreground
          }

          // ----------------------------------------------------
          // Footer
          // ----------------------------------------------------
          RowLayout {
            width: parent.width

            Text {
              Layout.fillWidth: true
              textFormat: Text.PlainText
              text: service.updatedAt !== "" ? ("Updated " + service.updatedAt) : ""
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
              color: root.dim
            }

            Button {
              text: service.refreshing ? "Refreshing…" : "Refresh (R)"
              bordered: true
              onClicked: service.refresh()
            }
          }
        }
      }
    }
  }
}
