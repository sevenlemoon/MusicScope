"""Create a deterministic catalog and listening import for local demos."""

from datetime import datetime, timezone
from sqlalchemy import select

from app.db import SessionLocal
from app.constants import DEMO_USER_ID
from app.importer import import_rows, normalize_text
from app.models import Album, Artist, Track, TrackArtist, User, UserSettings, UserTrackRelationship
from app.timeline import generate_timeline
from app.models import Memory

DEFAULT_USER_ID = DEMO_USER_ID
GENRES = ["indie rock", "electronic", "soul", "jazz", "hip-hop", "folk", "ambient", "pop"]


def main() -> None:
    db = SessionLocal()
    try:
        user = db.get(User, DEFAULT_USER_ID)
        if not user:
            user = User(id=DEFAULT_USER_ID)
            db.add(user)
            db.add(UserSettings(user_id=DEFAULT_USER_ID))
            db.flush()
        if db.scalar(select(UserTrackRelationship.id).where(UserTrackRelationship.user_id == DEFAULT_USER_ID).limit(1)):
            periods = generate_timeline(db, DEFAULT_USER_ID)
            if periods and not db.scalar(select(Memory.id).where(Memory.user_id == DEFAULT_USER_ID)):
                db.add(Memory(user_id=DEFAULT_USER_ID, target_type="timeline_period", target_id=periods[0].id, text="A demo memory attached to this listening period."))
                db.commit()
            print(f"Demo catalog already exists; verified {len(periods)} timeline periods and demo memory.")
            return

        rows: list[dict[str, str]] = []
        for artist_index in range(50):
            artist_name = f"Demo Artist {artist_index + 1:02d}"
            artist = Artist(canonical_name=artist_name, normalized_name=normalize_text(artist_name), metadata_json={"genre": GENRES[artist_index % len(GENRES)]})
            db.add(artist)
            db.flush()
            for track_index in range(4):
                album_name = f"Period {artist_index // 10 + 1} Sessions"
                album = db.scalar(select(Album).where(Album.artist_id == artist.id, Album.normalized_title == normalize_text(album_name)))
                if not album:
                    album = Album(artist_id=artist.id, canonical_title=album_name, normalized_title=normalize_text(album_name))
                    db.add(album)
                    db.flush()
                title = f"{GENRES[artist_index % len(GENRES)].title()} Sketch {track_index + 1:02d}"
                track = Track(canonical_title=title, normalized_title=normalize_text(title), primary_artist_id=artist.id, album_id=album.id, duration_ms=180000 + track_index * 15000, metadata_json={"genre": GENRES[artist_index % len(GENRES)], "demo": True})
                db.add(track)
                db.flush()
                db.add(TrackArtist(track_id=track.id, artist_id=artist.id, role="primary"))
                period = artist_index // 10
                played_at = datetime(2021 + period, 2 + (artist_index % 8), 5 + track_index, 18, 30, tzinfo=timezone.utc)
                rows.append({"artist": artist_name, "title": title, "album": album_name, "played_at": played_at.isoformat(), "duration_played_ms": str(180000 + track_index * 15000), "completion_ratio": "0.92" if track_index != 3 else "0.28", "event_type": "favorite" if track_index == 0 else "play", "favorite": "true" if track_index == 0 else "false", "source_record_id": f"demo-{artist_index:02d}-{track_index:02d}", "source": "deterministic-demo"})

                if track_index == 0:
                    rows.append({**rows[-1], "played_at": datetime(2025, 1 + (artist_index % 3), 10 + track_index, 20, 0, tzinfo=timezone.utc).isoformat(), "event_type": "replay", "source_record_id": f"demo-recent-{artist_index:02d}"})

        rows.extend([
            {"artist": "Unknown Import Artist", "title": "Unmatched Song", "album": "Mystery", "played_at": "2025-03-01T12:00:00+00:00", "source_record_id": "demo-unresolved-1", "source": "deterministic-demo"},
            {"artist": "Demo Artist 01", "title": "Live Set Not In Catalog", "album": "Bootleg", "played_at": "2025-03-02T12:00:00+00:00", "source_record_id": "demo-unresolved-2", "source": "deterministic-demo"},
        ])
        db.commit()
        batch = import_rows(db, DEFAULT_USER_ID, rows, {"filename": "deterministic-demo", "description": "50 artists, 200 tracks, multiple periods and feedback types"})
        periods = generate_timeline(db, DEFAULT_USER_ID)
        if periods and not db.scalar(select(Memory.id).where(Memory.user_id == DEFAULT_USER_ID)):
            db.add(Memory(user_id=DEFAULT_USER_ID, target_type="timeline_period", target_id=periods[0].id, text="A demo memory attached to this listening period."))
            db.commit()
        print(f"Created {len(set(row['artist'] for row in rows))} artists, 200 canonical tracks, {batch.total_records} listening records in batch {batch.id}, and {len(periods)} timeline periods.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
