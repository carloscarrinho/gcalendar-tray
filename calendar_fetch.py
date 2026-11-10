#!/usr/bin/env python3
"""
calendar_fetch.py - Multi-calendar iCal fetcher and parser for Omarchy bar.
Parses Google Calendar / Notion Calendar iCal feeds and outputs JSON for the QML widget.
Supports multiple calendars simultaneously, with parallel fetching and deduplication.
"""

import sys
import os
import json
import re
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gcal_tray.ical import normalize, iter_vevents, extract_prop, parse_ical_date, parse_exdates
from gcal_tray.ical import unescape as unescape_ical
from gcal_tray.meetings import find_meeting_link
from gcal_tray.rrule import expand, parse_rrule
from gcal_tray.timefmt import format_relative

CONFIG_PATH = Path.home() / ".config" / "gcalendar-tray" / "config.json"


def load_calendar_configs():
    """
    Loads calendar configurations from ~/.config/gcalendar-tray/config.json.
    Supports:
    1. "calendars": [
         {"name": "Work", "url": "https://..."},
         {"name": "Personal", "url": "https://..."}
       ]
       or
       "calendars": ["https://...", "https://..."]
    2. "ical_urls": ["https://...", "https://..."]
    3. "ical_url": "https://..." (comma-separated or single)
    """
    configs = []
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Option 1: calendars array
                if "calendars" in data and isinstance(data["calendars"], list):
                    for idx, item in enumerate(data["calendars"]):
                        if isinstance(item, str) and item.strip():
                            configs.append({"name": f"Cal {idx+1}", "url": item.strip()})
                        elif isinstance(item, dict) and item.get("url"):
                            name = item.get("name") or f"Cal {idx+1}"
                            configs.append({"name": name, "url": item["url"].strip(), "color": item.get("color", "")})

                # Option 2: ical_urls array
                elif "ical_urls" in data and isinstance(data["ical_urls"], list):
                    for idx, u in enumerate(data["ical_urls"]):
                        if isinstance(u, str) and u.strip():
                            configs.append({"name": f"Cal {idx+1}", "url": u.strip()})

                # Option 3: ical_url string (single or comma-separated)
                elif "ical_url" in data and isinstance(data["ical_url"], str):
                    raw = data["ical_url"].strip()
                    if raw:
                        parts = [p.strip() for p in raw.split(",") if p.strip()]
                        for idx, p in enumerate(parts):
                            configs.append({"name": f"Cal {idx+1}" if len(parts) > 1 else "Calendar", "url": p})
        except Exception:
            pass
    return configs


def fetch_single_feed(cal_entry):
    name = cal_entry.get("name", "Calendar")
    url = cal_entry.get("url", "").strip()

    if not url:
        return name, None, "Empty URL"

    if os.path.exists(url):
        try:
            with open(url, "r", encoding="utf-8") as f:
                return name, f.read(), None
        except Exception as e:
            return name, None, f"File read error: {e}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) OmarchyGCalendarPlugin/1.0",
            "Accept": "text/calendar, text/plain, */*"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            return name, content, None
    except urllib.error.HTTPError as e:
        if e.code == 404 and "/public/" in url:
            return name, None, "404 Not Found (Make sure to use the 'Secret address in iCal format', not the Public one)"
        return name, None, f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return name, None, f"Network error: {e.reason}"
    except Exception as e:
        return name, None, f"Error: {e}"


def parse_events_from_ical(ical_text, cal_name, local_tz, now, window_start, window_end):
    events = []
    for block in iter_vevents(normalize(ical_text)):

        _, status = extract_prop(block, "STATUS")
        if status and status.strip().upper() == "CANCELLED":
            continue

        _, summary = extract_prop(block, "SUMMARY")
        title = unescape_ical(summary.strip()) if summary else "Untitled Event"

        dtstart_params, dtstart_val = extract_prop(block, "DTSTART")
        if not dtstart_val:
            continue
        dtstart, is_all_day = parse_ical_date(dtstart_params, dtstart_val, local_tz)
        if not dtstart:
            continue

        dtend_params, dtend_val = extract_prop(block, "DTEND")
        if dtend_val:
            dtend, _ = parse_ical_date(dtend_params, dtend_val, local_tz)
        else:
            dtend = dtstart + (timedelta(days=1) if is_all_day else timedelta(minutes=30))

        if not dtend:
            dtend = dtstart + timedelta(minutes=30)

        _, location_raw = extract_prop(block, "LOCATION")
        location = unescape_ical(location_raw.strip()) if location_raw else ""

        _, desc_raw = extract_prop(block, "DESCRIPTION")
        desc = unescape_ical(desc_raw.strip()) if desc_raw else ""

        combined_text = f"{location}\n{desc}\n{title}"
        call_type, call_url = find_meeting_link(combined_text)

        _, rrule = extract_prop(block, "RRULE")
        _, exdate_raw = extract_prop(block, "EXDATE")
        exdate_set = parse_exdates(exdate_raw)

        instances = expand(dtstart, dtend, parse_rrule(rrule) if rrule else None, window_start, window_end)

        for inst_start, inst_end in instances:
            if inst_end <= now:
                continue
            if inst_start.strftime("%Y%m%d") in exdate_set:
                continue

            events.append({
                "calendar_name": cal_name,
                "title": title,
                "start": inst_start,
                "end": inst_end,
                "is_all_day": is_all_day,
                "call_type": call_type or "",
                "call_url": call_url or "",
                "location": location,
                "description": desc[:300] if desc else ""
            })
    return events


