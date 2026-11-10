"""Shared fixtures: deterministic local timezone, frozen clock, fixture paths."""

from __future__ import annotations

import io
import os
import time
from datetime import datetime
from pathlib import Path

import pytest

# Pin the process-local timezone *before* anything reads it, so
# `datetime.now().astimezone()` is deterministic. Sao Paulo has no DST.
os.environ["TZ"] = "America/Sao_Paulo"
time.tzset()

TESTS_DIR = Path(__file__).parent
FIXTURES = TESTS_DIR / "fixtures"
GOLDEN = TESTS_DIR / "golden"

# Monday 2026-11-09 10:00 local (-03:00).
FROZEN_NAIVE = datetime(2026, 11, 9, 10, 0, 0)
FROZEN_NOW = FROZEN_NAIVE.astimezone()
LOCAL_TZ = FROZEN_NOW.tzinfo


def fixture_path(name: str) -> str:
    return str(FIXTURES / name)


@pytest.fixture
def now() -> datetime:
    return FROZEN_NOW


@pytest.fixture
def local_tz():
    return LOCAL_TZ


@pytest.fixture
def run_cli(tmp_path):
    """Run the CLI end to end with a frozen clock and an isolated config path.

    Returns stdout as a string. This is the single seam golden tests go
    through, so the refactor only has to change this helper.
    """

    def _run(argv: list[str], config: Path | None = None) -> str:
        from gcal_tray import cli

        out = io.StringIO()
        cli.main(
            argv,
            now=FROZEN_NOW,
            config_path=config or (tmp_path / "missing-config.json"),
            out=out,
        )
        return out.getvalue()

    return _run
