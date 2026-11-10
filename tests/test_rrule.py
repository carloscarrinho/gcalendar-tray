from datetime import datetime, timedelta

from gcal_tray.rrule import RRule, expand, parse_rrule, parse_until

from conftest import LOCAL_TZ

H = timedelta(hours=1)
WIN_START = datetime(2026, 11, 9, tzinfo=LOCAL_TZ)  # Monday
WIN_END = WIN_START + timedelta(days=7)


def at(y, m, d, hh=9, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=LOCAL_TZ)


def starts(start, rule, duration=H):
    return [s for s, _ in expand(start, start + duration, rule, WIN_START, WIN_END)]


def test_parse_rrule():
    assert parse_rrule("FREQ=WEEKLY;INTERVAL=2;COUNT=4;UNTIL=20261231T000000Z;BYDAY=MO,FR;WKST=SU") == RRule(
        freq="WEEKLY", interval=2, count=4, until="20261231T000000Z", byday="MO,FR")


def test_parse_rrule_defaults_and_bad_numbers():
    assert parse_rrule("FREQ=DAILY") == RRule(freq="DAILY")
    assert parse_rrule("FREQ=DAILY;INTERVAL=0").interval == 1
    assert parse_rrule("FREQ=DAILY;INTERVAL=x").interval == 1


def test_parse_until():
    assert parse_until("20261110", LOCAL_TZ) == datetime(2026, 11, 10, tzinfo=LOCAL_TZ)
    assert parse_until("20261110T120000", LOCAL_TZ) == datetime(2026, 11, 10, 12, tzinfo=LOCAL_TZ)
    assert parse_until("bogus", LOCAL_TZ) is None
    assert parse_until(None, LOCAL_TZ) is None


class TestNoRule:
    def test_overlapping_window(self):
        assert starts(at(2026, 11, 10), None) == [at(2026, 11, 10)]

    def test_outside_window(self):
        assert starts(at(2026, 11, 20), None) == []
        assert starts(at(2026, 11, 1), None) == []

    def test_multi_day_event_started_before_window_overlaps(self):
        start = at(2026, 11, 8, 20)
        assert expand(start, start + 10 * H, None, WIN_START, WIN_END) == [(start, start + 10 * H)]


class TestDaily:
    def test_unbounded_from_far_past_skips_ahead(self):
        got = starts(at(2026, 1, 1), parse_rrule("FREQ=DAILY"))
        assert got == [at(2026, 11, d) for d in range(9, 16)]

    def test_interval(self):
        got = starts(at(2026, 11, 7), parse_rrule("FREQ=DAILY;INTERVAL=3"))
        assert got == [at(2026, 11, 10), at(2026, 11, 13)]

    def test_count_counts_occurrences_before_window(self):
        got = starts(at(2026, 11, 7), parse_rrule("FREQ=DAILY;INTERVAL=2;COUNT=3"))
        assert got == [at(2026, 11, 9), at(2026, 11, 11)]

    def test_count_exhausted_long_ago(self):
        assert starts(at(2024, 1, 1), parse_rrule("FREQ=DAILY;COUNT=10")) == []

    def test_until_inside_window(self):
        got = starts(at(2026, 11, 1), parse_rrule("FREQ=DAILY;UNTIL=20261111T090000"))
        assert got == [at(2026, 11, 9), at(2026, 11, 10), at(2026, 11, 11)]

    def test_until_before_window(self):
        assert starts(at(2025, 1, 1), parse_rrule("FREQ=DAILY;UNTIL=20250201")) == []

    def test_duration_preserved(self):
        start = at(2026, 11, 1)
        inst = expand(start, start + 15 * timedelta(minutes=1), parse_rrule("FREQ=DAILY"), WIN_START, WIN_END)
        assert all(e - s == timedelta(minutes=15) for s, e in inst)


class TestWeekly:
    def test_defaults_to_dtstart_weekday(self):
        assert starts(at(2026, 1, 7), parse_rrule("FREQ=WEEKLY")) == [at(2026, 11, 11)]

    def test_byday(self):
        got = starts(at(2026, 1, 5, 18, 30), parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE,FR"))
        assert got == [at(2026, 11, 9, 18, 30), at(2026, 11, 11, 18, 30), at(2026, 11, 13, 18, 30)]

    def test_interval_from_far_past_keeps_phase(self):
        # Mondays every 2 weeks from 2026-01-05: Nov 9 is on-phase (44 weeks later).
        assert starts(at(2026, 1, 5), parse_rrule("FREQ=WEEKLY;INTERVAL=2")) == [at(2026, 11, 9)]
        # From 2026-01-12, Nov 9 is off-phase and Nov 16 is outside the window.
        assert starts(at(2026, 1, 12), parse_rrule("FREQ=WEEKLY;INTERVAL=2")) == []

    def test_instances_before_dtstart_skipped(self):
        got = starts(at(2026, 11, 11), parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE,FR"))
        assert got == [at(2026, 11, 11), at(2026, 11, 13)]

    def test_count(self):
        got = starts(at(2026, 11, 2), parse_rrule("FREQ=WEEKLY;BYDAY=MO,TU;COUNT=3"))
        assert got == [at(2026, 11, 9)]

    def test_count_expired_years_ago(self):
        assert starts(at(2023, 1, 2), parse_rrule("FREQ=WEEKLY;COUNT=10")) == []

    def test_until(self):
        got = starts(at(2026, 11, 2), parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=20261111T235959"))
        assert got == [at(2026, 11, 9), at(2026, 11, 11)]

    def test_only_unknown_byday_tokens_yields_nothing_without_crashing(self):
        assert starts(at(2026, 11, 2), parse_rrule("FREQ=WEEKLY;BYDAY=XX;COUNT=3")) == []


class TestOtherFreq:
    def test_unknown_freq_first_occurrence_in_window(self):
        assert starts(at(2026, 11, 10), parse_rrule("FREQ=MONTHLY")) == [at(2026, 11, 10)]

    def test_unknown_freq_first_occurrence_outside_window(self):
        assert starts(at(2026, 10, 10), parse_rrule("FREQ=YEARLY")) == []

    def test_missing_freq(self):
        assert starts(at(2026, 11, 10), parse_rrule("INTERVAL=2")) == [at(2026, 11, 10)]
