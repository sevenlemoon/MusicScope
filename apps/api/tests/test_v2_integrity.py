from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, func, select

from app.constants import DEMO_USER_ID, PERSONAL_USER_ID
from app.concerts import relevant_artists
from app.db import SessionLocal
from app.importer import import_library_rows, import_listening_rows
from app.models import Artist, ListeningEvent, Track, TrackArtist, User, UserLibraryTrack, UserTrackRelationship
from app.profile import calculate_profiles, refresh_relationships
from app.recommendation import generate_recommendations
from app.timeline import generate_timeline


def test_playlist_library_import_has_catalog_membership_but_no_play_events() -> None:
    db = SessionLocal()
    user_id = uuid4()
    rows = [
        {"title": "Can We Kiss Forever?", "artist": "Kina"},
        {"title": "Monody (Radio Edit)", "artist": "TheFatRat / Laura Brehm", "artists": ["TheFatRat", "Laura Brehm"]},
        {"title": "Tattoo", "artist": "GJan"},
    ]
    try:
        db.add(User(id=user_id))
        db.commit()
        batch = import_library_rows(db, user_id, rows, {"source_type": "assisted_playlist_text", "source_name": "integrity-test"})
        assert batch.total_records == 3
        assert db.scalar(select(func.count(UserLibraryTrack.id)).where(UserLibraryTrack.user_id == user_id)) == 3
        monody = db.scalar(select(Track).where(Track.normalized_title == "monody radio edit"))
        assert monody is not None
        artist_names = set(db.scalars(select(Artist.canonical_name).join(TrackArtist, TrackArtist.artist_id == Artist.id).where(TrackArtist.track_id == monody.id)).all())
        assert artist_names == {"TheFatRat", "Laura Brehm"}
        assert db.scalar(select(func.count(ListeningEvent.id)).where(ListeningEvent.user_id == user_id)) == 0
        assert db.scalar(select(func.count(Track.id)).where(Track.metadata_json["catalog_status"].as_string() == "imported")) >= 3
        tracks = refresh_relationships(db, user_id)
        assert all(item.in_library and item.play_count == 0 and item.replay_count == 0 and item.last_played_at is None for item in tracks)
        profiles = calculate_profiles(db, user_id)
        assert profiles["long_term"].features["summary"]["library_tracks"] == 3
        assert profiles["short_term"].features["summary"] == {}
        assert generate_timeline(db, user_id) == []
        import_library_rows(db, user_id, rows, {"source_type": "assisted_playlist_text", "source_name": "integrity-test"})
        assert db.scalar(select(func.count(Track.id)).where(Track.normalized_title.in_({"can we kiss forever", "monody radio edit", "tattoo"}), Track.primary_artist_id.is_not(None))) >= 3
        assert db.scalar(select(func.count(UserLibraryTrack.id)).where(UserLibraryTrack.user_id == user_id)) == 3
    finally:
        db.execute(delete(User).where(User.id == user_id))
        db.commit()
        db.close()


def test_real_listening_import_populates_short_term_without_changing_library_count() -> None:
    db = SessionLocal()
    user_id = uuid4()
    try:
        db.add(User(id=user_id))
        db.commit()
        import_library_rows(db, user_id, [{"title": "Integrity Song", "artist": "Integrity Artist"}], {"source_type": "assisted_playlist_text", "source_name": "integrity-list"})
        track = db.scalar(select(Track).where(Track.normalized_title == "integrity song"))
        import_listening_rows(db, user_id, [{"title": track.canonical_title, "artist": "Integrity Artist", "played_at": datetime.now(timezone.utc).isoformat(), "completion_ratio": "0.95"}], {"source_type": "csv_listening_history"})
        assert db.scalar(select(func.count(ListeningEvent.id)).where(ListeningEvent.user_id == user_id)) == 1
        assert calculate_profiles(db, user_id)["short_term"].features["summary"]["unique_tracks"] == 1
        assert db.scalar(select(func.count(UserLibraryTrack.id)).where(UserLibraryTrack.user_id == user_id)) == 1
    finally:
        db.execute(delete(User).where(User.id == user_id))
        db.commit()
        db.close()


def test_demo_identity_is_separate_from_personal_identity() -> None:
    db = SessionLocal()
    try:
        assert DEMO_USER_ID != PERSONAL_USER_ID
        assert db.scalar(select(func.count(UserTrackRelationship.id)).where(UserTrackRelationship.user_id == DEMO_USER_ID)) > 0
        assert db.scalar(select(func.count(UserTrackRelationship.id)).where(UserTrackRelationship.user_id == PERSONAL_USER_ID, UserTrackRelationship.discovery_source == "deterministic-demo")) == 0
        _, recommendations = generate_recommendations(db, PERSONAL_USER_ID, 50, 12)
        recommended_ids = {item.track_id for item in recommendations}
        leaked = db.scalar(select(func.count(UserTrackRelationship.id)).where(UserTrackRelationship.user_id == PERSONAL_USER_ID, UserTrackRelationship.track_id.in_(recommended_ids or [None]), UserTrackRelationship.discovery_source == "deterministic-demo"))
        assert leaked == 0
        assert all(not artist.canonical_name.startswith("Demo Artist ") for artist in relevant_artists(db, PERSONAL_USER_ID))
    finally:
        db.close()


def test_library_only_recommendations_are_bounded_and_do_not_claim_missing_genres() -> None:
    db = SessionLocal()
    user_id = uuid4()
    try:
        db.add(User(id=user_id))
        db.commit()
        import_library_rows(db, user_id, [{"title": "One Signal", "artist": "Plain Artist"}], {"source_type": "assisted_playlist_text", "source_name": "small-library"})
        _, first = generate_recommendations(db, user_id, 10, 12)
        assert len(first) == 1
        assert len({item.track_id for item in first}) == len(first)
        assert all(evidence["signal"] not in {"long_term_genre", "novelty"} for item in first for evidence in item.explanation_evidence)
        import_library_rows(db, user_id, [{"title": "Second Signal", "artist": "Second Artist"}, {"title": "Third Signal", "artist": "Third Artist"}], {"source_type": "assisted_playlist_text", "source_name": "small-library"})
        _, second = generate_recommendations(db, user_id, 90, 12)
        assert 1 <= len(second) <= 3
        assert len({item.track_id for item in second}) == len(second)
    finally:
        db.execute(delete(User).where(User.id == user_id))
        db.commit()
        db.close()
