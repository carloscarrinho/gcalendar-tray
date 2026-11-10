"""Bar text, tooltip and the JSON payload consumed by Service.qml."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from .agenda import Agenda, AgendaItem

TITLE_MAX_CHARS = 22        # longer titles are truncated in the bar...
TITLE_TRUNCATE_TO = 20      # ...to this many chars plus an ellipsis
URGENT_MINUTES = 5          # countdown turns urgent at or below this
COUNTDOWN_MINUTES = 60      # below this, the bar shows "In Xm"
MAX_UPCOMING = 10

NO_EVENTS_BAR = "No more events today"
NO_EVENTS_TOOLTIP = "No more events scheduled for today"


def truncate_title(title: str) -> str:
    return title[:TITLE_TRUNCATE_TO] + "…" if len(title) > TITLE_MAX_CHARS else title


def render_bar(focus: AgendaItem | None, compact: bool = False) -> tuple[str, bool]:
    """Return ``(bar_text, is_urgent)``."""
    if focus is None:
        return NO_EVENTS_BAR, False

    title = truncate_title(focus.title)
    if focus.is_now:
        return ("🔴 Now" if compact else f"🔴 {title} (Now)"), True
    if not focus.is_all_day and focus.minutes_away < COUNTDOWN_MINUTES:
        return f"🕒 In {focus.minutes_away}m: {title}", focus.minutes_away <= URGENT_MINUTES
    return f"🕒 {focus.start_str} {title}", False


def render_tooltip(focus: AgendaItem | None, errors: Sequence[str] = ()) -> str:
    if focus is None:
        tooltip = NO_EVENTS_TOOLTIP
    else:
        tooltip = f"{focus.title}\n{focus.start_str} - {focus.end_str} ({focus.relative})"
        if focus.call_url:
            tooltip += f"\nVideo: {focus.call_type}"
        if focus.calendar_name:
            tooltip += f"\nCalendar: {focus.calendar_name}"
    if errors:
        tooltip += "\nSync notices:\n" + "\n".join(errors)
    return tooltip


def build_payload(agenda: Agenda, *, errors: Sequence[str], ok: bool, calendar_count: int,
                  now: datetime, compact: bool = False) -> dict[str, Any]:
    bar_text, urgent = render_bar(agenda.focus, compact)
    return {
        "ok": ok,
        "configured": True,
        "bar_text": bar_text,
        "bar_urgent": urgent,
        "tooltip": render_tooltip(agenda.focus, errors),
        "has_events": agenda.has_events,
        "focus_event": agenda.focus.to_dict() if agenda.focus else None,
        "today_events": [i.to_dict() for i in agenda.today],
        "upcoming_events": [i.to_dict() for i in agenda.upcoming[:MAX_UPCOMING]],
        "errors": list(errors),
        "calendar_count": calendar_count,
        "updated_at": now.strftime("%H:%M"),
    }


def not_configured_payload(now: datetime, errors: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "ok": True,
        "configured": False,
        "bar_text": "Set Calendar URL",
        "bar_urgent": False,
        "tooltip": "Click to configure Google Calendar / Notion Calendar URL",
        "has_events": False,
        "focus_event": None,
        "today_events": [],
        "upcoming_events": [],
        "errors": list(errors),
        "updated_at": now.strftime("%H:%M"),
    }
