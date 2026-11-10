from datetime import datetime, timedelta

from gcal_tray.agenda import build_agenda, to_item
from gcal_tray.models import Event

from conftest import FROZEN_NOW, LOCAL_TZ

H = timedelta(hours=1)


def at(d, hh, mm=0):
    return datetime(2026, 11, d, hh, mm, tzinfo=LOCAL_TZ)


def ev(title, start, end=None, all_day=False):
    return Event("Cal", title, start, end or start + H, all_day)


def titles(items):
    return [i.title for i in items]


def test_to_item_timed():
    item = to_item(Event("Work", "Sync", at(9, 14), at(9, 15), False, "Zoom", "https://z", "Room"), FROZEN_NOW)
    assert item.to_dict() == {
        "calendar_name": "Work", "title": "Sync", "start_str": "14:00", "end_str": "15:00",
        "date_str": "Mon, Nov 09", "relative": "Today at 14:00", "is_now": False, "minutes_away": 240,
        "is_all_day": False, "call_type": "Zoom", "call_url": "https://z", "location": "Room",
    }


def test_to_item_all_day():
    item = to_item(ev("Holiday", at(10, 0), at(11, 0), all_day=True), FROZEN_NOW)
    assert (item.start_str, item.end_str, item.date_str) == ("All Day", "", "Tue, Nov 10")


def test_empty():
    a = build_agenda([], FROZEN_NOW)
    assert (a.today, a.upcoming, a.focus, a.has_events) == ([], [], None, False)


def test_active_beats_next():
    a = build_agenda([ev("Active", at(9, 9, 30)), ev("Later", at(9, 12))], FROZEN_NOW)
    assert a.focus.title == "Active" and a.focus.is_now


def test_next_today_when_nothing_active():
    a = build_agenda([ev("Later", at(9, 12)), ev("Later2", at(9, 13))], FROZEN_NOW)
    assert a.focus.title == "Later"


def test_all_day_excluded_from_next_but_not_from_active():
    upcoming_all_day = ev("Conf", at(9, 0) + 2 * timedelta(days=1), all_day=True)
    a = build_agenda([upcoming_all_day, ev("Timed", at(9, 15))], FROZEN_NOW)
    assert a.focus.title == "Timed"

    ongoing_all_day = ev("Holiday", at(9, 0), at(10, 0), all_day=True)
    a = build_agenda([ongoing_all_day, ev("Timed", at(9, 15))], FROZEN_NOW)
    assert a.focus.title == "Holiday"


def test_tomorrow_never_focus():
    a = build_agenda([ev("Tomorrow", at(10, 9))], FROZEN_NOW)
    assert a.focus is None and titles(a.upcoming) == ["Tomorrow"] and a.has_events


def test_multi_day_event_started_yesterday_counts_as_today():
    a = build_agenda([ev("Overnight", at(8, 22), at(9, 11)), ev("Fri", at(13, 9))], FROZEN_NOW)
    assert titles(a.today) == ["Overnight"] and titles(a.upcoming) == ["Fri"]
    assert a.focus.title == "Overnight"


def test_upcoming_not_truncated_here():
    evs = [ev(f"E{i}", at(10, 0) + i * H) for i in range(15)]
    assert len(build_agenda(evs, FROZEN_NOW).upcoming) == 15
