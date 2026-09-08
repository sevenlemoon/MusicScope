from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import TimelinePeriod
from .profile import aware, calculate_profiles, effective_events, utc_now

CHANGE_THRESHOLD = 0.20


def year_window(year: int) -> tuple[datetime, datetime]:
    return datetime(year, 1, 1, tzinfo=timezone.utc), datetime(year + 1, 1, 1, tzinfo=timezone.utc)


def distribution(values: list[str]) -> dict[str, float]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[value] += 1
    total = max(1, len(values))
    return {key: value / total for key, value in counts.items()}


def shift(current: dict[str, float], previous: dict[str, float]) -> float:
    return sum(abs(current.get(key, 0.0) - previous.get(key, 0.0)) for key in set(current) | set(previous)) / 2


def period_metrics(rows: list[tuple], previous_seen_artists: set[str]) -> tuple[dict, set[str]]:
    genres = [str((track.metadata_json or {}).get("genre", "unknown")) for event, track, artist in rows]
    artists = [str(artist.id) for event, track, artist in rows]
    artist_names = {str(artist.id): artist.canonical_name for event, track, artist in rows}
    completions = [event.completion_ratio for event, _, _ in rows if event.completion_ratio is not None]
    skips = sum(event.event_type == "skip" or (event.completion_ratio is not None and event.completion_ratio < 0.35) for event, _, _ in rows)
    unique_artists = set(artists)
    new_artists = unique_artists - previous_seen_artists
    metrics = {"event_count": len(rows), "unique_artists": len(unique_artists), "unique_tracks": len({track.id for event, track, artist in rows}), "genre_shares": distribution(genres), "artist_shares": distribution(artists), "artist_names": artist_names, "new_artist_count": len(new_artists), "new_artist_rate": round(len(new_artists) / max(1, len(unique_artists)), 4), "average_completion": round(sum(completions) / len(completions), 4) if completions else None, "skip_rate": round(skips / max(1, len(rows)), 4), "is_demo": bool(rows) and all(bool((track.metadata_json or {}).get("demo")) for _, track, _ in rows)}
    return metrics, previous_seen_artists | unique_artists


def evidence_for(current: dict, previous: dict) -> list[dict]:
    evidence: list[dict] = []
    genre_changes = []
    for genre in set(current["genre_shares"]) | set(previous["genre_shares"]):
        delta = current["genre_shares"].get(genre, 0.0) - previous["genre_shares"].get(genre, 0.0)
        if abs(delta) >= 0.03:
            genre_changes.append((abs(delta), genre, delta))
    for _, genre, delta in sorted(genre_changes, reverse=True)[:4]:
        evidence.append({"signal": "genre_share", "name": genre, "delta": round(delta, 4), "text": f"{genre} {'+' if delta >= 0 else ''}{round(delta * 100)}%"})
    if current["new_artist_count"]:
        evidence.append({"signal": "new_artists", "value": current["new_artist_count"], "text": f"{current['new_artist_count']} new artists ({round(current['new_artist_rate'] * 100)}% of artists)"})
    if current["average_completion"] is not None and previous.get("average_completion") is not None and abs(current["average_completion"] - previous["average_completion"]) >= 0.05:
        delta = current["average_completion"] - previous["average_completion"]
        evidence.append({"signal": "completion", "delta": round(delta, 4), "text": f"average completion {'+' if delta >= 0 else ''}{round(delta * 100)}%"})
    if abs(current["skip_rate"] - previous.get("skip_rate", current["skip_rate"])) >= 0.05:
        delta = current["skip_rate"] - previous["skip_rate"]
        evidence.append({"signal": "skip_rate", "delta": round(delta, 4), "text": f"skip rate {'+' if delta >= 0 else ''}{round(delta * 100)}%"})
    if abs(current["event_count"] - previous["event_count"]) / max(1, previous["event_count"]) >= 0.25:
        evidence.append({"signal": "listening_frequency", "current": current["event_count"], "previous": previous["event_count"], "text": f"listening events changed from {previous['event_count']} to {current['event_count']}"})
    return evidence


def generate_timeline(db: Session, user_id: UUID, threshold: float = CHANGE_THRESHOLD) -> list[TimelinePeriod]:
    rows = effective_events(db, user_id)
    grouped: dict[int, list[tuple]] = defaultdict(list)
    for event, track, artist in rows:
        if event.played_at:
            grouped[aware(event.played_at).year].append((event, track, artist))
    existing = {(period.start_at, period.end_at): period for period in db.scalars(select(TimelinePeriod).where(TimelinePeriod.user_id == user_id)).all()}
    for period in existing.values():
        period.active = False
    previous_metrics = None
    seen_artists: set[str] = set()
    generated: list[TimelinePeriod] = []
    for year in sorted(grouped):
        start, end = year_window(year)
        metrics, seen_artists = period_metrics(grouped[year], seen_artists)
        calculate_profiles(db, user_id, end.replace(microsecond=1), persist=True)
        if previous_metrics is None:
            previous_metrics = metrics
            continue
        genre_shift = shift(metrics["genre_shares"], previous_metrics["genre_shares"])
        artist_shift = shift(metrics["artist_shares"], previous_metrics["artist_shares"])
        new_rate = metrics["new_artist_rate"]
        behavior_shift = abs((metrics["average_completion"] or 0) - (previous_metrics["average_completion"] or 0)) + abs(metrics["skip_rate"] - previous_metrics["skip_rate"])
        frequency_shift = min(1.0, abs(metrics["event_count"] - previous_metrics["event_count"]) / max(1, previous_metrics["event_count"]))
        score = round(0.4 * genre_shift + 0.25 * artist_shift + 0.15 * new_rate + 0.1 * min(1.0, behavior_shift) + 0.1 * frequency_shift, 4)
        evidence = evidence_for(metrics, previous_metrics)
        if score >= threshold:
            label = next((item["text"] for item in evidence if item["signal"] == "genre_share"), f"Listening pattern changed in {year}")
            period = existing.get((start, end)) or TimelinePeriod(user_id=user_id, start_at=start, end_at=end)
            period.label = label
            period.change_score = score
            period.evidence = evidence
            period.metrics = metrics
            period.active = True
            period.calculated_at = utc_now()
            db.add(period)
            generated.append(period)
        previous_metrics = metrics
    db.commit()
    return list(db.scalars(select(TimelinePeriod).where(TimelinePeriod.user_id == user_id, TimelinePeriod.active.is_(True)).order_by(TimelinePeriod.start_at.desc())).all())
