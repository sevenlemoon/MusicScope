from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Artist, FeedbackEvent, Recommendation, RecommendationRun, Track
from .profile import calculate_profiles, refresh_relationships

ROLE_NAMES = ("PRECISE_MATCH", "ADJACENT_EXPLORATION", "CROSS_BOUNDARY_DISCOVERY", "BOLD_TRY")
SKIP_REASONS = {"TOO_LOUD", "TOO_SLOW", "DISLIKE_VOCALS", "NOT_FOR_TODAY", "SIMPLY_DISLIKE"}


@dataclass(frozen=True)
class RecommendationWeights:
    long_term: float
    short_term: float
    relationship: float
    novelty: float

    @classmethod
    def for_exploration(cls, exploration: float) -> "RecommendationWeights":
        return cls(long_term=0.40 - 0.18 * exploration, short_term=0.28 - 0.10 * exploration, relationship=0.18 - 0.10 * exploration, novelty=0.14 + 0.38 * exploration)


@dataclass
class Candidate:
    track: Track
    artist: Artist
    genre: str
    score: float
    role: str
    breakdown: dict[str, float]
    evidence: list[dict[str, Any]]


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def profile_maps(profile: dict) -> tuple[dict[str, float], dict[str, float]]:
    artists = {item["artist_id"]: float(item["score"]) for item in profile.get("artist_affinity", profile.get("artists", []))}
    genres = {item["name"]: float(item["score"]) for item in profile.get("genre_affinity", profile.get("genres", []))}
    artist_max = max(artists.values(), default=1.0)
    genre_max = max(genres.values(), default=1.0)
    return ({key: value / artist_max for key, value in artists.items()}, {key: value / genre_max for key, value in genres.items()})


def feedback_penalties(db: Session, user_id: UUID) -> dict[UUID, float]:
    penalties: dict[UUID, float] = {}
    for event in db.scalars(select(FeedbackEvent).where(FeedbackEvent.user_id == user_id).order_by(FeedbackEvent.created_at)).all():
        if event.event_type == "dislike" or event.reason == "SIMPLY_DISLIKE":
            penalties[event.track_id] = min(0.85, penalties.get(event.track_id, 0.0) + 0.55)
        elif event.reason == "NOT_FOR_TODAY":
            penalties[event.track_id] = min(0.35, penalties.get(event.track_id, 0.0) + 0.18)
        elif event.event_type == "skip":
            penalties[event.track_id] = min(0.25, penalties.get(event.track_id, 0.0) + 0.05)
        elif event.event_type == "like":
            penalties[event.track_id] = max(-0.15, penalties.get(event.track_id, 0.0) - 0.15)
    return penalties


def role_for(*, long_match: float, artist_match: float, genre_match: float, novelty: float, exploration: float) -> str:
    if (long_match >= 0.62 or (genre_match == 0 and artist_match >= 0.8)) and novelty <= 0.55:
        return "PRECISE_MATCH"
    if genre_match >= 0.42 and novelty <= 0.82:
        return "ADJACENT_EXPLORATION"
    if exploration >= 0.5 and (genre_match < 0.42 or novelty > 0.7):
        return "CROSS_BOUNDARY_DISCOVERY"
    return "BOLD_TRY"


def role_quota(exploration: float, limit: int) -> dict[str, int]:
    if exploration < 0.25:
        proportions = [0.58, 0.34, 0.08, 0.0]
    elif exploration < 0.6:
        proportions = [0.34, 0.34, 0.24, 0.08]
    else:
        proportions = [0.16, 0.25, 0.34, 0.25]
    quota = {role: int(limit * proportion) for role, proportion in zip(ROLE_NAMES, proportions)}
    while sum(quota.values()) < limit:
        role = ROLE_NAMES[sum(quota.values()) % len(ROLE_NAMES)]
        quota[role] += 1
    return quota


def make_evidence(candidate: Candidate, exploration: float) -> list[dict[str, Any]]:
    b = candidate.breakdown
    evidence: list[dict[str, Any]] = []
    if b["genre_match"] >= 0.5 and candidate.genre:
        evidence.append({"signal": "long_term_genre", "value": round(b["long_match"], 3), "text": f"matches a strong long-term {candidate.genre} preference"})
    elif b["artist_match"] >= 0.5:
        evidence.append({"signal": "artist_affinity", "value": round(b["artist_match"], 3), "text": "matches an artist in your music library"})
    if b["short_match"] >= 0.45:
        evidence.append({"signal": "short_term_state", "value": round(b["short_match"], 3), "text": "matches your recent listening state"})
    if b["relationship"] >= 0.5:
        evidence.append({"signal": "relationship", "value": round(b["relationship"], 3), "text": "builds on a frequently replayed or completed relationship"})
    if b["novelty"] >= 0.55:
        evidence.append({"signal": "novelty", "value": round(b["novelty"], 3), "text": "comes from an unfamiliar or lightly played artist"})
    if exploration >= 0.6 and b["long_match"] < 0.45:
        evidence.append({"signal": "exploration", "value": round(exploration, 2), "text": "selected as a cross-boundary option because exploration is high"})
    if b["negative_penalty"] > 0:
        evidence.append({"signal": "feedback_penalty", "value": round(b["negative_penalty"], 3), "text": "down-ranked by recent negative feedback"})
    return evidence or [{"signal": "balanced_match", "value": round(candidate.score, 3), "text": "balances profile fit, freshness, and diversity"}]


