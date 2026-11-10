"""Load calendar sources from ~/.config/gcalendar-tray/config.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CalendarSource, ConfigResult

CONFIG_PATH = Path.home() / ".config" / "gcalendar-tray" / "config.json"


def _default_name(idx: int) -> str:
    return f"Cal {idx + 1}"


def parse_config(data: Any) -> list[CalendarSource]:
    """Pure: map a decoded config document to calendar sources.

    Accepted shapes (first match wins):
      1. ``{"calendars": ["https://...", {"name": "Work", "url": "...", "color": "#f00"}]}``
      2. ``{"ical_urls": ["https://...", ...]}``
      3. ``{"ical_url": "https://a, https://b"}`` (single or comma-separated)
    """
    if not isinstance(data, dict):
        return []
    sources: list[CalendarSource] = []

    if isinstance(data.get("calendars"), list):
        for idx, item in enumerate(data["calendars"]):
            if isinstance(item, str) and item.strip():
                sources.append(CalendarSource(_default_name(idx), item.strip()))
            elif isinstance(item, dict) and isinstance(item.get("url"), str) and item["url"]:
                name = item.get("name") or _default_name(idx)
                sources.append(CalendarSource(str(name), item["url"].strip(), str(item.get("color") or "")))

    elif isinstance(data.get("ical_urls"), list):
        for idx, url in enumerate(data["ical_urls"]):
            if isinstance(url, str) and url.strip():
                sources.append(CalendarSource(_default_name(idx), url.strip()))

    elif isinstance(data.get("ical_url"), str):
        parts = [p.strip() for p in data["ical_url"].split(",") if p.strip()]
        for idx, url in enumerate(parts):
            sources.append(CalendarSource(_default_name(idx) if len(parts) > 1 else "Calendar", url))

    return sources


def load_calendar_configs(path: Path = CONFIG_PATH) -> ConfigResult:
    """Read and parse the config file. A missing file is not an error."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ConfigResult()
    except (OSError, UnicodeDecodeError) as e:
        return ConfigResult(errors=[f"Config: cannot read {path}: {e}"])

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return ConfigResult(errors=[f"Config: invalid JSON in {path}: {e}"])

    if not isinstance(data, dict):
        return ConfigResult(errors=[f"Config: expected a JSON object in {path}"])
    return ConfigResult(sources=parse_config(data))
