from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.main import app
from app.models import ImportBatch, ListeningEvent, RawImportRecord, Track, User
from app.routes import DEFAULT_USER_ID
from app.timeline import generate_timeline

client = TestClient(app)


def test_demo_timeline_is_deterministic_and_has_meaningful_periods() -> None:
    db = SessionLocal()
    try:
        first = generate_timeline(db, DEFAULT_USER_ID)
        first_shape = [(period.start_at, period.change_score, period.evidence) for period in first]
        second = generate_timeline(db, DEFAULT_USER_ID)
        second_shape = [(period.start_at, period.change_score, period.evidence) for period in second]
        assert first_shape == second_shape
        assert len(first) >= 3
        assert all(period.change_score >= 0.20 for period in first)
        response = client.get("/api/v1/timeline")
        assert response.status_code == 200
        response = client.post("/api/v1/timeline/recalculate")
        assert response.status_code == 200
    finally:
        db.close()


def test_threshold_suppresses_small_changes() -> None:
    db = SessionLocal()
    try:
        periods = generate_timeline(db, DEFAULT_USER_ID, threshold=0.99)
        assert periods == []
    finally:
        generate_timeline(db, DEFAULT_USER_ID)
        db.close()


def test_excluded_year_does_not_create_a_false_change() -> None:
    db = SessionLocal()
    user_id = uuid4()
    try:
        db.add(User(id=user_id))
        db.flush()
        first_track = db.scalar(select(Track))
        second_track = next(item for item in db.scalars(select(Track)).all() if item.primary_artist_id != first_track.primary_artist_id and (item.metadata_json or {}).get("genre") != (first_track.metadata_json or {}).get("genre"))
        tracks = [first_track, second_track]
        batch = ImportBatch(user_id=user_id, source_type="test", source_metadata={})
        db.add(batch)
        db.flush()
        for index, track in enumerate(tracks):
            raw = RawImportRecord(batch_id=batch.id, raw_payload={"title": track.canonical_title}, resolution_status="resolved", resolved_track_id=track.id, excluded=index == 1)
            db.add(raw)
            db.flush()
            db.add(ListeningEvent(user_id=user_id, track_id=track.id, raw_record_id=raw.id, played_at=datetime(2021 + index, 6, 1, tzinfo=timezone.utc), completion_ratio=0.9))
        db.commit()
        assert generate_timeline(db, user_id, threshold=0.0) == []
        raw_records = list(db.scalars(select(RawImportRecord).where(RawImportRecord.batch_id == batch.id)))
        raw_records[1].excluded = False
        db.commit()
        assert len(generate_timeline(db, user_id, threshold=0.0)) == 1
    finally:
        db.execute(delete(User).where(User.id == user_id))
        db.commit()
        db.close()


def test_memories_can_be_created_edited_and_deleted() -> None:
    db = SessionLocal()
    try:
        track = db.scalar(select(Track))
        response = client.post("/api/v1/memories", json={"target_type": "track", "target_id": str(track.id), "text": "A personal note"})
        assert response.status_code == 201
        memory_id = response.json()["id"]
        response = client.patch(f"/api/v1/memories/{memory_id}", json={"text": "An edited personal note"})
        assert response.status_code == 200
        assert response.json()["text"] == "An edited personal note"
        assert client.delete(f"/api/v1/memories/{memory_id}").status_code == 204
    finally:
        db.close()
