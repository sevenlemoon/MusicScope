import csv
import re
import unicodedata
from datetime import datetime, timezone
from io import StringIO
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Album, Artist, ImportBatch, ListeningEvent, RawImportRecord, Track, TrackArtist, UserLibraryTrack

RESOLUTION_STATES = {"resolved", "ambiguous", "unresolved", "manually_corrected"}
VERSION_RE = re.compile(r"\s*[\[(](live|remix|remastered|acoustic|cover|edit|version)[^\])]*[\])]", re.I)
PLAYLIST_SEPARATOR_RE = re.compile(r"\s+[-–—]\s+")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = "".join(character for character in unicodedata.normalize("NFKD", value) if not unicodedata.combining(character)).casefold()
    value = value.replace("&", " and ")
    value = re.sub(r"[’'`]+", "", value)
    value = re.sub(r"[–—−-]", " ", value)
    value = re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def detect_version(title: str) -> str:
    match = VERSION_RE.search(title)
    if not match:
        return "original"
    label = match.group(1).lower()
    return {"remastered": "remastered", "remix": "remix", "live": "live", "cover": "cover"}.get(label, "alternate")


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def parse_bool(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "y", "favorite", "favourite"}


def parse_csv(content: str) -> list[dict[str, str]]:
    reader = csv.DictReader(StringIO(content))
    return [{str(key).strip(): (value or "").strip() for key, value in row.items() if key} for row in reader]


def parse_playlist_text(content: str) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    invalid: list[str] = []
    for line in content.splitlines():
        original = line.strip()
        if not original:
            continue
        match = PLAYLIST_SEPARATOR_RE.search(original)
        if not match:
            invalid.append(original)
            continue
        title, artist = original[: match.start()].strip(), original[match.end() :].strip()
        if not title or not artist:
            invalid.append(original)
            continue
        artists = [part.strip() for part in re.split(r"\s*(?:/|＆|&|、|，|,)\s*", artist) if part.strip()]
        rows.append({"title": title, "artist": artist, "artists": artists, "source": "assisted_playlist_text"})
    return rows, invalid


def ensure_artist(db: Session, name: str) -> Artist:
    normalized = normalize_text(name)
    artist = db.scalar(select(Artist).where(Artist.normalized_name == normalized))
    if artist:
        return artist
    artist = Artist(canonical_name=name.strip() or "Unknown Artist", normalized_name=normalized or "unknown artist")
    db.add(artist)
    db.flush()
    return artist


def resolve_track(db: Session, artist_name: str, title: str, album_name: str | None) -> tuple[Track | None, str, float | None, str]:
    artist_key = normalize_text(artist_name)
    title_key = normalize_text(title)
    candidates = list(db.scalars(select(Track).join(Artist, Track.primary_artist_id == Artist.id).where(Artist.normalized_name == artist_key, Track.normalized_title == title_key)))
    if len(candidates) == 1:
        return candidates[0], "resolved", 1.0, "exact normalized artist/title match"
    if len(candidates) > 1:
        return None, "ambiguous", 0.65, "multiple canonical tracks share the normalized artist/title"
    return None, "unresolved", None, "no canonical track matched"


def ensure_catalog_track(db: Session, artist_names: list[str], title: str, album_name: str | None, source_type: str) -> Track:
    artists = [ensure_artist(db, name) for name in artist_names if name.strip()]
    if not artists:
        raise ValueError("artist is required")
    title_key = normalize_text(title)
    track = db.scalar(select(Track).where(Track.primary_artist_id == artists[0].id, Track.normalized_title == title_key))
    if track is None:
        album = None
        if album_name:
            album_key = normalize_text(album_name)
            album = db.scalar(select(Album).where(Album.normalized_title == album_key, Album.artist_id == artists[0].id))
            if album is None:
                album = Album(canonical_title=album_name.strip(), normalized_title=album_key, artist_id=artists[0].id)
                db.add(album)
                db.flush()
        track = Track(canonical_title=title.strip(), normalized_title=title_key, primary_artist_id=artists[0].id, album_id=album.id if album else None, version_type=detect_version(title), metadata_json={"catalog_status": "imported", "source": source_type})
        db.add(track)
        db.flush()
    for index, artist in enumerate(artists):
        role = "primary" if index == 0 else "featured"
        if db.scalar(select(TrackArtist).where(TrackArtist.track_id == track.id, TrackArtist.artist_id == artist.id, TrackArtist.role == role)) is None:
            db.add(TrackArtist(track_id=track.id, artist_id=artist.id, role=role))
    return track


