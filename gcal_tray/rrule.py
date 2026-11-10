"""RRULE parsing and expansion into concrete instances inside a time window.

Supported: FREQ=DAILY, WEEKLY, MONTHLY and YEARLY with INTERVAL, COUNT and
UNTIL. WEEKLY takes plain BYDAY (MO,WE,FR). MONTHLY takes BYDAY, including
ordinals (2MO, -1FR), and BYMONTHDAY (including negatives). YEARLY repeats on
DTSTART's month and day. Days that don't exist in a month (the 31st, Feb 29)
are skipped, as RFC 5545 says. Any other FREQ yields only the first occurrence,
and only if it starts inside the window.
"""

from __future__ import annotations

import calendar
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo

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
    bymonthday: str | None = None


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
        bymonthday=parts.get("BYMONTHDAY"),
    )


def parse_until(raw: str | None, tz: tzinfo | None) -> datetime | None:
    """Parse UNTIL. A trailing ``Z`` means UTC; otherwise the value is read in ``tz``."""
    if not raw:
        return None
    try:
        if "T" in raw:
            naive = datetime.strptime(raw.replace("Z", "")[:15], "%Y%m%dT%H%M%S")
            if raw.endswith("Z"):
                return naive.replace(tzinfo=timezone.utc).astimezone(tz)
            return naive.replace(tzinfo=tz)
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


_BYDAY_RE = re.compile(r"^([+-]?\d{1,2})?(MO|TU|WE|TH|FR|SA|SU)$")


def _month_days(year: int, month: int, start: datetime, rule: RRule) -> list[int]:
    """Days of the month an occurrence falls on, ascending."""
    last = calendar.monthrange(year, month)[1]
    days: set[int] = set()
    if rule.byday:
        for token in rule.byday.split(","):
            m = _BYDAY_RE.match(token.strip())
            if not m:
                continue
            weekday = WEEKDAYS[m.group(2)]
            matching = [d for d in range(1, last + 1) if calendar.weekday(year, month, d) == weekday]
            if m.group(1) is None:
                days.update(matching)
                continue
            n = int(m.group(1))
            if n != 0 and abs(n) <= len(matching):
                days.add(matching[n - 1] if n > 0 else matching[n])
    elif rule.bymonthday:
        for token in rule.bymonthday.split(","):
            n = _int(token.strip(), 0)
            if 1 <= n <= last:
                days.add(n)
            elif -last <= n <= -1:
                days.add(last + n + 1)
    elif start.day <= last:
        days.add(start.day)
    return sorted(days)


def _year_days(year: int, month: int, start: datetime, rule: RRule) -> list[int]:
    return [start.day] if start.day <= calendar.monthrange(year, month)[1] else []


def _expand_by_month(start: datetime, duration: timedelta, rule: RRule, until: datetime | None,
                     window_start: datetime, window_end: datetime, *,
                     step: int, days_of: Callable[[int, int, datetime, RRule], list[int]]) -> list[Instance]:
    """Walk periods of ``step`` months from DTSTART's month, emitting each period's days."""
    base = start.year * 12 + start.month - 1
    first = 0
    if rule.count is None:
        behind = window_start.year * 12 + window_start.month - 1 - base
        first = max(0, behind // step - 1)

    results: list[Instance] = []
    generated = 0
    k = first
    while True:
        index = base + k * step
        year, month = divmod(index, 12)
        month += 1
        if datetime(year, month, 1, tzinfo=start.tzinfo) > window_end:
            break
        for day in days_of(year, month, start, rule):
            inst = start.replace(year=year, month=month, day=day)
            if inst < start:
                continue
            if rule.count is not None and generated >= rule.count:
                return results
            if until and inst > until:
                return results
            if window_start <= inst <= window_end:
                results.append((inst, inst + duration))
            generated += 1
        k += 1
    return results


def _expand_monthly(start, duration, rule, until, window_start, window_end):
    return _expand_by_month(start, duration, rule, until, window_start, window_end,
                            step=rule.interval, days_of=_month_days)


def _expand_yearly(start, duration, rule, until, window_start, window_end):
    return _expand_by_month(start, duration, rule, until, window_start, window_end,
                            step=12 * rule.interval, days_of=_year_days)


def _expand_first_only(start: datetime, duration: timedelta, rule: RRule, until: datetime | None,
                       window_start: datetime, window_end: datetime) -> list[Instance]:
    if window_start <= start <= window_end:
        return [(start, start + duration)]
    return []


Expander = Callable[[datetime, timedelta, RRule, "datetime | None", datetime, datetime], list[Instance]]

EXPANDERS: dict[str, Expander] = {
    "DAILY": _expand_daily,
    "WEEKLY": _expand_weekly,
    "MONTHLY": _expand_monthly,
    "YEARLY": _expand_yearly,
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
