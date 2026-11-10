"""Recurrence behaviour that used to be wrong: UTC UNTIL, MONTHLY/YEARLY, ordinal BYDAY, EXDATE tz."""

from datetime import datetime, timedelta

from gcal_tray.events import parse_events
from gcal_tray.models import Window
from gcal_tray.rrule import expand, parse_rrule

from conftest import FROZEN_NOW, LOCAL_TZ

WIN = Window(datetime(2026, 11, 9, tzinfo=LOCAL_TZ), datetime(2026, 11, 16, tzinfo=LOCAL_TZ))


def at(m, d, hh=9, mm=0, y=2026):
    return datetime(y, m, d, hh, mm, tzinfo=LOCAL_TZ)


def starts(start, rule):
    return [s for s, _ in expand(start, start + timedelta(hours=1), parse_rrule(rule), WIN.start, WIN.end)]


def test_utc_until_is_utc():
    # UNTIL 11:00Z == 08:00 local, so the 09:00-local instance on Nov 11 is past UNTIL.
    assert starts(at(11, 10), "FREQ=DAILY;UNTIL=20261111T110000Z") == [at(11, 10)]


def test_monthly_ordinal_byday():
    # Second Monday of each month, from Oct 12 2026 -> Nov 9 2026.
    assert starts(at(10, 12), "FREQ=MONTHLY;BYDAY=2MO") == [at(11, 9)]


def test_monthly_same_day():
    assert starts(at(10, 12), "FREQ=MONTHLY") == [at(11, 12)]


def test_yearly():
    assert starts(at(11, 10, y=2025), "FREQ=YEARLY") == [at(11, 10)]


def test_exdate_honours_tzid():
    # 2026-11-11 00:00 Tokyo == 2026-11-10 12:00 local: the Nov 10 instance is the excluded one.
    text = ("BEGIN:VEVENT\nSUMMARY:Lunch\nDTSTART:20261109T150000Z\nDTEND:20261109T160000Z\n"
            "RRULE:FREQ=DAILY\nEXDATE;TZID=Asia/Tokyo:20261111T000000\nEND:VEVENT\n")
    days = [e.start.day for e in parse_events(text, "Cal", LOCAL_TZ, FROZEN_NOW, WIN)]
    assert days == [9, 11, 12, 13, 14, 15]


def test_monthly_skips_months_without_the_day():
    assert starts(at(1, 31), "FREQ=MONTHLY") == []  # Feb..Nov: only the 31st-bearing months, none in window


def test_monthly_last_friday_and_negative_monthday():
    assert starts(at(10, 1), "FREQ=MONTHLY;BYDAY=-1FR") == []
    assert starts(at(10, 1), "FREQ=MONTHLY;BYMONTHDAY=-20") == [at(11, 11)]


def test_monthly_interval_and_count():
    assert starts(at(9, 12), "FREQ=MONTHLY;INTERVAL=2") == [at(11, 12)]
    assert starts(at(9, 12), "FREQ=MONTHLY;COUNT=2") == []
    assert starts(at(9, 12), "FREQ=MONTHLY;COUNT=3") == [at(11, 12)]


def test_monthly_until_stops_series():
    assert starts(at(10, 12), "FREQ=MONTHLY;UNTIL=20261111T000000") == []


def test_yearly_leap_day_skipped_off_leap_years():
    assert starts(at(2, 29, y=2024), "FREQ=YEARLY") == []
