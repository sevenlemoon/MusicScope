from datetime import date, time

from sqlalchemy import select
from fastapi.testclient import TestClient

from app.concerts import ConcertEventData, ConcertProviderError, MiletOfficialProvider, TicketmasterConcertProvider, deduplicate_events, lookup_artist_concerts, select_exact_attraction
from app.constants import DEMO_USER_ID
from app.db import SessionLocal
from app.models import Artist
from app.main import app


client = TestClient(app)


def demo_artist(db, number: int) -> Artist:
    return db.scalar(select(Artist).where(Artist.canonical_name == f"Demo Artist {number:02d}"))


def test_demo_artist_events_are_ordered_and_cache_on_second_lookup() -> None:
    db = SessionLocal()
    try:
        artist = demo_artist(db, 1)
        first = lookup_artist_concerts(db, artist, force_refresh=True, allow_demo=True)
        assert first["source"] == "demo"
        assert [event["date"] for event in first["events"]] == ["2027-03-18", "2027-07-02"]
        assert first["events"][1]["time"] is None
        second = lookup_artist_concerts(db, artist, allow_demo=True)
        assert second["source"] == "cache"
        assert second["events"] == first["events"]
    finally:
        db.close()


def test_artist_with_no_demo_events_returns_empty_list() -> None:
    db = SessionLocal()
    try:
        result = lookup_artist_concerts(db, demo_artist(db, 4), allow_demo=True)
        assert result["events"] == []
    finally:
        db.close()


def test_provider_mapping_extracts_event_fields() -> None:
    payload = {"id": "event-1", "name": "Live demo", "url": "https://example.com/event-1", "dates": {"start": {"localDate": "2027-05-01", "localTime": "20:30:00"}, "timezone": "Europe/London"}, "_embedded": {"venues": [{"name": "Room", "city": {"name": "London"}, "state": {}, "country": {"countryCode": "GB"}, "location": {"latitude": "51.5", "longitude": "-0.1"}}]}}
    event = TicketmasterConcertProvider._event_from_payload(payload, "artist-1")
    assert event == ConcertEventData("event-1", "Live demo", date(2027, 5, 1), event.start_time, "Europe/London", "Room", "London", None, "GB", 51.5, -0.1, "https://example.com/event-1", "artist-1")


def test_provider_failure_does_not_fabricate_live_results(monkeypatch) -> None:
    db = SessionLocal()
    try:
        artist = demo_artist(db, 4)

        class BrokenProvider:
            name = "broken"

            def upcoming_events(self, _artist):
                raise ConcertProviderError("offline")

        monkeypatch.setattr("app.concerts.provider_for", lambda _artist: BrokenProvider())
        result = lookup_artist_concerts(db, artist, force_refresh=True)
        assert result["provider_status"] == "provider_unavailable"
        assert result["source"] == "broken"
        assert result["events"] == []
    finally:
        db.close()


def test_ticketmaster_requires_exact_normalized_attraction_match() -> None:
    attractions = [{"name": "milet Official Fan Event"}, {"name": "Mile High Orchestra"}]
    assert select_exact_attraction(attractions, "milet") is None
    assert select_exact_attraction(attractions + [{"name": " Milet "}], "milet")["name"] == " Milet "


def test_concert_endpoints_return_artist_and_relevant_events() -> None:
    db = SessionLocal()
    try:
        artist = demo_artist(db, 1)
        artist_response = client.get(f"/api/v1/artists/{artist.id}/concerts?demo=true")
        assert artist_response.status_code == 200
        assert len(artist_response.json()["events"]) == 2
        all_response = client.get(f"/api/v1/concerts?demo=true&user_id={DEMO_USER_ID}")
        assert all_response.status_code == 200
        assert any(event["artist"] == "Demo Artist 01" for event in all_response.json()["events"])
    finally:
        db.close()


def test_concert_search_demo_mode_is_explicit() -> None:
    response = client.get("/api/v1/concerts/search?artist=milet&demo=true")
    assert response.status_code == 200
    payload = response.json()
    assert payload["artist"]["name"] == "milet"
    assert payload["events"][0]["is_demo"] is True
    assert payload["events"][0]["external_url"] is None


def test_milet_official_parser_maps_schedule_fields() -> None:
    html = '''<meta property="og:image" content="/tour.png"><div class="live-schedule-section__list-wrapper"><dt class="live-schedule-section__list-title">2026<span class="live-schedule-section__list-date">9.12</span></dt><dd class="live-schedule-section__list-description">千葉県　森のホール21大ホール<br />開場16:00 / 開演17:00</dd></div>'''
    event = MiletOfficialProvider._parse(html)[0]
    assert event.event_name == 'milet live tour “Made of Glass”'
    assert event.start_date == date(2026, 9, 12)
    assert event.start_time.isoformat(timespec="minutes") == "17:00"
    assert event.doors_time.isoformat(timespec="minutes") == "16:00"
    assert event.region == "千葉県"
    assert event.external_url == MiletOfficialProvider.tour_url
    assert event.image_url.endswith("/tour.png")


def test_provider_deduplication_uses_date_and_venue() -> None:
    first = ConcertEventData("one", "Tour", date(2026, 9, 12), None, "Asia/Tokyo", "Room", None, None, "Japan", None, None, "https://official.example/tour")
    duplicate = ConcertEventData("two", "Tour", date(2026, 9, 12), time(19, 0), "Asia/Tokyo", "Room", None, None, "Japan", None, None, "https://ticketmaster.example/event")
    assert deduplicate_events([first, duplicate]) == [first]


def test_unavailable_live_search_never_returns_demo_or_placeholder_link() -> None:
    response = client.get("/api/v1/concerts/search?artist=Unknown%20Live%20Artist&force_refresh=true")
    assert response.status_code == 200
    payload = response.json()
    assert payload["events"] == []
    assert payload["provider_status"] == "provider_unavailable"
    assert all("example.com" not in str(event.get("external_url")) for event in payload["events"])
