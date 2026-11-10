"""Plain data types passed between the pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CalendarSource:
    name: str
    url: str
    color: str = ""


@dataclass(frozen=True)
class FetchResult:
    name: str
    content: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class Event:
    calendar_name: str
    title: str
    start: datetime
    end: datetime
    is_all_day: bool
    call_type: str = ""
    call_url: str = ""
    location: str = ""
    description: str = ""


@dataclass(frozen=True)
class ConfigResult:
    sources: list[CalendarSource] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
