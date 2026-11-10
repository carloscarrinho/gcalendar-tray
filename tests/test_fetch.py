import email.message
import io
import urllib.error

import pytest

from gcal_tray.fetch import PUBLIC_404_HINT, TIMEOUT_SEC, USER_AGENT, fetch_all, fetch_feed
from gcal_tray.models import CalendarSource, FetchResult

from conftest import fixture_path


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def opener_returning(body: bytes):
    calls = []

    def opener(req, timeout):
        calls.append((req, timeout))
        return FakeResponse(body)

    opener.calls = calls
    return opener


def opener_raising(exc):
    def opener(req, timeout):
        raise exc
    return opener


def http_error(url, code, reason):
    return urllib.error.HTTPError(url, code, reason, email.message.Message(), None)


def test_local_file():
    r = fetch_feed(CalendarSource("Local", fixture_path("soon.ics")), opener=opener_raising(AssertionError))
    assert r.error is None and "Quick huddle" in r.content


def test_local_file_not_utf8(tmp_path):
    p = tmp_path / "bad.ics"
    p.write_bytes(b"\xff\xfe\x00bad")
    r = fetch_feed(CalendarSource("Bad", str(p)))
    assert r.content is None and r.error.startswith("File read error: ")


@pytest.mark.parametrize("url", ["", "   "])
def test_empty_url(url):
    assert fetch_feed(CalendarSource("X", url)) == FetchResult("X", error="Empty URL")


def test_http_200_sends_headers_and_timeout():
    opener = opener_returning("BEGIN:VCALENDAR\nSUMMARY:Café\n".encode() + b"\xff")
    r = fetch_feed(CalendarSource("Web", " https://example.com/cal.ics "), opener=opener)
    assert r.error is None
    assert r.content.startswith("BEGIN:VCALENDAR\nSUMMARY:Café") and r.content.endswith("�")
    [(req, timeout)] = opener.calls
    assert req.full_url == "https://example.com/cal.ics"
    assert req.get_header("User-agent") == USER_AGENT
    assert timeout == TIMEOUT_SEC


def test_404_on_public_url_gives_hint():
    url = "https://calendar.google.com/calendar/ical/x/public/basic.ics"
    r = fetch_feed(CalendarSource("G", url), opener=opener_raising(http_error(url, 404, "Not Found")))
    assert r == FetchResult("G", error=PUBLIC_404_HINT)


def test_404_on_private_url():
    url = "https://example.com/private-abc/basic.ics"
    r = fetch_feed(CalendarSource("G", url), opener=opener_raising(http_error(url, 404, "Not Found")))
    assert r.error == "HTTP Error 404: Not Found"


def test_other_http_error():
    url = "https://example.com/x"
    r = fetch_feed(CalendarSource("G", url), opener=opener_raising(http_error(url, 503, "Service Unavailable")))
    assert r.error == "HTTP Error 503: Service Unavailable"


def test_url_error():
    r = fetch_feed(CalendarSource("G", "https://nope.invalid/"),
                   opener=opener_raising(urllib.error.URLError("Name or service not known")))
    assert r.error == "Network error: Name or service not known"


def test_timeout():
    r = fetch_feed(CalendarSource("G", "https://slow.example/"), opener=opener_raising(TimeoutError("timed out")))
    assert r.error == "Error: timed out"


def test_malformed_url_is_reported_not_raised():
    r = fetch_feed(CalendarSource("G", "not-a-real-feed"))
    assert r.error == "Error: unknown url type: 'not-a-real-feed'"


def test_fetch_all_preserves_order():
    sources = [CalendarSource(f"C{i}", fixture_path("soon.ics") if i % 2 else "") for i in range(5)]
    results = fetch_all(sources, max_workers=3)
    assert [r.name for r in results] == ["C0", "C1", "C2", "C3", "C4"]
    assert [r.error for r in results] == ["Empty URL", None, "Empty URL", None, "Empty URL"]


def test_fetch_all_empty():
    assert fetch_all([]) == []
