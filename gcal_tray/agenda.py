"""Classify events into today / upcoming and choose the bar's focus event."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from .models import Event
from .timefmt import format_relative


@dataclass(frozen=True)
class AgendaItem:
    """One event as shown by the QML. Field order is the JSON key order."""

    calendar_name: str
    title: str
    start_str: str
    end_str: str
    date_str: str
    relative: str
    is_now: bool
    minutes_away: int
    is_all_day: bool
    call_type: str
    call_url: str
    location: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Agenda:
    today: list[AgendaItem]
    upcoming: list[AgendaItem]
    focus: AgendaItem | None
    has_events: bool


def to_item(ev: Event, now: datetime) -> AgendaItem:
    rel = format_relative(ev.start, ev.end, now)
    return AgendaItem(
        calendar_name=ev.calendar_name,
        title=ev.title,
        start_str="All Day" if ev.is_all_day else ev.start.strftime("%H:%M"),
        end_str="" if ev.is_all_day else ev.end.strftime("%H:%M"),
        date_str=ev.start.strftime("%a, %b %d"),
        relative=rel.text,
        is_now=rel.is_now,
        minutes_away=rel.minutes,
        is_all_day=ev.is_all_day,
        call_type=ev.call_type,
        call_url=ev.call_url,
        location=ev.location,
    )


def build_agenda(events: Sequence[Event], now: datetime) -> Agenda:
    """Pure: ``events`` must already be sorted and de-duplicated.

    Focus is the first event happening now (all-day included); otherwise the
    next timed event that starts later today.
    """
    today_date = now.date()
    today: list[AgendaItem] = []
    upcoming: list[AgendaItem] = []
    active: AgendaItem | None = None
    next_up: AgendaItem | None = None

    for ev in events:
        item = to_item(ev, now)
        starts_today = ev.start.date() == today_date

        if item.is_now:
            active = active or item
        elif next_up is None and not ev.is_all_day and starts_today:
            next_up = item

        (today if starts_today or item.is_now else upcoming).append(item)

    return Agenda(today=today, upcoming=upcoming, focus=active or next_up, has_events=bool(events))
