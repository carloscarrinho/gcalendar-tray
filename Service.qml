import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons

Item {
  id: root

  property var settings: ({})

  // Settings values
  readonly property string icalUrl: setting("icalUrl", "")
  readonly property int refreshIntervalSec: intSetting("refreshIntervalSec", 60, 30, 1800)
  readonly property bool compact: setting("compact", false) === true

  // State
  property bool configured: false
  property bool refreshing: false
  property string barText: "📅 Calendar"
  property bool barUrgent: false
  property string tooltip: "Calendar"
  property bool hasEvents: false
  property var focusEvent: null
  property var todayEvents: []
  property var upcomingEvents: []
  property string updatedAt: ""
  property string lastError: ""

  readonly property string helperPath: Qt.resolvedUrl("calendar_fetch.py").toString().replace(/^file:\/\//, "")

  function setting(name, fallback) {
    var val = settings ? settings[name] : undefined
    return val === undefined || val === null ? fallback : val
  }

  function intSetting(name, fallback, min, max) {
    var n = parseInt(String(setting(name, fallback)), 10)
    if (!isFinite(n)) n = fallback
    if (n < min) n = min
    if (n > max) n = max
    return n
  }

  function refresh() {
    if (fetchProcess.running) return
    refreshing = true
    var cmd = ["python3", helperPath]
    if (root.compact) cmd.push("--compact")
    if (root.icalUrl && root.icalUrl.trim() !== "") cmd.push(root.icalUrl.trim())
    fetchProcess.command = cmd
    fetchProcess.running = true
  }

  function saveIcalUrl(newUrl) {
    if (!newUrl || newUrl.trim() === "") return
    var cmd = ["python3", helperPath, newUrl.trim()]
    saveProcess.command = cmd
    saveProcess.running = true
  }

  function openUrl(url) {
    if (!url) return
    Qt.openUrlExternally(url)
  }

  function openNotionCalendar() {
    try {
      Quickshell.execDetached(["gtk-launch", "chrome-mcfihigmlcachhfleacaoifboeehiidf-Default"])
    } catch (e) {
      Qt.openUrlExternally("https://calendar.notion.so")
    }
  }

  function openGoogleCalendar() {
    Qt.openUrlExternally("https://calendar.google.com")
  }

  function applyResult(rawJson) {
    try {
      var data = JSON.parse(rawJson)
      if (!data) return
      root.configured = data.configured === true
      root.barText = String(data.bar_text || "📅 Calendar")
      root.barUrgent = data.bar_urgent === true
      root.tooltip = String(data.tooltip || "")
      root.hasEvents = data.has_events === true
      root.focusEvent = data.focus_event || null
      root.todayEvents = data.today_events || []
      root.upcomingEvents = data.upcoming_events || []
      root.updatedAt = String(data.updated_at || "")
      root.lastError = data.error ? String(data.error) : ""
    } catch (err) {
      root.lastError = "Failed to parse calendar output"
    }
  }

  Timer {
    id: pollTimer
    interval: root.refreshIntervalSec * 1000
    repeat: true
    running: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  Process {
    id: fetchProcess
    running: false
    command: []
    stdout: StdioCollector {
      id: fetchStdout
      waitForEnd: true
      onStreamFinished: {
        root.refreshing = false
        if (text && text.trim() !== "") {
          root.applyResult(text.trim())
        }
      }
    }
    stderr: StdioCollector {
      id: fetchStderr
      waitForEnd: true
      onStreamFinished: {
        if (text && text.trim() !== "") {
          root.lastError = text.trim()
        }
      }
    }
    onExited: function(code) {
      root.refreshing = false
    }
  }

  Process {
    id: saveProcess
    running: false
    command: []
    onExited: function(code) {
      root.refresh()
    }
  }
}
