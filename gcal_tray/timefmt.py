"""Human-friendly relative time labels ("In 15m", "Tomorrow 09:00", ...)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import NamedTuple

# Same-day events closer than this are shown as a countdown ("In 2h 5m").
COUNTDOWN_MAX_HOURS = 4


class Relative(NamedTuple):
    text: str
    is_now: bool
    minutes: int


def format_relative(start: datetime, end: datetime, now: datetime) -> Relative:
    if start <= now < end:
        rem_min = max(1, int((end - now).total_seconds() / 60))
        return Relative(f"Now (ends in {rem_min}m)", True, rem_min)

    total_min = int((start - now).total_seconds() / 60)

    if total_min < 0:
        return Relative("Ended", False, 0)
    if total_min < 60:
        return Relative(f"In {total_min}m", False, total_min)

    hours, rem_min = divmod(total_min, 60)
    if start.date() == now.date():
        if hours < COUNTDOWN_MAX_HOURS:
            text = f"In {hours}h {rem_min}m" if rem_min > 0 else f"In {hours}h"
            return Relative(text, False, total_min)
        return Relative(f"Today at {start.strftime('%H:%M')}", False, total_min)

    if start.date() == (now + timedelta(days=1)).date():
        return Relative(f"Tomorrow {start.strftime('%H:%M')}", False, total_min)

    return Relative(start.strftime("%a %d %b %H:%M"), False, total_min)
