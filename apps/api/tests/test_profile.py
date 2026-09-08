from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.constants import DEMO_USER_ID
from app.models import Artist, ImportBatch, ListeningEvent, ProfileSnapshot, RawImportRecord, Track, User
from app.profile import calculate_profiles, refresh_relationships
from app.routes import DEFAULT_USER_ID
from app.main import app

client = TestClient(app)


def test_relationships_aggregate_replays_favorites_and_completion() -> None:
    db = SessionLocal()
    try:
        relationships = refresh_relationships(db, DEMO_USER_ID)
        relationship = next(item for item in relationships if item.play_count > 1)
        assert relationship.replay_count > 0
        assert relationship.favorite_state is True
        assert relationship.completion_avg is not None
        assert relationship.first_seen_at <= relationship.last_played_at
    finally:
        db.close()


def test_profiles_have_distinct_long_and_recent_windows() -> None:
    db = SessionLocal()
    try:
        profiles = calculate_profiles(db, DEMO_USER_ID, datetime(2025, 3, 3, tzinfo=timezone.utc))
        long_term = profiles["long_term"].features
        short_term = profiles["short_term"].features
        assert long_term["summary"]["unique_tracks"] > short_term["summary"]["unique_tracks"]
        assert long_term["summary"]["unique_artists"] > short_term["summary"]["unique_artists"]
        assert long_term["parameters"]["recent_window_days"] == 30
    finally:
        db.close()


def test_excluded_events_do_not_enter_effective_profile() -> None:
    db = SessionLocal()
    user_id = uuid4()
    try:
        track = db.scalar(select(Track).join(Artist, Track.primary_artist_id == Artist.id))
        db.add(User(id=user_id))
        db.flush()
        batch = ImportBatch(user_id=user_id, source_type="test", source_metadata={})
        db.add(batch)
        db.flush()
        raw = RawImportRecord(batch_id=batch.id, raw_payload={"artist": "excluded"}, excluded=True, resolution_status="unresolved", resolved_track_id=track.id)
        db.add(raw)
        db.flush()
        db.add(ListeningEvent(user_id=user_id, track_id=track.id, raw_record_id=raw.id, played_at=datetime.now(timezone.utc), completion_ratio=1.0))
        db.commit()
        relationships = refresh_relationships(db, user_id)
        assert relationships[0].excluded is True
        profiles = calculate_profiles(db, user_id)
        assert profiles["long_term"].features["summary"] == {}
    finally:
        db.close()


def test_profile_get_does_not_persist_snapshots() -> None:
    db = SessionLocal()
    try:
        before = db.scalar(select(func.count(ProfileSnapshot.id)).where(ProfileSnapshot.user_id == DEFAULT_USER_ID))
        response = client.get("/api/v1/profile")
        after = db.scalar(select(func.count(ProfileSnapshot.id)).where(ProfileSnapshot.user_id == DEFAULT_USER_ID))
        assert response.status_code == 200
        assert before == after
    finally:
        db.close()
