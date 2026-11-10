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

---

## Dependencies / Permissions

- **Runtime:** the system `python3` (3.11+), **standard library only**. Nothing is installed with the plugin.
- **Network:** outbound HTTPS to the iCal URLs you configure, and nowhere else.
- **Files:** reads `~/.config/gcalendar-tray/config.json`. Local `.ics` paths are also accepted as feed URLs.

---

## Development

`Service.qml` runs `python3 calendar_fetch.py [--compact]`. That file is a thin shim around the
`gcal_tray/` package:

| Module | Responsibility |
| --- | --- |
| `config.py` | Reads and validates `config.json` |
| `fetch.py` | Fetches HTTP feeds and local files in parallel, with an injectable opener |
| `ical.py` | Line unfolding, properties, escapes, dates and TZID |
| `rrule.py` | RRULE parsing and DAILY/WEEKLY expansion |
| `events.py` | Builds `Event`s from iCal text; dedupe |
| `meetings.py` | Detects Meet, Zoom, Teams, Webex and Whereby links |
| `timefmt.py` | Relative labels ("In 15m", "Tomorrow 09:00") |
| `agenda.py` | Splits events into today/upcoming and picks the focus event |
| `render.py` | Bar text, urgency, tooltip and the JSON payload |
| `cli.py` | Wires the stages together (argv, clock, stdout) |

Only `config`, `fetch` and `cli` touch the outside world. Everything else is a pure function.

### Tests

Tests use [uv](https://docs.astral.sh/uv/) and pytest. pytest is a dev-only dependency group and is never needed at runtime.

> [!IMPORTANT]
> Omarchy refuses plugin folders that contain **symlinks**, and a virtualenv contains them
> (`.venv/bin/python`). If a `.venv/` exists inside the plugin folder, `omarchy plugin validate`
> fails, and the shell won't load the plugin. So keep the venv outside the folder:
>
> ```bash
> export UV_PROJECT_ENVIRONMENT=~/.cache/venvs/gcalendar-tray
> ```

```bash
uv run pytest                                   # full suite
UPDATE_GOLDEN=1 uv run pytest tests/test_cli_golden.py   # re-snapshot after an intended output change
python3 calendar_fetch.py tests/fixtures/recurring.ics | python3 -m json.tool   # try a fixture
```

- `tests/test_cli_golden.py` runs the full CLI with a frozen clock (Mon 2026-11-09 10:00, `America/Sao_Paulo`)
  and checks that the output is byte-identical to `tests/golden/*.json`. That makes the JSON contract with the QML explicit.
- `tests/test_known_bugs.py` lists known limitations as strict `xfail` tests: UTC `UNTIL`, MONTHLY/YEARLY
  expansion, ordinal `BYDAY`, and EXDATE with TZID. Fixing one makes its test XPASS, which fails the run until you remove the marker.

### Validate and reload

```bash
omarchy plugin validate .
qmllint -I "$OMARCHY_PATH/shell" Panel.qml Service.qml   # from the qt6-declarative package
omarchy-shell shell rescanPlugins
qs log -p "$OMARCHY_PATH/shell" --tail 100
```
