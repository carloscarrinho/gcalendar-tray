"""RRULE parsing and expansion into concrete instances inside a time window.

Supported: FREQ=DAILY and FREQ=WEEKLY with INTERVAL, COUNT, UNTIL and plain
BYDAY (MO,WE,FR). Any other FREQ yields only the first occurrence, and only
if it starts inside the window.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo

Instance = tuple[datetime, datetime]

WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

# Weekly rules that started more than this before the window jump ahead
# instead of iterating week by week from DTSTART.
WEEKLY_SKIP_AHEAD_THRESHOLD = timedelta(days=14)


@dataclass(frozen=True)
class RRule:
    freq: str | None = None
    interval: int = 1
    count: int | None = None
    until: str | None = None
    byday: str | None = None


def _int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def parse_rrule(rule: str) -> RRule:
    parts = dict(p.split("=", 1) for p in rule.split(";") if "=" in p)
    return RRule(
        freq=parts.get("FREQ"),
        interval=max(1, _int(parts.get("INTERVAL"), 1)),
        count=_int(parts["COUNT"], 0) if "COUNT" in parts else None,
        until=parts.get("UNTIL"),
        byday=parts.get("BYDAY"),
    )


def parse_until(raw: str | None, tz: tzinfo | None) -> datetime | None:
    """Parse UNTIL. Note: a trailing ``Z`` is dropped and the value read in ``tz``."""
    if not raw:
        return None
    try:
        if "T" in raw:
            return datetime.strptime(raw.replace("Z", "")[:15], "%Y%m%dT%H%M%S").replace(tzinfo=tz)
        return datetime.strptime(raw[:8], "%Y%m%d").replace(tzinfo=tz)
    except ValueError:
        return None


def _expand_daily(start: datetime, duration: timedelta, rule: RRule, until: datetime | None,
                  window_start: datetime, window_end: datetime) -> list[Instance]:
    interval, count = rule.interval, rule.count
    if count is not None and start + timedelta(days=count * interval) < window_start:
        return []

    results: list[Instance] = []
    cur = start
    generated = 0
    while cur <= window_end:
        if count is not None and generated >= count:
            break
        if until and cur > until:
            break
        if cur >= window_start:
            results.append((cur, cur + duration))
        elif count is None:
            # Unbounded rule far in the past: jump close to the window.
            days_behind = (window_start.date() - cur.date()).days
            cur += timedelta(days=max(1, days_behind // interval) * interval)
            continue
        cur += timedelta(days=interval)
        generated += 1
    return results


def _expand_weekly(start: datetime, duration: timedelta, rule: RRule, until: datetime | None,
                   window_start: datetime, window_end: datetime) -> list[Instance]:
    interval, count = rule.interval, rule.count
    if rule.byday:
        target_days = sorted(WEEKDAYS[d] for d in rule.byday.split(",") if d in WEEKDAYS)
    else:
        target_days = [start.weekday()]
    if not target_days:
        return []

    if count is not None:
        weeks_needed = (count // len(target_days) + 2) * interval
        if start + timedelta(weeks=weeks_needed) < window_start:
            return []

    week = start - timedelta(days=start.weekday())
    week = week.replace(hour=start.hour, minute=start.minute, second=start.second)

    if count is None and week < window_start - WEEKLY_SKIP_AHEAD_THRESHOLD:
        weeks_behind = (window_start - week).days // 7
        week += timedelta(weeks=(weeks_behind // interval) * interval)

    results: list[Instance] = []
    generated = 0
    while week <= window_end:
        for day_idx in target_days:
            inst = week + timedelta(days=day_idx)
            if inst < start:
                continue
            if count is not None and generated >= count:
                break
            if until and inst > until:
                break
            if window_start <= inst <= window_end:
                results.append((inst, inst + duration))
            generated += 1
        week += timedelta(weeks=interval)
    return results


def _expand_first_only(start: datetime, duration: timedelta, rule: RRule, until: datetime | None,
                       window_start: datetime, window_end: datetime) -> list[Instance]:
    if window_start <= start <= window_end:
        return [(start, start + duration)]
    return []


Expander = Callable[[datetime, timedelta, RRule, "datetime | None", datetime, datetime], list[Instance]]

EXPANDERS: dict[str, Expander] = {
    "DAILY": _expand_daily,
    "WEEKLY": _expand_weekly,
}


def expand(start: datetime, end: datetime, rule: RRule | None,
           window_start: datetime, window_end: datetime) -> list[Instance]:
    """Return ``(start, end)`` instances of an event that fall inside the window."""
    if rule is None:
        if start <= window_end and end >= window_start:
            return [(start, end)]
        return []

    until = parse_until(rule.until, start.tzinfo)
    if until and until < window_start:
        return []

    expander = EXPANDERS.get(rule.freq or "", _expand_first_only)
    return expander(start, end - start, rule, until, window_start, window_end)
