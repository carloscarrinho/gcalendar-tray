import json

import pytest

from gcal_tray.config import load_calendar_configs, parse_config
from gcal_tray.models import CalendarSource as S


def test_calendars_mixed_strings_and_objects():
    data = {"calendars": [
        " https://a ",
        {"name": "Work", "url": "https://b ", "color": "#f00"},
        {"url": "https://c"},
        {"name": "No url"},
        "",
        42,
    ]}
    assert parse_config(data) == [S("Cal 1", "https://a"), S("Work", "https://b", "#f00"), S("Cal 3", "https://c")]


def test_calendars_wins_over_other_keys():
    assert parse_config({"calendars": ["https://a"], "ical_url": "https://x"}) == [S("Cal 1", "https://a")]


def test_non_list_calendars_falls_through():
    assert parse_config({"calendars": "nope", "ical_urls": ["https://a"]}) == [S("Cal 1", "https://a")]


def test_ical_urls():
    assert parse_config({"ical_urls": ["https://a", "  ", "https://b"]}) == [S("Cal 1", "https://a"), S("Cal 3", "https://b")]


def test_ical_url_single_is_named_calendar():
    assert parse_config({"ical_url": " https://a "}) == [S("Calendar", "https://a")]


def test_ical_url_comma_separated():
    assert parse_config({"ical_url": "https://a, ,https://b"}) == [S("Cal 1", "https://a"), S("Cal 2", "https://b")]


@pytest.mark.parametrize("data", [{}, {"ical_url": "  "}, [], "x", None, {"calendars": []}])
def test_empty(data):
    assert parse_config(data) == []


def test_load_missing_file_is_not_an_error(tmp_path):
    r = load_calendar_configs(tmp_path / "nope.json")
    assert r.sources == [] and r.errors == []


def test_load_valid(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"ical_url": "https://a"}))
    r = load_calendar_configs(p)
    assert r.sources == [S("Calendar", "https://a")] and r.errors == []


def test_load_invalid_json_reports_error(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("{not json")
    r = load_calendar_configs(p)
    assert r.sources == []
    assert len(r.errors) == 1 and r.errors[0].startswith("Config: invalid JSON in ")


def test_load_non_object_reports_error(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("[]")
    assert load_calendar_configs(p).errors == [f"Config: expected a JSON object in {p}"]


def test_load_unreadable_reports_error(tmp_path):
    assert load_calendar_configs(tmp_path).errors[0].startswith("Config: cannot read ")
