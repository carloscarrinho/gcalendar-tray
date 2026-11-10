"""Known bugs, preserved by the refactor and pinned here.

`strict = true` in pyproject makes these XPASS -> FAIL once fixed, so the
marker has to be removed together with the fix.
"""

from datetime import datetime, timedelta

import pytest

from gcal_tray.events import parse_events
from gcal_tray.models import Window
from gcal_tray.rrule import expand, parse_rrule

from conftest import FROZEN_NOW, LOCAL_TZ

WIN = Window(datetime(2026, 11, 9, tzinfo=LOCAL_TZ), datetime(2026, 11, 16, tzinfo=LOCAL_TZ))


def at(m, d, hh=9, mm=0, y=2026):
    return datetime(y, m, d, hh, mm, tzinfo=LOCAL_TZ)


def starts(start, rule):
    return [s for s, _ in expand(start, start + timedelta(hours=1), parse_rrule(rule), WIN.start, WIN.end)]


@pytest.mark.xfail(reason="UNTIL=...Z is read in the event's local tz instead of UTC")
def test_utc_until_is_utc():
    # UNTIL 11:00Z == 08:00 local, so the 09:00-local instance on Nov 11 is past UNTIL.
    assert starts(at(11, 10), "FREQ=DAILY;UNTIL=20261111T110000Z") == [at(11, 10)]


@pytest.mark.xfail(reason="ordinal BYDAY (2MO, -1FR) is ignored; MONTHLY shows only the first occurrence")
def test_monthly_ordinal_byday():
    # Second Monday of each month, from Oct 12 2026 -> Nov 9 2026.
    assert starts(at(10, 12), "FREQ=MONTHLY;BYDAY=2MO") == [at(11, 9)]


@pytest.mark.xfail(reason="MONTHLY is not expanded beyond DTSTART")
def test_monthly_by_monthday():
    assert starts(at(10, 12), "FREQ=MONTHLY") == [at(11, 12)]


@pytest.mark.xfail(reason="YEARLY is not expanded beyond DTSTART")
def test_yearly():
    assert starts(at(11, 10, y=2025), "FREQ=YEARLY") == [at(11, 10)]


@pytest.mark.xfail(reason="EXDATE is matched on its raw date string; TZID and time are ignored")
def test_exdate_honours_tzid():
    # 2026-11-11 00:00 Tokyo == 2026-11-10 12:00 local: the Nov 10 instance is the excluded one.
    text = ("BEGIN:VEVENT\nSUMMARY:Lunch\nDTSTART:20261109T150000Z\nDTEND:20261109T160000Z\n"
            "RRULE:FREQ=DAILY\nEXDATE;TZID=Asia/Tokyo:20261111T000000\nEND:VEVENT\n")
    days = [e.start.day for e in parse_events(text, "Cal", LOCAL_TZ, FROZEN_NOW, WIN)]
    assert days == [9, 11, 12, 13, 14, 15]
