import pytest

from gcal_tray.meetings import find_meeting_link


@pytest.mark.parametrize(
    ("text", "provider", "url"),
    [
        ("Join https://meet.google.com/abc-defg-hij now", "Google Meet", "https://meet.google.com/abc-defg-hij"),
        ("https://acme.zoom.us/j/123456789?pwd=xYz", "Zoom", "https://acme.zoom.us/j/123456789?pwd=xYz"),
        ("https://zoom.us/my/jane.doe", "Zoom", "https://zoom.us/my/jane.doe"),
        ("<https://teams.microsoft.com/l/meetup-join/19%3a0/0>", "Microsoft Teams",
         "https://teams.microsoft.com/l/meetup-join/19%3a0/0"),
        ("https://acme.webex.com/meet/jdoe", "Webex", "https://acme.webex.com/meet/jdoe"),
        ("Room: https://whereby.com/room-42", "Whereby", "https://whereby.com/room-42"),
    ],
)
def test_providers(text, provider, url):
    assert find_meeting_link(text) == (provider, url)


@pytest.mark.parametrize("text", [None, "", "Room 4, https://example.com/meet", "https://meet.google.com/bad"])
def test_no_match(text):
    assert find_meeting_link(text) == (None, None)


def test_first_provider_in_priority_order_wins():
    text = "https://acme.zoom.us/j/1 or https://meet.google.com/abc-defg-hij"
    assert find_meeting_link(text)[0] == "Google Meet"