def _new_batch(db: Session, user_id, source_metadata: dict[str, Any]) -> ImportBatch:
    batch = ImportBatch(user_id=user_id, source_type=str(source_metadata.get("source_type", "csv")), source_metadata=source_metadata, status="processing")
    db.add(batch)
    db.flush()
    return batch


def _finish_batch(db: Session, batch: ImportBatch) -> ImportBatch:
    records = list(db.scalars(select(RawImportRecord).where(RawImportRecord.batch_id == batch.id)))
    batch.total_records = len(records)
    batch.resolved_records = sum(record.resolution_status in {"resolved", "manually_corrected"} for record in records)
    batch.ambiguous_records = sum(record.resolution_status == "ambiguous" for record in records)
    batch.unresolved_records = sum(record.resolution_status == "unresolved" for record in records)
    batch.status = "completed"
    db.commit()
    db.refresh(batch)
    return batch


def import_library_rows(db: Session, user_id, rows: list[dict[str, Any]], source_metadata: dict[str, Any] | None = None) -> ImportBatch:
    source_metadata = source_metadata or {}
    batch = _new_batch(db, user_id, source_metadata)
    source_type = str(source_metadata.get("source_type", "playlist_library"))
    source_name = str(source_metadata.get("source_name") or source_metadata.get("filename") or source_type)
    for row in rows:
        artist_name = row.get("artist") or row.get("artist_name") or ""
        title = row.get("title") or row.get("track") or row.get("track_title") or ""
        album_name = row.get("album") or row.get("album_title") or ""
        artists = row.get("artists") or [artist_name]
        track = ensure_catalog_track(db, artists, title, album_name, source_type) if title and artist_name else None
        state, confidence, note = ("resolved", 1.0, "canonical track created or matched from library import") if track else ("unresolved", None, "artist and title are required")
        raw = RawImportRecord(batch_id=batch.id, raw_payload=dict(row), source_record_id=row.get("source_record_id") or row.get("id"), observed_at=None, resolution_status=state, resolution_confidence=confidence, resolution_note=note, resolved_track_id=track.id if track else None)
        db.add(raw)
        db.flush()
        if track:
            membership = db.scalar(select(UserLibraryTrack).where(UserLibraryTrack.user_id == user_id, UserLibraryTrack.track_id == track.id, UserLibraryTrack.source_type == source_type, UserLibraryTrack.source_name == source_name))
            if membership is None:
                db.add(UserLibraryTrack(user_id=user_id, track_id=track.id, source_type=source_type, source_name=source_name, source_metadata=source_metadata, imported_at=datetime.now(timezone.utc), active=True))
            else:
                membership.active = True
    db.flush()
    return _finish_batch(db, batch)


def import_listening_rows(db: Session, user_id, rows: list[dict[str, Any]], source_metadata: dict[str, Any] | None = None) -> ImportBatch:
    source_metadata = source_metadata or {}
    batch = _new_batch(db, user_id, source_metadata)
    for row in rows:
        artist_name = row.get("artist") or row.get("artist_name") or ""
        title = row.get("title") or row.get("track") or row.get("track_title") or ""
        album_name = row.get("album") or row.get("album_title") or ""
        track, state, confidence, note = resolve_track(db, artist_name, title, album_name) if artist_name and title else (None, "unresolved", None, "artist and title are required")
        raw = RawImportRecord(batch_id=batch.id, raw_payload=dict(row), source_record_id=row.get("source_record_id") or row.get("id"), observed_at=parse_datetime(row.get("played_at") or row.get("timestamp")), resolution_status=state, resolution_confidence=confidence, resolution_note=note, resolved_track_id=track.id if track else None)
        db.add(raw)
        db.flush()
        if track:
            duration = int(row["duration_played_ms"]) if str(row.get("duration_played_ms", "")).isdigit() else None
            db.add(ListeningEvent(user_id=user_id, track_id=track.id, raw_record_id=raw.id, played_at=raw.observed_at, duration_played_ms=duration, completion_ratio=float(row["completion_ratio"]) if row.get("completion_ratio") else None, event_type=(row.get("event_type") or "play").casefold(), is_favorite=parse_bool(row.get("favorite") or row.get("is_favorite")), context={"source": row.get("source") or "csv", "version_type": detect_version(title)}))
    db.flush()
    return _finish_batch(db, batch)


def import_rows(db: Session, user_id, rows: list[dict[str, Any]], source_metadata: dict[str, Any] | None = None) -> ImportBatch:
    """Compatibility name for behavioral/listening-history imports."""
    return import_listening_rows(db, user_id, rows, source_metadata)
