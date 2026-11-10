import io
import json
import subprocess
import sys

from gcal_tray import cli
from gcal_tray.models import FetchResult

from conftest import FIXTURES, FROZEN_NOW, TESTS_DIR, fixture_path

REPO = TESTS_DIR.parent


def test_parse_args():
    a = cli.parse_args(["--verbose", "a.ics", "--compact", "-x", "b"])
    assert a.compact is True and a.urls == ["a.ics", "-x", "b"]
    assert cli.parse_args([]) == cli.Args(False, [])


def test_agenda_window():
    w = cli.agenda_window(FROZEN_NOW)
    assert w.start.hour == 0 and (w.end - w.start).days == cli.WINDOW_DAYS and w.start.tzinfo is FROZEN_NOW.tzinfo


def test_injected_fetcher_receives_sources():
    seen = []

    def fetcher(sources):
        seen.extend(sources)
        return [FetchResult(s.name, content=(FIXTURES / "soon.ics").read_text()) for s in sources]

    p = cli.run(["https://a", "https://b"], now=FROZEN_NOW, fetcher=fetcher)
    assert [(s.name, s.url) for s in seen] == [("Cal 1", "https://a"), ("Cal 2", "https://b")]
    assert p["calendar_count"] == 2 and len(p["today_events"]) == 1  # deduped across feeds


def test_feed_with_empty_content_counts_as_neither_ok_nor_error():
    p = cli.run(["x"], now=FROZEN_NOW, fetcher=lambda s: [FetchResult("Cal 1", content="")])
    assert p["ok"] is True and p["errors"] == [] and p["has_events"] is False


def test_invalid_config_reported_in_not_configured_payload(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text("{oops")
    p = cli.run([], now=FROZEN_NOW, config_path=cfg, fetcher=lambda s: [])
    assert p["configured"] is False
    assert len(p["errors"]) == 1 and p["errors"][0].startswith("Config: invalid JSON")


def test_main_writes_single_json_line():
    out = io.StringIO()
    cli.main([fixture_path("soon.ics")], now=FROZEN_NOW, out=out)
    assert out.getvalue().count("\n") == 1
    assert json.loads(out.getvalue())["bar_text"] == "🕒 In 4m: Quick huddle"


def test_shim_runs_with_isolated_system_python():
    """calendar_fetch.py must work as Service.qml runs it: plain python3, no venv, any cwd."""
    proc = subprocess.run(
        [sys.executable, "-I", "-S", str(REPO / "calendar_fetch.py"), fixture_path("empty.ics")],
        capture_output=True, text=True, cwd="/", timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    data = json.loads(proc.stdout)
    assert data["configured"] is True and data["calendar_count"] == 1
