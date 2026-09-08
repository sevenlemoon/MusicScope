"""Small concert-provider boundary with a deterministic local fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from html import unescape
from urllib.parse import urljoin
import re
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .importer import normalize_text
from .models import Artist, ArtistProviderIdentity, ConcertEvent, UserTrackRelationship


class ConcertProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConcertEventData:
    provider_event_id: str
    event_name: str | None
    start_date: date
    start_time: time | None
    timezone_name: str | None
    venue_name: str | None
    city: str | None
    region: str | None
    country: str | None
    latitude: float | None
    longitude: float | None
    external_url: str | None
    provider_artist_id: str | None = None
    image_url: str | None = None
    doors_time: time | None = None


class ConcertProvider(Protocol):
    name: str

    def upcoming_events(self, artist: Artist) -> list[ConcertEventData]: ...


DEMO_FIXTURES: dict[str, list[ConcertEventData]] = {
    "milet": [
        ConcertEventData("demo-milet-1", "milet — Demo Live", date(2027, 5, 16), time(19, 0), "Asia/Tokyo", "Zepp DiverCity", "Tokyo", None, "Japan", None, None, "https://example.com/musicscope-demo/milet-1"),
    ],
    "demo artist 01": [
        ConcertEventData("demo-a01-1", "Demo Artist 01 — Spring Room", date(2027, 3, 18), time(20, 0), "Asia/Shanghai", "Harbor Room", "Shanghai", None, "China", None, None, "https://example.com/musicscope-demo/demo-a01-1"),
        ConcertEventData("demo-a01-2", "Demo Artist 01 — Summer Hall", date(2027, 7, 2), None, "Europe/London", "North Hall", "London", None, "United Kingdom", None, None, "https://example.com/musicscope-demo/demo-a01-2"),
    ],
    "demo artist 02": [
        ConcertEventData("demo-a02-1", "Demo Artist 02 — Night Set", date(2027, 4, 9), time(19, 30), "America/New_York", "Civic Theater", "New York", "NY", "United States", None, None, "https://example.com/musicscope-demo/demo-a02-1"),
    ],
    "demo artist 03": [
        ConcertEventData("demo-a03-1", "Demo Artist 03 — Festival Stage", date(2027, 6, 21), None, "Europe/Berlin", "Park Stage", "Berlin", None, "Germany", None, None, None),
    ],
    "demo artist 04": [],
}


class DemoConcertProvider:
    name = "demo"

    def upcoming_events(self, artist: Artist) -> list[ConcertEventData]:
        return DEMO_FIXTURES.get(normalize_text(artist.canonical_name), [])


class UnavailableConcertProvider:
    """Explicit live-mode failure when no external provider is configured."""

    name = "live"

    def upcoming_events(self, _artist: Artist) -> list[ConcertEventData]:
        raise ConcertProviderError("No live concert provider is configured")


class TicketmasterConcertProvider:
    name = "ticketmaster"
    base_url = "https://app.ticketmaster.com/discovery/v2"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def upcoming_events(self, artist: Artist) -> list[ConcertEventData]:
        try:
            with httpx.Client(timeout=get_settings().concert_request_timeout_seconds) as client:
                attraction_response = client.get(f"{self.base_url}/attractions.json", params={"apikey": self.api_key, "keyword": artist.canonical_name, "classificationName": "music", "size": 10})
                attraction_response.raise_for_status()
                attractions = attraction_response.json().get("_embedded", {}).get("attractions", [])
                match = select_exact_attraction(attractions, artist.canonical_name)
                if not match:
                    return []
                provider_artist_id = match.get("id")
                event_response = client.get(f"{self.base_url}/events.json", params={"apikey": self.api_key, "attractionId": provider_artist_id, "startDateTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "sort": "date,asc", "size": 50})
                event_response.raise_for_status()
                return [self._event_from_payload(event, provider_artist_id) for event in event_response.json().get("_embedded", {}).get("events", [])]
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ConcertProviderError(f"Ticketmaster lookup failed: {exc}") from exc
    @staticmethod
    def _event_from_payload(event: dict, provider_artist_id: str | None) -> ConcertEventData:
        dates = event.get("dates", {})
        start = dates.get("start", {})
        venue = (event.get("_embedded", {}).get("venues") or [{}])[0]
        local_date = date.fromisoformat(start["localDate"])
        local_time = time.fromisoformat(start["localTime"]) if start.get("localTime") else None
        location = venue.get("location") or {}
        images = sorted(event.get("images") or [], key=lambda image: image.get("width", 0) * image.get("height", 0), reverse=True)
        return ConcertEventData(str(event["id"]), event.get("name"), local_date, local_time, dates.get("timezone"), venue.get("name"), venue.get("city", {}).get("name"), venue.get("state", {}).get("stateCode") or venue.get("state", {}).get("name"), venue.get("country", {}).get("countryCode"), float(location["latitude"]) if location.get("latitude") else None, float(location["longitude"]) if location.get("longitude") else None, event.get("url"), provider_artist_id, images[0].get("url") if images else None)


def select_exact_attraction(attractions: list[dict], artist_name: str) -> dict | None:
    normalized_artist = normalize_text(artist_name)
    return next((item for item in attractions if normalize_text(item.get("name")) == normalized_artist), None)


class MiletOfficialProvider:
    name = "official_milet"
    tour_url = "https://fc.milet.jp/s/n114/page/tour-2026?ima=0000&link=ROBO004"

    def upcoming_events(self, artist: Artist) -> list[ConcertEventData]:
        if normalize_text(artist.canonical_name) != "milet":
            return []
        try:
            response = httpx.get(self.tour_url, headers={"User-Agent": "MusicScope/1.0"}, timeout=get_settings().concert_request_timeout_seconds)
            response.raise_for_status()
            return self._parse(response.text)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ConcertProviderError(f"Official milet lookup failed: {exc}") from exc

    @classmethod
    def _parse(cls, html: str) -> list[ConcertEventData]:
        image_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.I)
        image_url = urljoin(cls.tour_url, unescape(image_match.group(1))) if image_match else None
        blocks = re.findall(r'<div[^>]+class=["\']live-schedule-section__list-wrapper["\'][^>]*>(.*?)</div>', html, re.I | re.S)
        results: list[ConcertEventData] = []
        for index, block in enumerate(blocks):
            title = re.search(r'live-schedule-section__list-title[^>]*>\s*(\d{4})\s*<span[^>]*>\s*(\d{1,2}\.\d{1,2})', block, re.I | re.S)
            description = re.search(r'live-schedule-section__list-description[^>]*>(.*?)</dd>', block, re.I | re.S)
            if not title or not description:
                continue
            year, month_day = int(title.group(1)), title.group(2).split(".")
            text = re.sub(r'<br\s*/?>', "\n", description.group(1), flags=re.I)
            text = re.sub(r'<[^>]+>', " ", unescape(text))
            text = re.sub(r"\s+", " ", text).strip()
            venue_parts = re.split(r"\s*[　 ]\s*", text, maxsplit=1)
            location = venue_parts[0].strip()
            venue = venue_parts[1].split(" 開場", 1)[0].strip() if len(venue_parts) > 1 else location
            prefecture = location if len(venue_parts) <= 1 else location
            doors_match = re.search(r"開場\s*(\d{1,2}:\d{2})", text)
            start_match = re.search(r"開演\s*(\d{1,2}:\d{2})", text)
            results.append(ConcertEventData(f"milet-official-{year}-{month_day[0]}-{month_day[1]}-{index}", "milet live tour “Made of Glass”", date(year, int(month_day[0]), int(month_day[1])), time.fromisoformat(start_match.group(1)) if start_match else None, "Asia/Tokyo", venue, None, prefecture, "Japan", None, None, cls.tour_url, None, image_url, time.fromisoformat(doors_match.group(1)) if doors_match else None))
        if not results:
            raise ValueError("No structured milet tour events found")
        return results


def provider_for(artist: Artist | None = None) -> ConcertProvider:
    settings = get_settings()
    if artist and normalize_text(artist.canonical_name) == "milet":
        return MiletOfficialProvider()
    if settings.concert_provider.casefold() == "ticketmaster" and settings.ticketmaster_api_key:
        return TicketmasterConcertProvider(settings.ticketmaster_api_key)
    return UnavailableConcertProvider()


def deduplicate_events(data: list[ConcertEventData]) -> list[ConcertEventData]:
    """Collapse provider duplicates using the stable artist/date/venue tuple."""
    unique: list[ConcertEventData] = []
    seen: set[tuple[date, str]] = set()
    for item in data:
        key = (item.start_date, normalize_text(item.venue_name or ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def serialize_event(event: ConcertEvent, artist: Artist) -> dict:
    return {"id": str(event.id), "artist_id": str(artist.id), "artist": artist.canonical_name, "provider": event.provider, "event_id": event.provider_event_id, "event_name": event.event_name, "date": event.start_date.isoformat(), "time": event.start_time.isoformat(timespec="minutes") if event.start_time else None, "doors_time": event.doors_time.isoformat(timespec="minutes") if event.doors_time else None, "timezone": event.timezone_name, "venue": event.venue_name, "city": event.city, "region": event.region, "country": event.country, "latitude": event.latitude, "longitude": event.longitude, "external_url": None if event.is_demo else event.external_url, "image_url": event.image_url, "fetched_at": event.fetched_at, "status": event.status, "is_demo": event.is_demo}


def relevant_artists(db: Session, user_id, limit: int = 20) -> list[Artist]:
    # The relationship is track-scoped, so aggregate it against each track's artist.
    from .models import Track
    relationships = list(db.execute(select(Track.primary_artist_id, UserTrackRelationship.favorite_state, UserTrackRelationship.play_count, UserTrackRelationship.last_played_at).join(UserTrackRelationship, UserTrackRelationship.track_id == Track.id).where(UserTrackRelationship.user_id == user_id, UserTrackRelationship.excluded.is_(False))).all())
    scores: dict = {}
    for artist_id, favorite, play_count, last_played in relationships:
        current = scores.setdefault(artist_id, [0, 0, datetime.min.replace(tzinfo=timezone.utc)])
        current[0] += 1 if favorite else 0
        current[1] += play_count or 0
        if last_played and last_played > current[2]:
            current[2] = last_played
    artists = {artist.id: artist for artist in db.scalars(select(Artist).where(Artist.id.in_(list(scores) or [None]))).all()}
    ordered = sorted(artists.values(), key=lambda artist: (-scores[artist.id][0], -scores[artist.id][1], artist.canonical_name))
    return ordered[:limit]


def lookup_artist_concerts(db: Session, artist: Artist, force_refresh: bool = False, allow_demo: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    cache_cutoff = now.timestamp() - get_settings().concert_cache_hours * 3600
    cached = list(db.scalars(select(ConcertEvent).where(ConcertEvent.artist_id == artist.id, ConcertEvent.start_date >= date.today(), ConcertEvent.is_demo == allow_demo).order_by(ConcertEvent.start_date, ConcertEvent.start_time.nulls_last(), ConcertEvent.event_name)))
    fresh = cached and max(event.fetched_at.timestamp() for event in cached) >= cache_cutoff
    if cached and fresh and not force_refresh:
        return {"artist": {"id": str(artist.id), "name": artist.canonical_name}, "events": [serialize_event(event, artist) for event in cached], "source": "cache", "provider_status": "cached", "stale": False}
    provider = DemoConcertProvider() if allow_demo else provider_for(artist)
    try:
        data = deduplicate_events(provider.upcoming_events(artist))
        events = upsert_events(db, artist, provider.name, data)
        return {"artist": {"id": str(artist.id), "name": artist.canonical_name}, "events": [serialize_event(event, artist) for event in events], "source": provider.name, "provider_status": "ok", "stale": False}
    except ConcertProviderError:
        if allow_demo:
            demo = DemoConcertProvider()
            events = upsert_events(db, artist, demo.name, demo.upcoming_events(artist))
            return {"artist": {"id": str(artist.id), "name": artist.canonical_name}, "events": [serialize_event(event, artist) for event in events], "source": "demo", "provider_status": "demo", "stale": False}
        if cached:
            return {"artist": {"id": str(artist.id), "name": artist.canonical_name}, "events": [serialize_event(event, artist) for event in cached], "source": "cache", "provider_status": "stale_cache", "stale": True}
        return {"artist": {"id": str(artist.id), "name": artist.canonical_name}, "events": [], "source": provider.name, "provider_status": "provider_unavailable", "stale": False}


def upsert_events(db: Session, artist: Artist, provider_name: str, data: list[ConcertEventData]) -> list[ConcertEvent]:
    now = datetime.now(timezone.utc)
    result: list[ConcertEvent] = []
    for item in data:
        event = db.scalar(select(ConcertEvent).where(ConcertEvent.artist_id == artist.id, ConcertEvent.provider == provider_name, ConcertEvent.provider_event_id == item.provider_event_id))
        if not event:
            event = ConcertEvent(artist_id=artist.id, provider=provider_name, provider_event_id=item.provider_event_id)
        event.event_name = item.event_name
        event.start_date = item.start_date
        event.start_time = item.start_time
        event.doors_time = item.doors_time
        event.timezone_name = item.timezone_name
        event.venue_name = item.venue_name
        event.city = item.city
        event.region = item.region
        event.country = item.country
        event.latitude = item.latitude
        event.longitude = item.longitude
        event.external_url = item.external_url
        event.image_url = item.image_url
        event.fetched_at = now
        event.status = "upcoming"
        event.is_demo = provider_name == "demo"
        db.add(event)
        result.append(event)
        if item.provider_artist_id:
            identity = db.scalar(select(ArtistProviderIdentity).where(ArtistProviderIdentity.artist_id == artist.id, ArtistProviderIdentity.provider == provider_name)) or ArtistProviderIdentity(artist_id=artist.id, provider=provider_name, normalized_name=normalize_text(artist.canonical_name))
            identity.provider_artist_id = item.provider_artist_id
            identity.last_resolved_at = now
            db.add(identity)
    db.commit()
    return sorted(result, key=lambda event: (event.start_date, event.start_time is None, event.start_time or time.min, event.event_name or ""))
