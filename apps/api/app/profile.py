import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Artist, ListeningEvent, ProfileSnapshot, RawImportRecord, Track, UserLibraryTrack, UserTrackRelationship

RECENT_WINDOW_DAYS = 30
RECENCY_HALF_LIFE_DAYS = 14


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def effective_events(db: Session, user_id: UUID, as_of: datetime | None = None) -> list[tuple[ListeningEvent, Track, Artist]]:
    query = (
        select(ListeningEvent, Track, Artist)
        .join(RawImportRecord, ListeningEvent.raw_record_id == RawImportRecord.id)
        .join(Track, ListeningEvent.track_id == Track.id)
        .join(Artist, Track.primary_artist_id == Artist.id)
        .where(ListeningEvent.user_id == user_id, RawImportRecord.excluded.is_(False), ListeningEvent.track_id.is_not(None))
    )
    if as_of:
        query = query.where(ListeningEvent.played_at <= as_of)
    return list(db.execute(query).all())


def refresh_relationships(db: Session, user_id: UUID) -> list[UserTrackRelationship]:
    all_events = list(
        db.execute(
            select(ListeningEvent, RawImportRecord)
            .join(RawImportRecord, ListeningEvent.raw_record_id == RawImportRecord.id)
            .where(ListeningEvent.user_id == user_id, ListeningEvent.track_id.is_not(None))
        ).all()
    )
    active_by_track: dict[UUID, list[ListeningEvent]] = defaultdict(list)
    all_track_ids: set[UUID] = set()
    for event, raw in all_events:
        if event.track_id:
            all_track_ids.add(event.track_id)
            if not raw.excluded:
                active_by_track[event.track_id].append(event)

    memberships = list(db.scalars(select(UserLibraryTrack).where(UserLibraryTrack.user_id == user_id, UserLibraryTrack.active.is_(True))).all())
    memberships_by_track: dict[UUID, list[UserLibraryTrack]] = defaultdict(list)
    for membership in memberships:
        memberships_by_track[membership.track_id].append(membership)
        all_track_ids.add(membership.track_id)

    existing = {relation.track_id: relation for relation in db.scalars(select(UserTrackRelationship).where(UserTrackRelationship.user_id == user_id)).all()}
    all_track_ids.update(existing)
    for track_id in all_track_ids:
        relation = existing.get(track_id) or UserTrackRelationship(user_id=user_id, track_id=track_id)
        events = sorted(active_by_track.get(track_id, []), key=lambda item: aware(item.played_at) or datetime.min.replace(tzinfo=timezone.utc))
        library_items = memberships_by_track.get(track_id, [])
        relation.in_library = bool(library_items)
        relation.first_library_imported_at = min((aware(item.imported_at) for item in library_items), default=None)
        relation.library_source_count = len({(item.source_type, item.source_name) for item in library_items})
        relation.excluded = not events and not library_items
        relation.play_count = len(events)
        relation.replay_count = max(0, len(events) - 1)
        relation.first_seen_at = aware(events[0].played_at) if events else None
        relation.last_played_at = aware(events[-1].played_at) if events else None
        ratios = [event.completion_ratio for event in events if event.completion_ratio is not None]
        relation.completion_avg = sum(ratios) / len(ratios) if ratios else None
        relation.completed_count = sum((event.completion_ratio or 0) >= 0.8 for event in events)
        relation.skip_count = sum(event.event_type == "skip" or (event.completion_ratio is not None and event.completion_ratio < 0.35) for event in events)
        relation.total_duration_played_ms = sum(event.duration_played_ms or 0 for event in events)
        relation.favorite_state = any(event.is_favorite or event.event_type in {"favorite", "like"} for event in events)
        feedback = [event.event_type for event in events if event.event_type in {"like", "dislike"}]
        relation.explicit_feedback = feedback[-1] if feedback else None
        relation.discovery_source = next((event.context.get("source") for event in reversed(events) if event.context.get("source")), None) or (library_items[0].source_type if library_items else None)
        relation.updated_at = utc_now()
        db.add(relation)
    db.commit()
    return list(db.scalars(select(UserTrackRelationship).where(UserTrackRelationship.user_id == user_id).order_by(UserTrackRelationship.last_played_at.desc().nullslast())).all())


