"""Minimal RFC 5545 helpers: line normalisation, VEVENT blocks, properties, dates."""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import datetime, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_VEVENT_RE = re.compile(r"BEGIN:VEVENT(.*?)END:VEVENT", re.DOTALL)
_FOLD_RE = re.compile(r"\n[ \t]")


def normalize(text: str) -> str:
    """Convert CRLF/CR line endings to LF and unfold continuation lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return _FOLD_RE.sub("", text)


def iter_vevents(text: str) -> Iterator[str]:
    """Yield the body of every VEVENT block in already-normalised text."""
    for m in _VEVENT_RE.finditer(text):
        yield m.group(1)


def extract_prop(block: str, name: str) -> tuple[str | None, str | None]:
    """Return ``(params, value)`` for the first ``NAME[;params]:value`` line in a block."""
    m = re.search(r"^" + re.escape(name) + r"(?:;([^:\n]*))?:([^\n]*)$", block, re.MULTILINE)
    if not m:
        return None, None
    return m.group(1), m.group(2).strip()


def unescape(s: str | None) -> str:
    if not s:
        return ""
    return (
        s.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def parse_params(params: str | None) -> dict[str, str]:
    """Parse ``TZID="X";VALUE=DATE`` into a dict (quotes stripped from values)."""
    out: dict[str, str] = {}
    if not params:
        return out
    for param in params.split(";"):
        if "=" in param:
            key, val = param.split("=", 1)
            out[key] = val.strip('"')  # last occurrence wins
    return out


def _resolve_tz(params: str | None, fallback: tzinfo) -> tzinfo:
    tz_name = parse_params(params).get("TZID")
    if not tz_name:
        return fallback
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return fallback


def parse_ical_date(params: str | None, val: str | None, local_tz: tzinfo) -> tuple[datetime | None, bool]:
    """Parse a DTSTART/DTEND value into a local-tz datetime.

    Returns ``(dt, is_all_day)``; ``dt`` is None when the value is unparseable.
    """
    if not val:
        return None, False
    val = val.strip()

    # All-day: YYYYMMDD
    if len(val) == 8 and val.isdigit():
        try:
            d = datetime.strptime(val, "%Y%m%d")
        except ValueError:
            return None, False
        return datetime(d.year, d.month, d.day, tzinfo=local_tz), True

    try:
        # UTC: YYYYMMDDTHHMMSSZ
        if val.endswith("Z"):
            dt = datetime.strptime(val[:-1][:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
            return dt.astimezone(local_tz), False

        # Floating or TZID-qualified: YYYYMMDDTHHMMSS
        dt = datetime.strptime(val[:15], "%Y%m%dT%H%M%S").replace(tzinfo=_resolve_tz(params, local_tz))
        return dt.astimezone(local_tz), False
    except ValueError:
        return None, False


def parse_exdates(raw: str | None) -> set[str]:
    """Return the ``YYYYMMDD`` dates listed in an EXDATE value.

    Matching is by calendar date only (time and TZID are ignored).
    """
    out: set[str] = set()
    if not raw:
        return out
    for ex in raw.split(","):
        ex_clean = ex.strip().replace("Z", "")
        if len(ex_clean) >= 8:
            out.add(ex_clean[:8])
    return out
