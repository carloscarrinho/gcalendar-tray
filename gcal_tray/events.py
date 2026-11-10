"""Turn iCal text into concrete, de-duplicated Event instances inside a window."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, tzinfo

from . import ical
from .meetings import find_meeting_link
from .models import Event, Window
from .rrule import expand, parse_rrule

DEFAULT_DURATION = timedelta(minutes=30)
ALL_DAY_DURATION = timedelta(days=1)
DESCRIPTION_MAX_CHARS = 300
UNTITLED = "Untitled Event"


def _text_prop(block: str, name: str) -> str:
    _, raw = ical.extract_prop(block, name)
    return ical.unescape(raw.strip()) if raw else ""


def parse_vevent(block: str, cal_name: str, local_tz: tzinfo, now: datetime, window: Window) -> list[Event]:
    """Expand one VEVENT body into the instances that are in the window and not yet over."""
    _, status = ical.extract_prop(block, "STATUS")
    if status and status.strip().upper() == "CANCELLED":
        return []

    title = _text_prop(block, "SUMMARY") or UNTITLED

    dtstart_params, dtstart_val = ical.extract_prop(block, "DTSTART")
    start, is_all_day = ical.parse_ical_date(dtstart_params, dtstart_val, local_tz)
    if not start:
        return []

    dtend_params, dtend_val = ical.extract_prop(block, "DTEND")
    if dtend_val:
        end, _ = ical.parse_ical_date(dtend_params, dtend_val, local_tz)
    else:
        end = start + (ALL_DAY_DURATION if is_all_day else DEFAULT_DURATION)
    if not end:
        end = start + DEFAULT_DURATION

    location = _text_prop(block, "LOCATION")
    description = _text_prop(block, "DESCRIPTION")
    call_type, call_url = find_meeting_link(f"{location}\n{description}\n{title}")

    _, rrule_raw = ical.extract_prop(block, "RRULE")
    _, exdate_raw = ical.extract_prop(block, "EXDATE")
    exdates = ical.parse_exdates(exdate_raw)

    rule = parse_rrule(rrule_raw) if rrule_raw else None
    events = []
    for inst_start, inst_end in expand(start, end, rule, window.start, window.end):
        if inst_end <= now or inst_start.strftime("%Y%m%d") in exdates:
            continue
        events.append(Event(
            calendar_name=cal_name,
            title=title,
            start=inst_start,
            end=inst_end,
            is_all_day=is_all_day,
            call_type=call_type or "",
            call_url=call_url or "",
            location=location,
            description=description[:DESCRIPTION_MAX_CHARS],
        ))
    return events


def parse_events(ical_text: str, cal_name: str, local_tz: tzinfo, now: datetime, window: Window) -> list[Event]:
    events: list[Event] = []
    for block in ical.iter_vevents(ical.normalize(ical_text)):
        events.extend(parse_vevent(block, cal_name, local_tz, now, window))
    return events


def dedupe(events: Iterable[Event]) -> list[Event]:
    """Sort by (start, end) and drop repeats of the same title at the same start.

    The first occurrence (in feed order, for equal times) is kept.
    """
    unique: list[Event] = []
    seen: set[tuple[str, str]] = set()
    for ev in sorted(events, key=lambda e: (e.start, e.end)):
        key = (ev.title.lower().strip(), ev.start.isoformat())
        if key not in seen:
            seen.add(key)
            unique.append(ev)
    return unique