def profile_features(db: Session, user_id: UUID, profile_type: str, as_of: datetime | None = None) -> tuple[dict, datetime | None, datetime | None]:
    rows = effective_events(db, user_id, as_of)
    timestamps = [aware(event.played_at) for event, _, _ in rows if event.played_at]
    reference = as_of or (max(timestamps) if timestamps else utc_now())
    window_start = reference - timedelta(days=RECENT_WINDOW_DAYS) if profile_type == "short_term" else (min(timestamps) if timestamps else reference)
    membership_query = select(UserLibraryTrack, Track, Artist).join(Track, UserLibraryTrack.track_id == Track.id).join(Artist, Track.primary_artist_id == Artist.id).where(UserLibraryTrack.user_id == user_id, UserLibraryTrack.active.is_(True))
    if as_of:
        membership_query = membership_query.where(UserLibraryTrack.imported_at <= as_of)
    memberships = [] if profile_type == "short_term" else list(db.execute(membership_query).all())
    unique_memberships: dict[UUID, tuple[UserLibraryTrack, Track, Artist]] = {}
    for membership, track, artist in memberships:
        unique_memberships.setdefault(track.id, (membership, track, artist))
    memberships = list(unique_memberships.values())
    if not rows and not memberships:
        return {"schema_version": 1, "profile_type": profile_type, "summary": {}, "artists": [], "genres": []}, None, as_of
    artist_scores: dict[str, dict] = {}
    genre_scores: dict[str, float] = defaultdict(float)
    total_weight = 0.0
    completed = 0
    skips = 0
    favorites = 0
    recent_replays = 0
    seen_tracks: set[UUID] = set()
    included_events = 0
    for event, track, artist in rows:
        played_at = aware(event.played_at)
        if not played_at or played_at < window_start:
            continue
        if profile_type == "short_term":
            age_days = max(0.0, (reference - played_at).total_seconds() / 86400)
            weight = math.exp(-math.log(2) * age_days / RECENCY_HALF_LIFE_DAYS)
        else:
            weight = 1.0
        signal = weight * (1.0 + (event.completion_ratio or 0) * 0.5 + (1.0 if event.is_favorite else 0.0))
        artist_data = artist_scores.setdefault(str(artist.id), {"artist_id": str(artist.id), "name": artist.canonical_name, "score": 0.0, "play_count": 0})
        artist_data["score"] += signal
        artist_data["play_count"] += 1
        genre = (track.metadata_json or {}).get("genre")
        if genre:
            genre_scores[str(genre)] += signal
        total_weight += weight
        included_events += 1
        completed += (event.completion_ratio or 0) >= 0.8
        skips += event.event_type == "skip" or (event.completion_ratio is not None and event.completion_ratio < 0.35)
        favorites += event.is_favorite
        recent_replays += event.event_type == "replay"
        seen_tracks.add(track.id)
    if profile_type == "long_term":
        for _, track, artist in memberships:
            artist_data = artist_scores.setdefault(str(artist.id), {"artist_id": str(artist.id), "name": artist.canonical_name, "score": 0.0, "play_count": 0})
            artist_data["score"] += 0.6
            genre = (track.metadata_json or {}).get("genre")
            if genre:
                genre_scores[str(genre)] += 0.6
            seen_tracks.add(track.id)
    complete_artists = sorted(artist_scores.values(), key=lambda item: (-item["score"], item["name"]))
    artists = complete_artists[:10]
    genres = [{"name": name, "score": round(score, 4)} for name, score in sorted(genre_scores.items(), key=lambda item: (-item[1], item[0]))[:10]]
    complete_genres = [{"name": name, "score": round(score, 4)} for name, score in sorted(genre_scores.items(), key=lambda item: (-item[1], item[0]))]
    features = {"schema_version": 1, "profile_type": profile_type, "summary": {"weighted_plays": round(total_weight, 4), "unique_tracks": len(seen_tracks), "unique_artists": len(artist_scores), "library_tracks": len(unique_memberships), "favorites": favorites, "completion_rate": round(completed / included_events, 4) if included_events else None, "skip_rate": round(skips / included_events, 4) if included_events else None, "replays": recent_replays}, "artists": artists, "genres": genres, "artist_affinity": complete_artists, "genre_affinity": complete_genres, "parameters": {"recent_window_days": RECENT_WINDOW_DAYS, "recency_half_life_days": RECENCY_HALF_LIFE_DAYS, "library_membership_weight": 0.6}}
    return features, window_start, reference


def calculate_profiles(db: Session, user_id: UUID, as_of: datetime | None = None, persist: bool = False) -> dict[str, ProfileSnapshot]:
    refresh_relationships(db, user_id)
    snapshots: dict[str, ProfileSnapshot] = {}
    for profile_type in ("long_term", "short_term"):
        features, start, end = profile_features(db, user_id, profile_type, as_of if as_of is not None else None)
        if persist:
            snapshot = db.scalar(select(ProfileSnapshot).where(ProfileSnapshot.user_id == user_id, ProfileSnapshot.profile_type == profile_type, ProfileSnapshot.window_start == start, ProfileSnapshot.window_end == end))
            if snapshot is None:
                snapshot = ProfileSnapshot(user_id=user_id, profile_type=profile_type, window_start=start, window_end=end, window_days=RECENT_WINDOW_DAYS if profile_type == "short_term" else None)
            snapshot.features = features
            snapshot.calculated_at = utc_now()
            db.add(snapshot)
        else:
            snapshot = ProfileSnapshot(user_id=user_id, profile_type=profile_type, window_start=start, window_end=end, window_days=RECENT_WINDOW_DAYS if profile_type == "short_term" else None, features=features, calculated_at=utc_now())
        snapshots[profile_type] = snapshot
    if persist:
        db.commit()
    return snapshots
