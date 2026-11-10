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

from gcal_tray.config import CONFIG_PATH as DEFAULT_CONFIG_PATH, load_calendar_configs
from gcal_tray.events import dedupe, parse_events
from gcal_tray.fetch import fetch_all
from gcal_tray.models import CalendarSource, Window
from gcal_tray.timefmt import format_relative

CONFIG_PATH = DEFAULT_CONFIG_PATH


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
        cal_configs = [CalendarSource(f"Cal {i+1}", u) for i, u in enumerate(cli_urls)]
        config_errors = []
    else:
        loaded = load_calendar_configs(CONFIG_PATH)
        cal_configs, config_errors = loaded.sources, loaded.errors

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
            "errors": config_errors,
            "updated_at": datetime.now().strftime("%H:%M")
        }))
        return

    # Fetch all calendar feeds in parallel
    errors = list(config_errors)
    feed_contents = []
    for r in fetch_all(cal_configs):
        if r.error:
            errors.append(f"{r.name}: {r.error}")
        elif r.content:
            feed_contents.append((r.name, r.content))

    local_tz = datetime.now().astimezone().tzinfo
    now = datetime.now(local_tz)
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=local_tz)
    window_end = today_start + timedelta(days=7)

    all_events = []
    for name, content in feed_contents:
        all_events.extend(parse_events(content, name, local_tz, now, Window(today_start, window_end)))

    unique_events = dedupe(all_events)

    today_date = now.date()
    today_events = []
    upcoming_events = []

    active_event = None
    next_event = None

    for ev in unique_events:
        start = ev.start
        end = ev.end
        rel_str, is_now, total_min = format_relative(start, end, now)

        item = {
            "calendar_name": ev.calendar_name,
            "title": ev.title,
            "start_str": start.strftime("%H:%M") if not ev.is_all_day else "All Day",
            "end_str": end.strftime("%H:%M") if not ev.is_all_day else "",
            "date_str": start.strftime("%a, %b %d"),
            "relative": rel_str,
            "is_now": is_now,
            "minutes_away": total_min,
            "is_all_day": ev.is_all_day,
            "call_type": ev.call_type,
            "call_url": ev.call_url,
            "location": ev.location
        }

        if is_now and active_event is None:
            active_event = item
        elif not is_now and next_event is None and not ev.is_all_day and start.date() == today_date:
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