def main():
    compact = False
    cli_urls = []

    for arg in sys.argv[1:]:
        if arg == "--compact":
            compact = True
        elif not arg.startswith("--"):
            cli_urls.append(arg)

    # If CLI URLs were passed, wrap them into configs
    if cli_urls:
        cal_configs = [{"name": f"Cal {i+1}", "url": u} for i, u in enumerate(cli_urls)]
    else:
        cal_configs = load_calendar_configs()

    if not cal_configs:
        print(json.dumps({
            "ok": True,
            "configured": False,
            "bar_text": "Set Calendar URL",
            "bar_urgent": False,
            "tooltip": "Click to configure Google Calendar / Notion Calendar URL",
            "has_events": False,
            "focus_event": None,
            "today_events": [],
            "upcoming_events": [],
            "errors": [],
            "updated_at": datetime.now().strftime("%H:%M")
        }))
        return

    # Fetch all calendar feeds in parallel
    fetch_results = []
    with ThreadPoolExecutor(max_workers=min(8, len(cal_configs))) as executor:
        futures = [executor.submit(fetch_single_feed, cfg) for cfg in cal_configs]
        for f in futures:
            fetch_results.append(f.result())

    errors = []
    feed_contents = []
    for name, content, err in fetch_results:
        if err:
            errors.append(f"{name}: {err}")
        elif content:
            feed_contents.append((name, content))

    local_tz = datetime.now().astimezone().tzinfo
    now = datetime.now(local_tz)
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=local_tz)
    window_end = today_start + timedelta(days=7)

    all_events = []
    for name, content in feed_contents:
        all_events.extend(parse_events_from_ical(content, name, local_tz, now, today_start, window_end))

    # Sort and deduplicate
    all_events.sort(key=lambda x: (x["start"], x["end"]))
    unique_events = []
    seen = set()
    for ev in all_events:
        # Deduplicate key by title and start timestamp
        key = (ev["title"].lower().strip(), ev["start"].isoformat())
        if key not in seen:
            seen.add(key)
            unique_events.append(ev)

    today_date = now.date()
    today_events = []
    upcoming_events = []

    active_event = None
    next_event = None

    for ev in unique_events:
        start = ev["start"]
        end = ev["end"]
        rel_str, is_now, total_min = format_relative(start, end, now)

        item = {
            "calendar_name": ev["calendar_name"],
            "title": ev["title"],
            "start_str": start.strftime("%H:%M") if not ev["is_all_day"] else "All Day",
            "end_str": end.strftime("%H:%M") if not ev["is_all_day"] else "",
            "date_str": start.strftime("%a, %b %d"),
            "relative": rel_str,
            "is_now": is_now,
            "minutes_away": total_min,
            "is_all_day": ev["is_all_day"],
            "call_type": ev["call_type"],
            "call_url": ev["call_url"],
            "location": ev["location"]
        }

        if is_now and active_event is None:
            active_event = item
        elif not is_now and next_event is None and not ev["is_all_day"] and start.date() == today_date:
            next_event = item

        if start.date() == today_date or is_now:
            today_events.append(item)
        else:
            upcoming_events.append(item)

    focus = active_event or next_event

    # Bar text formatting
    is_urgent = False
    if focus:
        title_snippet = focus["title"]
        if len(title_snippet) > 22:
            title_snippet = title_snippet[:20] + "…"

        if focus["is_now"]:
            bar_text = f"🔴 {title_snippet} (Now)" if not compact else "🔴 Now"
            is_urgent = True
        elif focus["minutes_away"] <= 5 and not focus["is_all_day"]:
            bar_text = f"🕒 In {focus['minutes_away']}m: {title_snippet}"
            is_urgent = True
        elif focus["minutes_away"] < 60 and not focus["is_all_day"]:
            bar_text = f"🕒 In {focus['minutes_away']}m: {title_snippet}"
        else:
            bar_text = f"🕒 {focus['start_str']} {title_snippet}"

        tooltip = f"{focus['title']}\n{focus['start_str']} - {focus['end_str']} ({focus['relative']})"
        if focus["call_url"]:
            tooltip += f"\nVideo: {focus['call_type']}"
        if focus.get("calendar_name"):
            tooltip += f"\nCalendar: {focus['calendar_name']}"
    else:
        # As requested: short text "No more events today"
        bar_text = "No more events today"
        tooltip = "No more events scheduled for today"

    if errors:
        tooltip += f"\nSync notices:\n" + "\n".join(errors)

    print(json.dumps({
        "ok": len(feed_contents) > 0 or not errors,
        "configured": True,
        "bar_text": bar_text,
        "bar_urgent": is_urgent,
        "tooltip": tooltip,
        "has_events": len(unique_events) > 0,
        "focus_event": focus,
        "today_events": today_events,
        "upcoming_events": upcoming_events[:10],
        "errors": errors,
        "calendar_count": len(cal_configs),
        "updated_at": now.strftime("%H:%M")
    }))


if __name__ == "__main__":
    main()
