# Calendar Next Event & Agenda Tray Plugin for Omarchy

An Omarchy bar plugin replicating the macOS Notion Calendar / Cron menu bar experience:
- **Bar Display:** Shows the countdown and title of your next upcoming event (e.g., `🕒 In 15m: Engineering Sync`), highlights actively ongoing meetings in red (`🔴 Design Review (Now)`), or shows `No more events today` when your schedule is done.
- **Multiple Calendars:** Syncs across multiple Google / Notion / Outlook calendars in parallel, merges schedules, and labels events by calendar.
- **Interactive Popup:** Clicking the widget opens an agenda card showing:
  - **Up Next / Happening Now:** Highlighting the current or immediate next meeting with time and video service badge.
  - **1-Click Video Call Join:** Direct "Join" button for Google Meet, Zoom, Microsoft Teams, and Webex.
  - **Launch Notion Calendar:** Quick button to open Notion Calendar.
  - **Today's Agenda:** Chronological list of remaining events for the day.
  - **Upcoming Events:** Quick preview of tomorrow and upcoming days.

---

## Configuration (`~/.config/gcalendar-tray/config.json`)

You can sync **one or multiple calendars** simultaneously.

### Single Calendar Example
```json
{
  "ical_url": "https://calendar.google.com/calendar/ical/.../basic.ics"
}
```

### Multiple Calendars Example (Recommended)
```json
{
  "calendars": [
    {
      "name": "Work",
      "url": "https://calendar.google.com/calendar/ical/work_user%40company.com/private-xxxxxxx/basic.ics"
    },
    {
      "name": "Personal",
      "url": "https://calendar.google.com/calendar/ical/personal%40gmail.com/private-yyyyyyy/basic.ics"
    }
  ]
}
```

Or simple list of URLs:
```json
{
  "calendars": [
    "https://calendar.google.com/calendar/ical/cal1/private-xxxx/basic.ics",
    "https://calendar.google.com/calendar/ical/cal2/private-yyyy/basic.ics"
  ]
}
```

---

## Important: Secret vs Public iCal Address in Google Calendar

> [!IMPORTANT]
> Make sure to copy the **"Secret address in iCal format"**, NOT the "Public address in iCal format":
> - **Public address** (`.../public/basic.ics`): Returns `404 Not Found` unless your calendar is publicly exposed to the world.
> - **Secret address** (`.../private-XXXXXX/basic.ics`): Allows you to sync your private schedule securely without making it public.

---

## Controls

- **Left-Click:** Open/close the Agenda panel.
- **Right-Click:** Instantly re-fetch and refresh events.
- **R:** Refresh when the panel is open.
- **N:** Launch Notion Calendar.
- **G:** Open Google Calendar in browser.
- **Esc:** Close panel.
