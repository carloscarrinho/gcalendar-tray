from datetime import timedelta

import pytest

from gcal_tray.timefmt import format_relative

M = timedelta(minutes=1)


def rel(now, start_offset_min, duration_min=30):
    start = now + start_offset_min * M
    return format_relative(start, start + duration_min * M, now)


def test_happening_now(now):
    r = rel(now, -10, 25)
    assert r == ("Now (ends in 15m)", True, 15)


def test_now_reports_at_least_one_minute(now):
    start = now - 30 * M
    assert format_relative(start, now + timedelta(seconds=20), now).minutes == 1


def test_ended(now):
    assert rel(now, -60, 30) == ("Ended", False, 0)


@pytest.mark.parametrize(("offset", "text"), [(0.5, "In 0m"), (1, "In 1m"), (59, "In 59m")])
def test_minutes(now, offset, text):
    assert rel(now, offset).text == text


@pytest.mark.parametrize(
    ("offset", "text"),
    [(60, "In 1h"), (61, "In 1h 1m"), (239, "In 3h 59m"), (240, "Today at 14:00"), (13 * 60 + 59, "Today at 23:59")],
)
def test_same_day(now, offset, text):
    assert rel(now, offset).text == text


def test_midnight_is_tomorrow(now):
    r = rel(now, 14 * 60)  # 00:00 next day
    assert r.text == "Tomorrow 00:00"
    assert r.minutes == 840


def test_later_this_week(now):
    assert rel(now, 2 * 24 * 60).text == "Wed 11 Nov 10:00"
