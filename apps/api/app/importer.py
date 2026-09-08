import csv
import re
import unicodedata
from datetime import datetime
from io import StringIO
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Album,
    Artist,
    ImportBatch,
    ListeningEvent,
    RawImportRecord,
    Track,
)

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
    if label == "remastered":
        return "remastered"
    if label == "remix":
        return "remix"
    if label == "live":
        return "live"
    if label == "cover":
        return "cover"
    return "alternate"


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
    rows = []
    for row in reader:
        rows.append({str(key).strip(): (value or "").strip() for key, value in row.items() if key})
    return rows


def parse_playlist_text(content: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse copied `Track - Artist` lines without inventing metadata."""
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
    candidates = list(
        db.scalars(
            select(Track)
            .join(Artist, Track.primary_artist_id == Artist.id, isouter=False)
            .where(Artist.normalized_name == artist_key, Track.normalized_title == title_key)
        )
    )
    if len(candidates) == 1:
        return candidates[0], "resolved", 1.0, "exact normalized artist/title match"
    if len(candidates) > 1:
        return None, "ambiguous", 0.65, "multiple canonical tracks share the normalized artist/title"
    return None, "unresolved", None, "no canonical track matched"


def import_rows(db: Session, user_id, rows: list[dict[str, Any]], source_metadata: dict[str, Any] | None = None) -> ImportBatch:
    source_metadata = source_metadata or {}
    batch = ImportBatch(user_id=user_id, source_type=str(source_metadata.get("source_type", "csv")), source_metadata=source_metadata, status="processing")
    db.add(batch)
    db.flush()
    for row in rows:
        artist_name = row.get("artist") or row.get("artist_name") or ""
        title = row.get("title") or row.get("track") or row.get("track_title") or ""
        album_name = row.get("album") or row.get("album_title") or ""
        artist = ensure_artist(db, artist_name) if artist_name else None
        track, state, confidence, note = resolve_track(db, artist_name, title, album_name) if artist_name and title else (None, "unresolved", None, "artist and title are required")
        if track is None and artist and title:
            album = None
            if album_name:
                album_key = normalize_text(album_name)
                album = db.scalar(select(Album).where(Album.normalized_title == album_key, Album.artist_id == artist.id))
                if not album:
                    album = Album(canonical_title=album_name, normalized_title=album_key, artist_id=artist.id)
                    db.add(album)
                    db.flush()
            track = None
        raw_payload = dict(row)
        raw = RawImportRecord(
            batch_id=batch.id,
            raw_payload=raw_payload,
            source_record_id=row.get("source_record_id") or row.get("id"),
            observed_at=parse_datetime(row.get("played_at") or row.get("timestamp")),
            resolution_status=state,
            resolution_confidence=confidence,
            resolution_note=note,
            resolved_track_id=track.id if track else None,
        )
        db.add(raw)
        db.flush()
        duration = int(row["duration_played_ms"]) if str(row.get("duration_played_ms", "")).isdigit() else None
        db.add(
            ListeningEvent(
                user_id=user_id,
                track_id=track.id if track else None,
                raw_record_id=raw.id,
                played_at=raw.observed_at,
                duration_played_ms=duration,
                completion_ratio=float(row["completion_ratio"]) if row.get("completion_ratio") else None,
                event_type=(row.get("event_type") or "play").casefold(),
                is_favorite=parse_bool(row.get("favorite") or row.get("is_favorite")),
                context={"source": row.get("source") or "csv", "version_type": detect_version(title)},
            )
        )
    db.flush()
    records = list(db.scalars(select(RawImportRecord).where(RawImportRecord.batch_id == batch.id)))
    batch.total_records = len(records)
    batch.resolved_records = sum(record.resolution_status in {"resolved", "manually_corrected"} for record in records)
    batch.ambiguous_records = sum(record.resolution_status == "ambiguous" for record in records)
    batch.unresolved_records = sum(record.resolution_status == "unresolved" for record in records)
    batch.status = "completed"
    db.commit()
    db.refresh(batch)
    return batch
