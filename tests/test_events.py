from datetime import datetime, timedelta

import pytest

from gcal_tray.events import dedupe, parse_events
from gcal_tray.models import Event, Window

from conftest import FIXTURES, FROZEN_NOW, LOCAL_TZ

WINDOW = Window(datetime(2026, 11, 9, tzinfo=LOCAL_TZ), datetime(2026, 11, 16, tzinfo=LOCAL_TZ))


def cal(*vevents: str) -> str:
    body = "".join(f"BEGIN:VEVENT\n{v.strip()}\nEND:VEVENT\n" for v in vevents)
    return f"BEGIN:VCALENDAR\n{body}END:VCALENDAR\n"


def parse(text, name="Cal"):
    return parse_events(text, name, LOCAL_TZ, FROZEN_NOW, WINDOW)


def at(d, hh, mm=0):
    return datetime(2026, 11, d, hh, mm, tzinfo=LOCAL_TZ)


def test_basic_fields():
    [ev] = parse(cal("""
SUMMARY:Planning\\, Q4
DTSTART:20261109T170000Z
DTEND:20261109T180000Z
LOCATION:Room 1
DESCRIPTION:https://meet.google.com/abc-defg-hij
"""), name="Work")
    assert ev == Event("Work", "Planning, Q4", at(9, 14), at(9, 15), False, "Google Meet",
                       "https://meet.google.com/abc-defg-hij", "Room 1", "https://meet.google.com/abc-defg-hij")


def test_cancelled_skipped():
    assert parse(cal("STATUS:cancelled\nSUMMARY:x\nDTSTART:20261109T170000Z")) == []


def test_missing_or_bad_dtstart_skipped():
    assert parse(cal("SUMMARY:x")) == []
    assert parse(cal("SUMMARY:x\nDTSTART:garbage")) == []


def test_untitled():
    [ev] = parse(cal("DTSTART:20261109T170000Z"))
    assert ev.title == "Untitled Event"


def test_missing_dtend_defaults_30_minutes():
    [ev] = parse(cal("DTSTART:20261109T170000Z"))
    assert ev.end - ev.start == timedelta(minutes=30)


def test_missing_dtend_all_day_defaults_one_day():
    [ev] = parse(cal("DTSTART;VALUE=DATE:20261110"))
    assert ev.is_all_day and ev.end - ev.start == timedelta(days=1)


def test_unparseable_dtend_falls_back_to_30_minutes():
    [ev] = parse(cal("DTSTART:20261109T170000Z\nDTEND:nope"))
    assert ev.end - ev.start == timedelta(minutes=30)


def test_ended_instances_dropped():
    assert parse(cal("DTSTART:20261109T110000Z\nDTEND:20261109T130000Z")) == []  # ends exactly at now


def test_exdate_filters_by_local_date():
    evs = parse(cal("DTSTART:20261109T200000Z\nDTEND:20261109T210000Z\nRRULE:FREQ=DAILY\n"
                    "EXDATE:20261110T200000Z,20261112T200000Z"))
    assert [e.start.day for e in evs] == [9, 11, 13, 14, 15]


def test_description_truncated():
    [ev] = parse(cal("DTSTART:20261109T170000Z\nDESCRIPTION:" + "x" * 400))
    assert len(ev.description) == 300


def test_meeting_link_found_in_title():
    [ev] = parse(cal("SUMMARY:Sync https://whereby.com/abc\nDTSTART:20261109T170000Z"))
    assert ev.call_type == "Whereby"


def test_crlf_fixture_unfolds_and_unescapes():
    evs = parse((FIXTURES / "tz_crlf.ics").read_text(encoding="utf-8"))
    assert evs[0].title == "Planning, Q4 ; budget\nreview"
    assert evs[0].location == "Room 4, 2nd floor"
    assert evs[0].call_url == "https://acme.webex.com/meet/jdoe"
    assert evs[2].call_type == "Whereby"


def ev(title, start, end=None, cal_name="A"):
    return Event(cal_name, title, start, end or start + timedelta(hours=1), False)


def test_dedupe_sorts_and_drops_same_title_and_start():
    a = ev("Sync", at(9, 14), cal_name="A")
    b = ev(" sync ", at(9, 14), cal_name="B")
    c = ev("Sync", at(9, 15))
    d = ev("Other", at(9, 14))
    early = ev("Early", at(9, 11))
    assert dedupe([c, a, d, b, early]) == [early, a, d, c]


@pytest.mark.parametrize("n", [0, 1])
def test_dedupe_trivial(n):
    evs = [ev("x", at(9, 14))][:n]
    assert dedupe(evs) == evs
