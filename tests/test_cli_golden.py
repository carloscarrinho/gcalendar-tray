"""End-to-end characterization tests.

Each scenario runs the CLI with a frozen clock and compares stdout against
`tests/golden/<scenario>.json`. Goldens are stored pretty-printed for
readable diffs, but the comparison is byte-exact: re-serialising the golden
with default `json.dumps` must reproduce stdout exactly (key order, escaping).

Regenerate with:  UPDATE_GOLDEN=1 uv run pytest tests/test_cli_golden.py
"""

from __future__ import annotations

import json
import os

import pytest

from conftest import GOLDEN, fixture_path

MISSING_FEED = "file:///nonexistent/gcal-tray-test/feed.ics"

SCENARIOS: dict[str, list[str]] = {
    "single": [fixture_path("single.ics")],
    "allday": [fixture_path("allday.ics")],
    "tz_crlf": [fixture_path("tz_crlf.ics")],
    "recurring": [fixture_path("recurring.ics")],
    "active": [fixture_path("active.ics")],
    "active_compact": ["--compact", fixture_path("active.ics")],
    "soon": [fixture_path("soon.ics")],
    "within_hour": [fixture_path("within_hour.ics")],
    "tomorrow_only": [fixture_path("tomorrow_only.ics")],
    "empty": [fixture_path("empty.ics")],
    "multi_dedupe": [fixture_path("single.ics"), fixture_path("single.ics"), fixture_path("recurring.ics")],
    "partial_error": [fixture_path("within_hour.ics"), MISSING_FEED],
    "all_error": [MISSING_FEED],
    "unknown_flag_ignored": ["--verbose", fixture_path("soon.ics")],
}


def _check(name: str, stdout: str) -> None:
    golden = GOLDEN / f"{name}.json"
    if os.environ.get("UPDATE_GOLDEN"):
        golden.write_text(json.dumps(json.loads(stdout), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    expected = json.loads(golden.read_text(encoding="utf-8"))
    assert stdout == json.dumps(expected) + "\n"


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_golden_cli_args(run_cli, name):
    _check(name, run_cli(SCENARIOS[name]))


def test_golden_not_configured(run_cli):
    _check("not_configured", run_cli([]))


def test_golden_config_file(run_cli, tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "calendars": [
            {"name": "Work", "url": fixture_path("single.ics"), "color": "#f00"},
            fixture_path("recurring.ics"),
        ]
    }))
    _check("config_file", run_cli([], config=config))
