from dataclasses import replace

import pytest

from gcal_tray.agenda import Agenda, AgendaItem
from gcal_tray.render import (MAX_UPCOMING, build_payload, not_configured_payload, render_bar,
                              render_tooltip, truncate_title)

from conftest import FROZEN_NOW

BASE = AgendaItem(
    calendar_name="Work", title="Sync", start_str="14:00", end_str="15:00", date_str="Mon, Nov 09",
    relative="Today at 14:00", is_now=False, minutes_away=240, is_all_day=False,
    call_type="", call_url="", location="",
)


def item(**kw):
    return replace(BASE, **kw)


@pytest.mark.parametrize(
    ("title", "expected"),
    [("x" * 22, "x" * 22), ("x" * 23, "x" * 20 + "…"), ("", "")],
)
def test_truncate_title(title, expected):
    assert truncate_title(title) == expected


def test_bar_no_focus():
    assert render_bar(None) == ("No more events today", False)


def test_bar_now():
    long = item(title="Sprint sync with the whole team", is_now=True)
    assert render_bar(long) == ("🔴 Sprint sync with the… (Now)", True)
    assert render_bar(long, compact=True) == ("🔴 Now", True)


@pytest.mark.parametrize(
    ("minutes", "text", "urgent"),
    [(0, "🕒 In 0m: Sync", True), (5, "🕒 In 5m: Sync", True), (6, "🕒 In 6m: Sync", False),
     (59, "🕒 In 59m: Sync", False), (60, "🕒 14:00 Sync", False)],
)
def test_bar_countdown_thresholds(minutes, text, urgent):
    assert render_bar(item(minutes_away=minutes)) == (text, urgent)


def test_bar_compact_only_affects_now():
    assert render_bar(item(minutes_away=3), compact=True) == ("🕒 In 3m: Sync", True)


def test_bar_all_day_never_counts_down():
    assert render_bar(item(is_all_day=True, start_str="All Day", minutes_away=2)) == ("🕒 All Day Sync", False)


def test_tooltip_full():
    focus = item(call_url="https://z", call_type="Zoom")
    assert render_tooltip(focus) == "Sync\n14:00 - 15:00 (Today at 14:00)\nVideo: Zoom\nCalendar: Work"


def test_tooltip_minimal():
    assert render_tooltip(item(calendar_name="")) == "Sync\n14:00 - 15:00 (Today at 14:00)"


def test_tooltip_appends_errors():
    assert render_tooltip(None, ["A: boom", "B: bang"]) == (
        "No more events scheduled for today\nSync notices:\nA: boom\nB: bang")


def test_payload_shape_and_truncation():
    agenda = Agenda(today=[BASE], upcoming=[BASE] * 12, focus=BASE, has_events=True)
    p = build_payload(agenda, errors=["X: e"], ok=True, calendar_count=2, now=FROZEN_NOW)
    assert list(p) == ["ok", "configured", "bar_text", "bar_urgent", "tooltip", "has_events", "focus_event",
                       "today_events", "upcoming_events", "errors", "calendar_count", "updated_at"]
    assert len(p["upcoming_events"]) == MAX_UPCOMING
    assert p["focus_event"] == BASE.to_dict()
    assert p["updated_at"] == "10:00" and p["configured"] is True and p["errors"] == ["X: e"]


def test_payload_without_focus():
    p = build_payload(Agenda([], [], None, False), errors=[], ok=True, calendar_count=1, now=FROZEN_NOW)
    assert p["focus_event"] is None and p["bar_text"] == "No more events today"


def test_not_configured():
    p = not_configured_payload(FROZEN_NOW, ["Config: invalid JSON"])
    assert p["configured"] is False and p["bar_text"] == "Set Calendar URL"
    assert p["errors"] == ["Config: invalid JSON"] and "calendar_count" not in p