def generate_recommendations(db: Session, user_id: UUID, exploration_level: float, limit: int = 12) -> tuple[RecommendationRun, list[Recommendation]]:
    exploration = clamp(exploration_level / 100)
    relationships = refresh_relationships(db, user_id)
    relationship_by_track = {item.track_id: item for item in relationships}
    profiles = calculate_profiles(db, user_id)
    long_artists, long_genres = profile_maps(profiles["long_term"].features)
    short_artists, short_genres = profile_maps(profiles["short_term"].features)
    recent_artist_ids = set(short_artists)
    penalties = feedback_penalties(db, user_id)
    latest_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    tracks = list(db.execute(select(Track, Artist).join(Artist, Track.primary_artist_id == Artist.id).order_by(Track.id)).all())
    candidates: list[Candidate] = []
    weights = RecommendationWeights.for_exploration(exploration)
    for track, artist in tracks:
        relation = relationship_by_track.get(track.id)
        if relation is None or relation.excluded:
            continue
        genre = str((track.metadata_json or {}).get("genre") or "")
        long_artist = long_artists.get(str(artist.id), 0.0)
        short_artist = short_artists.get(str(artist.id), 0.0)
        long_genre = long_genres.get(genre, 0.0)
        short_genre = short_genres.get(genre, 0.0)
        long_match = 0.55 * long_artist + 0.45 * long_genre
        short_match = 0.55 * short_artist + 0.45 * short_genre
        plays = relation.play_count if relation else 0
        novelty = max(0.08, 0.25 - min(plays / 3, 0.17)) if relation.in_library else max(0.15, 1.0 - min(plays / 3, 1.0))
        if not relation.in_library and str(artist.id) not in recent_artist_ids:
            novelty = min(1.0, novelty + 0.2)
        relationship = 0.0 if not relation else clamp(min(plays / 4, 1.0) * 0.55 + (0.45 if relation.favorite_state else 0.0))
        repetition = 1.0 if relation and relation.last_played_at and relation.last_played_at >= latest_cutoff else 0.0
        negative_penalty = penalties.get(track.id, 0.0)
        score = weights.long_term * long_match + weights.short_term * short_match + weights.relationship * relationship + weights.novelty * novelty - 0.12 * repetition - negative_penalty
        breakdown = {"long_match": round(long_match, 4), "short_match": round(short_match, 4), "artist_match": round(long_artist, 4), "genre_match": round(long_genre, 4), "relationship": round(relationship, 4), "novelty": round(novelty, 4), "repetition_penalty": round(0.12 * repetition, 4), "negative_penalty": round(negative_penalty, 4), "exploration": round(exploration, 4)}
        candidate = Candidate(track, artist, genre, round(score, 6), role_for(long_match=long_match, artist_match=long_artist, genre_match=long_genre, novelty=novelty, exploration=exploration), breakdown, [])
        candidate.evidence = make_evidence(candidate, exploration)
        candidates.append(candidate)
    candidates.sort(key=lambda item: (-item.score, str(item.track.id)))
    selected = select_diverse(candidates, role_quota(exploration, limit), limit)
    run = RecommendationRun(user_id=user_id, exploration_level=exploration_level, context={"pipeline_version": 1, "limit": limit, "profile_window_days": 30})
    db.add(run)
    db.flush()
    persisted: list[Recommendation] = []
    for rank, candidate in enumerate(selected, 1):
        item = Recommendation(run_id=run.id, track_id=candidate.track.id, score=candidate.score, role=candidate.role, rank=rank, explanation_evidence=candidate.evidence, score_breakdown=candidate.breakdown)
        db.add(item)
        persisted.append(item)
    db.commit()
    return run, persisted


def select_diverse(candidates: list[Candidate], quota: dict[str, int], limit: int) -> list[Candidate]:
    pools = {role: [candidate for candidate in candidates if candidate.role == role] for role in ROLE_NAMES}
    selected: list[Candidate] = []
    used: set[UUID] = set()
    artist_counts: dict[UUID, int] = {}
    genre_counts: dict[str, int] = {}
    def diversity_genre(candidate: Candidate) -> str:
        return candidate.genre or f"unknown:{candidate.track.id}"

    def allowed(candidate: Candidate) -> bool:
        # Small libraries should still produce all available results.
        artist_cap = 3 if len({item.artist.id for item in candidates}) >= 3 else limit
        genre_cap = 5 if len({diversity_genre(item) for item in candidates}) >= 3 else limit
        return artist_counts.get(candidate.artist.id, 0) < artist_cap and genre_counts.get(diversity_genre(candidate), 0) < genre_cap

    for role in ROLE_NAMES:
        while quota[role] and pools[role]:
            candidate = max(pools[role], key=lambda item: item.score - 0.08 * artist_counts.get(item.artist.id, 0) - 0.04 * genre_counts.get(diversity_genre(item), 0))
            pools[role].remove(candidate)
            quota[role] -= 1
            if candidate.track.id in used:
                continue
            if not allowed(candidate):
                continue
            selected.append(candidate)
            used.add(candidate.track.id)
            artist_counts[candidate.artist.id] = artist_counts.get(candidate.artist.id, 0) + 1
            genre = diversity_genre(candidate)
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
    remaining = [candidate for candidate in candidates if candidate.track.id not in used]
    for candidate in sorted(remaining, key=lambda item: (-item.score, str(item.track.id))):
        if len(selected) >= limit:
            break
        if not allowed(candidate):
            continue
        selected.append(candidate)
        used.add(candidate.track.id)
        artist_counts[candidate.artist.id] = artist_counts.get(candidate.artist.id, 0) + 1
        genre = diversity_genre(candidate)
        genre_counts[genre] = genre_counts.get(genre, 0) + 1
    return selected[:limit]
