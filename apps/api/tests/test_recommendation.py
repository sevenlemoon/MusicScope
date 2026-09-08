from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.models import Artist, FeedbackEvent, ImportBatch, ListeningEvent, ProfileSnapshot, RawImportRecord, Track, User
from app.recommendation import feedback_penalties, generate_recommendations
from app.routes import DEFAULT_USER_ID


def test_fixed_recommendation_run_is_deterministic_and_diverse() -> None:
    db = SessionLocal()
    try:
        _, first = generate_recommendations(db, DEFAULT_USER_ID, 50, 12)
        _, second = generate_recommendations(db, DEFAULT_USER_ID, 50, 12)
        assert [(item.track_id, item.role, item.score) for item in first] == [(item.track_id, item.role, item.score) for item in second]
        tracks = {track.id: track for track in db.scalars(select(Track)).all()}
        artists = {artist.id: artist for artist in db.scalars(select(Artist)).all()}
        artist_counts = Counter(str(artists[tracks[item.track_id].primary_artist_id].id) for item in first)
        assert max(artist_counts.values()) <= 3
    finally:
        db.close()


def test_exploration_changes_roles_and_novelty() -> None:
    db = SessionLocal()
    try:
        runs = {level: generate_recommendations(db, DEFAULT_USER_ID, level, 12)[1] for level in (10, 50, 90)}
        role_counts = {level: Counter(item.role for item in items) for level, items in runs.items()}
        assert role_counts[10] != role_counts[90]
        low_novelty = sum(item.score_breakdown["novelty"] for item in runs[10]) / 12
        high_novelty = sum(item.score_breakdown["novelty"] for item in runs[90]) / 12
        assert high_novelty >= low_novelty
        assert {item.track_id for item in runs[10]} != {item.track_id for item in runs[90]}
    finally:
        db.close()


def test_negative_feedback_and_skip_reasons_have_different_strengths() -> None:
    db = SessionLocal()
    user_id = uuid4()
    try:
        db.add(User(id=user_id))
        db.commit()
        track = db.scalar(select(Track))
        db.add(FeedbackEvent(user_id=user_id, track_id=track.id, event_type="skip", reason="NOT_FOR_TODAY"))
        db.commit()
        contextual = feedback_penalties(db, user_id)[track.id]
        db.add(FeedbackEvent(user_id=user_id, track_id=track.id, event_type="dislike", reason="SIMPLY_DISLIKE"))
        db.commit()
        strong = feedback_penalties(db, user_id)[track.id]
        assert strong > contextual
    finally:
        db.execute(delete(User).where(User.id == user_id))
        db.commit()
        db.close()


def test_excluded_tracks_and_profile_get_do_not_leak_or_create_snapshots() -> None:
    db = SessionLocal()
    user_id = uuid4()
    try:
        db.add(User(id=user_id))
        db.flush()
        track = db.scalar(select(Track))
        batch = ImportBatch(user_id=user_id, source_type="test", source_metadata={})
        db.add(batch)
        db.flush()
        raw = RawImportRecord(batch_id=batch.id, raw_payload={"title": "excluded"}, resolution_status="resolved", resolved_track_id=track.id, excluded=True)
        db.add(raw)
        db.flush()
        db.add(ListeningEvent(user_id=user_id, track_id=track.id, raw_record_id=raw.id, played_at=datetime.now(timezone.utc)))
        db.commit()
        before = db.scalar(select(func.count(ProfileSnapshot.id)).where(ProfileSnapshot.user_id == DEFAULT_USER_ID))
        _, recommendations = generate_recommendations(db, user_id, 50, 12)
        assert track.id not in {item.track_id for item in recommendations}
        from app.profile import calculate_profiles
        calculate_profiles(db, DEFAULT_USER_ID)
        after = db.scalar(select(func.count(ProfileSnapshot.id)).where(ProfileSnapshot.user_id == DEFAULT_USER_ID))
        assert before == after
    finally:
        db.execute(delete(User).where(User.id == user_id))
        db.commit()
        db.close()


def test_explanations_reference_stored_scoring_evidence() -> None:
    db = SessionLocal()
    try:
        _, recommendations = generate_recommendations(db, DEFAULT_USER_ID, 90, 12)
        assert recommendations
        for item in recommendations:
            assert item.explanation_evidence
            assert all("signal" in evidence and "text" in evidence and "value" in evidence for evidence in item.explanation_evidence)
            assert item.score_breakdown["exploration"] == 0.9
    finally:
        db.close()

