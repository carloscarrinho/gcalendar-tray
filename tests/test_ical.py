from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from gcal_tray import ical


def test_normalize_crlf_and_cr():
    assert ical.normalize("A\r\nB\rC\n") == "A\nB\nC\n"


def test_normalize_unfolds_space_and_tab_continuations():
    assert ical.normalize("SUMMARY:Hel\r\n lo\r\n\tworld\r\nX:1") == "SUMMARY:Helloworld\nX:1"


def test_iter_vevents():
    text = "BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:1\nEND:VEVENT\nBEGIN:VEVENT\nUID:2\nEND:VEVENT\n"
    assert [b.strip() for b in ical.iter_vevents(text)] == ["UID:1", "UID:2"]


def test_extract_prop_with_and_without_params():
    block = "\nDTSTART;TZID=Europe/London:20261109T190000\nSUMMARY: Hi \n"
    assert ical.extract_prop(block, "DTSTART") == ("TZID=Europe/London", "20261109T190000")
    assert ical.extract_prop(block, "SUMMARY") == (None, "Hi")
    assert ical.extract_prop(block, "LOCATION") == (None, None)


def test_extract_prop_needs_exact_name():
    assert ical.extract_prop("\nSUMMARYX:nope\n", "SUMMARY") == (None, None)


def test_unescape():
    assert ical.unescape(r"a\, b\; c\nd\Ne\\f") == "a, b; c\nd\ne\\f"
    assert ical.unescape(None) == ""


def test_parse_params():
    assert ical.parse_params('TZID="America/New_York";VALUE=DATE-TIME') == {
        "TZID": "America/New_York", "VALUE": "DATE-TIME"}
    assert ical.parse_params(None) == {}


def test_all_day(local_tz):
    assert ical.parse_ical_date("VALUE=DATE", "20261109", local_tz) == (datetime(2026, 11, 9, tzinfo=local_tz), True)


def test_utc_converted_to_local(local_tz):
    dt, all_day = ical.parse_ical_date(None, "20261109T170000Z", local_tz)
    assert not all_day
    assert dt == datetime(2026, 11, 9, 17, tzinfo=timezone.utc)
    assert dt.tzinfo is local_tz and dt.hour == 14


def test_tzid(local_tz):
    dt, _ = ical.parse_ical_date("TZID=Europe/London", "20261109T190000", local_tz)
    assert dt == datetime(2026, 11, 9, 19, tzinfo=ZoneInfo("Europe/London"))
    assert dt.hour == 16


def test_quoted_tzid(local_tz):
    dt, _ = ical.parse_ical_date('TZID="America/New_York"', "20261111T080000", local_tz)
    assert dt.hour == 10


@pytest.mark.parametrize("tzid", ["Not/AZone", "../etc/passwd", ""])
def test_invalid_tzid_falls_back_to_local(local_tz, tzid):
    dt, _ = ical.parse_ical_date(f"TZID={tzid}", "20261110T150000", local_tz)
    assert dt == datetime(2026, 11, 10, 15, tzinfo=local_tz)


def test_floating_time_is_local(local_tz):
    dt, _ = ical.parse_ical_date(None, "20261110T150000", local_tz)
    assert dt == datetime(2026, 11, 10, 15, tzinfo=local_tz)


@pytest.mark.parametrize("val", [None, "", "garbage", "2026-11-09", "20261399", "20261399T250000Z"])
def test_unparseable(local_tz, val):
    assert ical.parse_ical_date(None, val, local_tz) == (None, False)


def test_parse_exdates_instants_and_dates(local_tz):
    block = ("EXDATE:20261111T093000Z, 20261113T213000\n"
             "EXDATE;TZID=Asia/Tokyo:20261112T000000\n"
             "EXDATE;VALUE=DATE:20261120\n")
    instants, days = ical.parse_exdates(block, local_tz)
    assert {dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M") for dt in instants} == {
        "20261111T0930", "20261114T0030", "20261111T1500"}
    assert days == {date(2026, 11, 20)}


def test_parse_exdates_none(local_tz):
    assert ical.parse_exdates("SUMMARY:x\n", local_tz) == (set(), set())
