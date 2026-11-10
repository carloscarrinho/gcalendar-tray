# Syncing Work / Corporate Calendars with Secret iCal Restrictions

Many corporate Google Workspace (work/school) accounts restrict external sharing and disable the **"Secret address in iCal format"** via domain-wide administrative policies. 

Additionally, if you share your work calendar with your personal Google account, Google Calendar **does not merge shared calendar events into your personal account's `.ics` feed**. Each calendar feed in Google Calendar is strictly 1:1 and only contains events belonging to that specific calendar.

This guide outlines a simple, free workaround using **Google Apps Script** to automatically mirror your work calendar events onto a dedicated secondary calendar in your personal account, generating a private secret iCal feed that you can use with this plugin.

---

## Architecture Overview

```
[ Work Calendar ] (Inside Work Workspace Account)
       │
       ▼ (Google Apps Script runs every 15 min inside Work account)
[ Secondary Calendar in Personal Account ] (e.g., "Work")
       │
       ▼ (Owned by personal account -> Has its own Secret iCal URL)
[ gcalendar-tray-plugin ] (Fetches and renders events)
```

- **Zero dependencies:** Runs 100% on Google's infrastructure for free.
- **Enterprise-friendly:** Runs natively inside Google Apps Script without needing external OAuth client approval.
- **Auto-sync:** Keeps updates, time changes, and cancellations in sync.
- **Full recurrence support:** Correctly tracks each individual recurring instance (e.g. daily standups) with its unique start timestamp.
- **Preserves meeting links:** Extracts native Google Meet links (`hangoutLink`) as well as Zoom, Teams, and Webex links so the 1-click **Join** button appears in your tray widget.

---

## Step-by-Step Setup

### Step 1: Create a Secondary Calendar in your Personal Account

