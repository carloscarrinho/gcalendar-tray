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
    contentWidth: panel.fittedContentWidth(Style.space(380))
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
          // Header: Not Configured Banner
          // ----------------------------------------------------
          BorderSurface {
            visible: !service.configured
            width: parent.width
            implicitHeight: setupCol.implicitHeight + Style.space(24)
            color: Qt.rgba(Commons.Color.surface.r, Commons.Color.surface.g, Commons.Color.surface.b, 0.4)
            radius: Style.radius(8)
            border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.15)
            border.width: 1

            Column {
              id: setupCol
              anchors.fill: parent
              anchors.margins: Style.space(12)
              spacing: Style.space(8)

              Text {
                textFormat: Text.PlainText
                text: "Calendar Not Configured"
                font.family: root.fontFamily
                font.bold: true
                font.pixelSize: Style.font.body
                color: root.foreground
              }

              Text {
                textFormat: Text.PlainText
                width: parent.width
                wrapMode: Text.Wrap
                text: "To show your upcoming Notion / Google events in the bar:\n\n1. In Google Calendar, go to Settings → Click your calendar.\n2. Scroll to 'Secret address in iCal format' and copy it.\n3. Save it to ~/.config/gcalendar-tray/config.json or pass it in shell.json."
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                color: Qt.darker(root.foreground, 1.25)
              }

              Row {
                spacing: Style.space(8)

                Button {
                  text: "Open Google Calendar"
                  onClicked: service.openGoogleCalendar()
                }

                Button {
                  text: "Refresh"
                  onClicked: service.refresh()
                }
              }
            }
          }

          // ----------------------------------------------------
          // Hero Card: Focus / Next Event
          // ----------------------------------------------------
          BorderSurface {
            visible: service.configured && service.focusEvent !== null
            width: parent.width
            implicitHeight: heroCol.implicitHeight + Style.space(24)
            color: service.focusEvent && service.focusEvent.is_now
                   ? Qt.rgba(root.urgent.r, root.urgent.g, root.urgent.b, 0.12)
                   : Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.10)
            radius: Style.radius(8)
            border.color: service.focusEvent && service.focusEvent.is_now
                          ? Qt.rgba(root.urgent.r, root.urgent.g, root.urgent.b, 0.4)
                          : Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.3)
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
                  radius: Style.radius(4)

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
              }

              // Event Title
              Text {
                width: parent.width
                textFormat: Text.PlainText
                text: service.focusEvent ? service.focusEvent.title : ""
                font.family: root.fontFamily
                font.bold: true
                font.pixelSize: Style.font.headline
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
                  color: Qt.darker(root.foreground, 1.2)
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
                  onClicked: {
                    service.openNotionCalendar()
                    root.close()
                  }
                }
              }
            }
          }

          // ----------------------------------------------------
          // Empty State (configured but no upcoming events today)
          // ----------------------------------------------------
          BorderSurface {
            visible: service.configured && service.todayEvents.length === 0 && (service.focusEvent === null || service.focusEvent.is_all_day)
            width: parent.width
            implicitHeight: emptyCol.implicitHeight + Style.space(24)
            color: Qt.rgba(Commons.Color.surface.r, Commons.Color.surface.g, Commons.Color.surface.b, 0.3)
            radius: Style.radius(8)

            Column {
              id: emptyCol
              anchors.fill: parent
              anchors.margins: Style.space(14)
              spacing: Style.space(6)

              Text {
                textFormat: Text.PlainText
                text: "✨ No upcoming events today"
                font.family: root.fontFamily
                font.bold: true
                font.pixelSize: Style.font.body
                color: root.foreground
              }

              Text {
                textFormat: Text.PlainText
                text: "Your schedule is clear for the rest of today."
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                color: Qt.darker(root.foreground, 1.3)
              }

              Row {
                spacing: Style.space(8)

                Button {
                  text: "Open Notion Calendar"
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

            Text {
              textFormat: Text.PlainText
              text: "Today's Agenda"
              font.family: root.fontFamily
              font.bold: true
              font.pixelSize: Style.font.caption
              color: Qt.darker(root.foreground, 1.4)
            }

            Repeater {
              model: service.todayEvents

              delegate: BorderSurface {
                required property var modelData
                width: mainColumn.width
                implicitHeight: itemRow.implicitHeight + Style.space(12)
                color: modelData.is_now
                       ? Qt.rgba(root.urgent.r, root.urgent.g, root.urgent.b, 0.08)
                       : Qt.rgba(Commons.Color.surface.r, Commons.Color.surface.g, Commons.Color.surface.b, 0.25)
                radius: Style.radius(6)
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

                    Text {
                      Layout.fillWidth: true
                      textFormat: Text.PlainText
                      text: modelData.title
                      font.family: root.fontFamily
                      font.pixelSize: Style.font.body
                      color: root.foreground
                      elide: Text.ElideRight
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

            Text {
              textFormat: Text.PlainText
              text: "Upcoming"
              font.family: root.fontFamily
              font.bold: true
              font.pixelSize: Style.font.caption
              color: Qt.darker(root.foreground, 1.4)
            }

            Repeater {
              model: service.upcomingEvents

              delegate: BorderSurface {
                required property var modelData
                width: mainColumn.width
                implicitHeight: upcomingRow.implicitHeight + Style.space(10)
                color: Qt.rgba(Commons.Color.surface.r, Commons.Color.surface.g, Commons.Color.surface.b, 0.15)
                radius: Style.radius(6)

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
                    color: Qt.darker(root.foreground, 1.3)
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
              color: Qt.darker(root.foreground, 1.6)
            }

            Button {
              text: service.refreshing ? "Refreshing…" : "Refresh (R)"
              onClicked: service.refresh()
            }
          }
        }
      }
    }
  }
}
