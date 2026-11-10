"""Fetch iCal feeds from URLs or local file paths, in parallel."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .models import CalendarSource, FetchResult

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) OmarchyGCalendarPlugin/1.0"
ACCEPT = "text/calendar, text/plain, */*"
TIMEOUT_SEC = 10
MAX_WORKERS = 8
PUBLIC_404_HINT = "404 Not Found (Make sure to use the 'Secret address in iCal format', not the Public one)"

Opener = Callable[..., Any]


def fetch_feed(source: CalendarSource, opener: Opener = urllib.request.urlopen) -> FetchResult:
    name = source.name or "Calendar"
    url = (source.url or "").strip()

    if not url:
        return FetchResult(name, error="Empty URL")

    if os.path.exists(url):
        try:
            with open(url, "r", encoding="utf-8") as f:
                return FetchResult(name, content=f.read())
        except (OSError, ValueError) as e:
            return FetchResult(name, error=f"File read error: {e}")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": ACCEPT})
        with opener(req, timeout=TIMEOUT_SEC) as resp:
            return FetchResult(name, content=resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        e.close()  # HTTPError wraps the open response body
        if e.code == 404 and "/public/" in url:
            return FetchResult(name, error=PUBLIC_404_HINT)
        return FetchResult(name, error=f"HTTP Error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        return FetchResult(name, error=f"Network error: {e.reason}")
    except Exception as e:  # noqa: BLE001 - one bad feed (bad URL, timeout, TLS...) must not break the bar
        return FetchResult(name, error=f"Error: {e}")


def fetch_all(sources: Sequence[CalendarSource], max_workers: int = MAX_WORKERS,
              opener: Opener = urllib.request.urlopen) -> list[FetchResult]:
    """Fetch every source concurrently; results keep the input order."""
    if not sources:
        return []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(sources))) as pool:
        return list(pool.map(lambda s: fetch_feed(s, opener), sources))