1. Open [Google Calendar](https://calendar.google.com) logged into your **personal Gmail account**.
2. On the left sidebar, click the **`+`** icon next to **"Other calendars"** > **Create new calendar**.
3. Name it **"Work"** (or `"Work Mirror"`) and click **Create calendar**.
4. Now, find that new calendar under **"Settings for my calendars"** on the left and click it:
   - Scroll down to the **"Integrate calendar"** section.
   - Copy the **Calendar ID** (e.g. `xxxxxxxxxxxxxxxxxxxxxxxxxxxx@group.calendar.google.com`). *Save this for Step 4.*
   - Copy the **"Secret address in iCal format"** (`https://calendar.google.com/calendar/ical/.../private-.../basic.ics`). *Save this for Step 6.*

---

### Step 2: Share the Secondary Calendar with your Work Account

1. Still in the settings for the new secondary calendar in your **personal** account:
2. Under **"Share with specific people or groups"**, click **Add people and groups**.
3. Enter your **work email address** (e.g., `your.name@company.com`).
4. Set permission to **"Make changes to events"**.
5. Click **Send**.

---

### Step 3: Accept / Subscribe in your Work Account

1. Open [Google Calendar](https://calendar.google.com) on your **work account**.
2. On the left sidebar, next to **"Other calendars"**, click the **`+`** icon > **Subscribe to calendar**.
3. Paste the secondary calendar ID copied in Step 1 (the one ending in `@group.calendar.google.com`) and hit **Enter**.
4. Verify that this calendar now appears on the left sidebar in your work Google Calendar.

---

### Step 4: Create the Google Apps Script in your Work Account

Running the script inside your work account guarantees 100% access to all meeting titles, descriptions, and video conference links, even if your company restricts external data sharing.

1. Open [script.google.com](https://script.google.com) logged into your **Work account**.
2. Click **New project** (top-left) and name it `Sync Work Calendar`.
3. **Enable Google Calendar API Service (Required for Google Meet links):**
   - On the left sidebar of the script editor, click the **`+`** icon next to **Services**.
   - Select **Google Calendar API** (Identifier: `Calendar`).
   - Click **Add**.
4. Replace all code in `Code.gs` with the following:

```javascript
/**
 * Sync Work Calendar events to a personal secondary calendar.
 * Automatically mirrors events, recurring series, and conference links
 * so a Secret iCal feed is available.
 */

// ---------------------- CONFIGURATION ----------------------
// Source: "primary" (your work calendar)
const SOURCE_CALENDAR_ID = "primary"; 

// Target: The secondary calendar ID created in your personal account (from Step 1)
const TARGET_CALENDAR_ID = "YOUR_SECONDARY_CALENDAR_ID@group.calendar.google.com";

// Time window for sync: 1 day past, 30 days future
const DAYS_PAST = 1;
const DAYS_FUTURE = 30;
// -----------------------------------------------------------

function syncCalendar() {
  const sourceCal = CalendarApp.getCalendarById(SOURCE_CALENDAR_ID);
  const targetCal = CalendarApp.getCalendarById(TARGET_CALENDAR_ID);

  if (!sourceCal) {
    throw new Error("Could not find source calendar: " + SOURCE_CALENDAR_ID);
  }
  if (!targetCal) {
    throw new Error("Could not find target calendar: " + TARGET_CALENDAR_ID);
  }

  const now = new Date();
  const startTime = new Date(now.getTime() - DAYS_PAST * 24 * 60 * 60 * 1000);
  const endTime = new Date(now.getTime() + DAYS_FUTURE * 24 * 60 * 60 * 1000);

  // Pre-fetch Google Meet / conference links via Calendar API (singleEvents expands recurrences)
  const meetLinkMap = new Map();
  try {
    const apiEvents = Calendar.Events.list(SOURCE_CALENDAR_ID, {
      timeMin: startTime.toISOString(),
      timeMax: endTime.toISOString(),
      singleEvents: true,
    });
    if (apiEvents && apiEvents.items) {
      for (const item of apiEvents.items) {
        const link = item.hangoutLink || 
          (item.conferenceData && item.conferenceData.entryPoints && item.conferenceData.entryPoints.find(e => e.entryPointType === "video")?.uri);
        if (link) {
          meetLinkMap.set(item.id, link);
          if (item.recurringEventId && !meetLinkMap.has(item.recurringEventId)) {
            meetLinkMap.set(item.recurringEventId, link);
          }
        }
      }
    }
  } catch (err) {
    Logger.log("Notice: Calendar API fetch issue: " + err);
  }

  const sourceEvents = sourceCal.getEvents(startTime, endTime);
  const targetEvents = targetCal.getEvents(startTime, endTime);

  // Map existing synced events by unique composite key (sId + startTime)
  const targetMap = new Map();
  const untaggedOrLegacy = [];

  for (const tEvent of targetEvents) {
    const syncKey = tEvent.getTag("SYNC_KEY");
    if (syncKey) {
      targetMap.set(syncKey, tEvent);
    } else {
      // Collect legacy or untagged events from prior runs for cleanup
      untaggedOrLegacy.push(tEvent);
    }
  }

  const seenKeys = new Set();

  for (const sEvent of sourceEvents) {
    // Skip events you declined
    if (sEvent.getMyStatus() === CalendarApp.GuestStatus.NO) {
      continue;
    }

    const sId = sEvent.getId();
    const title = sEvent.getTitle() || "Untitled Event";
    const isAllDay = sEvent.isAllDayEvent();
    const sStart = sEvent.getStartTime();
    const sEnd = sEvent.getEndTime();
    const description = sEvent.getDescription() || "";
    const location = sEvent.getLocation() || "";

    // Unique sync key distinguishes individual instances of recurring events
    const startTimestamp = isAllDay ? sEvent.getAllDayStartDate().getTime() : sStart.getTime();
    const syncKey = sId + "_" + startTimestamp;
    seenKeys.add(syncKey);

    // Inject Google Meet link into description so the iCal parser catches it
    const cleanId = sId.split("@")[0];
    const meetLink = meetLinkMap.get(cleanId);
    let finalDescription = description;
    if (meetLink && !finalDescription.includes(meetLink) && !location.includes(meetLink)) {
      finalDescription = (meetLink + "\n\n" + finalDescription).trim();
    }

    const existing = targetMap.get(syncKey);

    if (existing) {
      // Update details if changed
      if (existing.getTitle() !== title) existing.setTitle(title);
      if (existing.getDescription() !== finalDescription) existing.setDescription(finalDescription);
      if (existing.getLocation() !== location) existing.setLocation(location);

      if (isAllDay) {
        if (!existing.isAllDayEvent() || existing.getAllDayStartDate().getTime() !== sEvent.getAllDayStartDate().getTime()) {
          existing.setAllDayDate(sEvent.getAllDayStartDate());
        }
      } else {
        if (existing.getStartTime().getTime() !== sStart.getTime() ||
            existing.getEndTime().getTime() !== sEnd.getTime()) {
          existing.setTime(sStart, sEnd);
        }
      }
    } else {
      // Create new mirrored event
      let newEvent;
      if (isAllDay) {
        newEvent = targetCal.createAllDayEvent(title, sEvent.getAllDayStartDate(), {
          description: finalDescription,
          location: location,
        });
      } else {
        newEvent = targetCal.createEvent(title, sStart, sEnd, {
          description: finalDescription,
          location: location,
        });
      }
      newEvent.setTag("SYNC_KEY", syncKey);
    }
  }

  // Delete events that were cancelled, declined, or removed from the source calendar
  for (const [syncKey, tEvent] of targetMap.entries()) {
    if (!seenKeys.has(syncKey)) {
      tEvent.deleteEvent();
    }
  }

  // Clean up legacy/untagged events from earlier runs
  for (const legacyEvent of untaggedOrLegacy) {
    legacyEvent.deleteEvent();
  }
}
```

5. Click **Save** (disk icon).
6. Click **Run** with `syncCalendar` selected and approve the permissions.

---

### Step 5: Schedule the Automation (Cron Trigger)

1. In the Apps Script editor, click the clock icon (**Triggers**) on the left sidebar.
2. Click **+ Add Trigger** (bottom-right).
3. Configure:
   - **Function to run:** `syncCalendar`
   - **Event source:** `Time-driven`
   - **Type of time based trigger:** `Minutes timer`
   - **Minute interval:** `Every 15 minutes`
4. Click **Save**.

---

### Step 6: Configure the Tray Plugin

Add the secret iCal feed of the secondary calendar to `~/.config/gcalendar-tray/config.json`:

```json
{
  "calendars": [
    {
      "name": "Personal",
      "url": "https://calendar.google.com/calendar/ical/personal%40gmail.com/private-xxxxxxxx/basic.ics"
    },
    {
      "name": "Work",
      "url": "https://calendar.google.com/calendar/ical/YOUR_SECONDARY_CALENDAR_ID%40group.calendar.google.com/private-yyyyyyyy/basic.ics"
    }
  ]
}
```

Right-click the tray widget or press `R` in the agenda panel to reload. Both calendars will now be merged, show full titles, and display the direct **Join** call buttons!
