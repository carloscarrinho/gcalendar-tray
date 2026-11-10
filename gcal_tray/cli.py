"""Entry point: config -> fetch -> parse -> agenda -> render -> JSON on stdout.

The only module that reads argv, the clock and stdout. Everything it calls
is either pure or takes its I/O as an injectable argument.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TextIO

from .agenda import build_agenda
from .config import CONFIG_PATH, load_calendar_configs
from .events import dedupe, parse_events
from .fetch import fetch_all
from .models import CalendarSource, Event, FetchResult, Window
from .render import build_payload, not_configured_payload

WINDOW_DAYS = 7

Fetcher = Callable[[Sequence[CalendarSource]], list[FetchResult]]


@dataclass(frozen=True)
class Args:
    compact: bool
    urls: list[str]


def parse_args(argv: Sequence[str]) -> Args:
    """``--compact`` toggles compact mode; other ``--flags`` are ignored; the rest are feed URLs/paths."""
    compact = False
    urls: list[str] = []
    for arg in argv:
        if arg == "--compact":
            compact = True
        elif not arg.startswith("--"):
            urls.append(arg)
    return Args(compact, urls)


def agenda_window(now: datetime) -> Window:
    start = datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)
    return Window(start, start + timedelta(days=WINDOW_DAYS))


def run(argv: Sequence[str], now: datetime, fetcher: Fetcher = fetch_all,
        config_path: Path = CONFIG_PATH) -> dict:
    args = parse_args(argv)
    if args.urls:
        sources = [CalendarSource(f"Cal {i + 1}", u) for i, u in enumerate(args.urls)]
        errors: list[str] = []
    else:
        loaded = load_calendar_configs(config_path)
        sources, errors = loaded.sources, list(loaded.errors)

    if not sources:
        return not_configured_payload(now, errors)

    feeds: list[tuple[str, str]] = []
    for result in fetcher(sources):
        if result.error:
            errors.append(f"{result.name}: {result.error}")
        elif result.content:
            feeds.append((result.name, result.content))

    window = agenda_window(now)
    events: list[Event] = []
    for name, content in feeds:
        events.extend(parse_events(content, name, now.tzinfo, now, window))

    agenda = build_agenda(dedupe(events), now)
    return build_payload(agenda, errors=errors, ok=bool(feeds) or not errors,
                         calendar_count=len(sources), now=now, compact=args.compact)


def main(argv: Sequence[str] | None = None, now: datetime | None = None, fetcher: Fetcher = fetch_all,
         config_path: Path = CONFIG_PATH, out: TextIO | None = None) -> None:
    payload = run(
        sys.argv[1:] if argv is None else argv,
        now=datetime.now().astimezone() if now is None else now,
        fetcher=fetcher,
        config_path=config_path,
    )
    print(json.dumps(payload), file=out or sys.stdout)
