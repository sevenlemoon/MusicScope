"""Print a deterministic, human-readable recommendation MVP evaluation."""

from collections import Counter
from statistics import mean
from uuid import UUID

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Artist, Track
from app.recommendation import generate_recommendations

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
LEVELS = (10, 50, 90)


def evaluate(level: int) -> dict:
    db = SessionLocal()
    try:
        _, recommendations = generate_recommendations(db, DEFAULT_USER_ID, level, limit=12)
        tracks = {track.id: (track, artist) for track, artist in db.execute(select(Track, Artist).join(Artist, Track.primary_artist_id == Artist.id)).all()}
        artists = [tracks[item.track_id][1].canonical_name for item in recommendations]
        genres = [str((tracks[item.track_id][0].metadata_json or {}).get("genre", "unknown")) for item in recommendations]
        novelty = [float(item.score_breakdown.get("novelty", 0.0)) for item in recommendations]
        unfamiliar = [value for value in novelty if value >= 0.8]
        evidence_count = sum(bool(item.explanation_evidence) for item in recommendations)
        return {
            "exploration": level,
            "roles": dict(Counter(item.role for item in recommendations)),
            "unique_artists": len(set(artists)),
            "unique_genres": len(set(genres)),
            "max_artist_share": round(max(Counter(artists).values(), default=0) / max(1, len(artists)), 3),
            "mean_novelty": round(mean(novelty), 3) if novelty else 0.0,
            "unfamiliar_artist_ratio": round(len(unfamiliar) / max(1, len(recommendations)), 3),
            "explanation_coverage": round(evidence_count / max(1, len(recommendations)), 3),
            "track_ids": [str(item.track_id) for item in recommendations],
        }
    finally:
        db.close()


if __name__ == "__main__":
    for level in LEVELS:
        print(evaluate(level))
