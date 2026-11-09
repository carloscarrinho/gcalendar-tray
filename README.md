# Calendar Next Event & Agenda Tray Plugin for Omarchy

An Omarchy bar plugin replicating the macOS Notion Calendar / Cron menu bar experience:
- **Bar Display:** Shows the countdown and title of your next upcoming event (e.g., `🕒 In 15m: Engineering Sync`), or highlights actively ongoing meetings in red (`🔴 Design Review (Now)`).
- **Interactive Popup:** Clicking the widget opens a dedicated agenda card showing:
  - **Up Next / Happening Now:** Highlighting the current or immediate next meeting with time and video service badge.
  - **1-Click Video Call Join:** Direct "Join" button for Google Meet, Zoom, Microsoft Teams, and Webex.
  - **Launch Notion Calendar:** Quick button to open Notion Calendar.
  - **Today's Agenda:** Chronological list of remaining events for the day.
  - **Upcoming Events:** Quick preview of tomorrow and upcoming days.

---

## Setup & Configuration

### 1. Get your Google Calendar Secret iCal URL
Since Notion Calendar syncs directly with Google Calendar:
1. Open [Google Calendar Settings](https://calendar.google.com/calendar/u/0/r/settings).
2. Under **Settings for my calendars** on the left, click your main calendar.
3. Scroll down to **"Integrate calendar"**.
4. Find **"Secret address in iCal format"** and copy the URL (looks like `https://calendar.google.com/calendar/ical/.../basic.ics`).

### 2. Configure the Plugin
You can set your iCal URL in either of two ways:

#### Option A: In the configuration file (Easiest)
Edit `~/.config/gcalendar-tray/config.json`:
```json
{
  "ical_url": "https://calendar.google.com/calendar/ical/your_secret_hash/basic.ics"
}
```

#### Option B: In `~/.config/omarchy/shell.json`
Under the widget's configuration in your bar layout:
```json
{
  "id": "caduco.gcalendar-tray",
  "icalUrl": "https://calendar.google.com/calendar/ical/your_secret_hash/basic.ics",
  "refreshIntervalSec": 60,
  "compact": false
}
```

---

## Adding to Omarchy's Bar

The plugin is symlinked in `~/.config/omarchy/plugins/caduco.gcalendar-tray`.

To add it to your bar:
```bash
omarchy bar put caduco.gcalendar-tray --section right --index 0
```
Or place it next to your clock in `~/.config/omarchy/shell.json`.

---

## Keyboard & Mouse Shortcuts

- **Left-Click:** Open/close the Agenda panel.
- **Right-Click:** Instantly re-fetch and refresh events.
- **R:** Refresh when the panel is open.
- **N:** Launch Notion Calendar.
- **G:** Open Google Calendar in browser.
- **Esc:** Close panel.
