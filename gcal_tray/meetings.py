"""Detect video-call links (Meet, Zoom, Teams, ...) in event text."""

from __future__ import annotations

import re

# Order matters: the first provider whose pattern matches wins.
MEETING_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Google Meet", re.compile(r"https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}")),
    ("Zoom", re.compile(r"https://[a-zA-Z0-9\.\-_]*zoom\.us/(?:j/[0-9]+|my/[a-zA-Z0-9\.\-_]+)(?:\?[^\s<>\"']*)?")),
    ("Microsoft Teams", re.compile(r"https://teams\.microsoft\.com/l/meetup-join/[^\s<>\"']+")),
    ("Webex", re.compile(r"https://[a-zA-Z0-9\.\-_]*webex\.com/[^\s<>\"']+")),
    ("Whereby", re.compile(r"https://whereby\.com/[^\s<>\"']+")),
]


def find_meeting_link(text: str | None) -> tuple[str | None, str | None]:
    """Return ``(provider, url)`` for the first known meeting link, else ``(None, None)``."""
    if not text:
        return None, None
    for name, pattern in MEETING_PATTERNS:
        m = pattern.search(text)
        if m:
            return name, m.group(0)
    return None, None
