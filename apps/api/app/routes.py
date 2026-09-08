from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import get_db
from .audio import AudioProcessingError, separation_configuration, separation_fingerprint, storage_path, store_uploaded_audio, submit_separation
from .concerts import lookup_artist_concerts, relevant_artists
from .constants import PERSONAL_USER_ID
from .importer import import_library_rows, import_listening_rows, normalize_text, parse_csv, parse_playlist_text
from .models import Album, Artist, AudioAsset, FeedbackEvent, ImportBatch, ListeningEvent, Memory, ProfileSnapshot, RawImportRecord, Recommendation, RecommendationRun, SeparationJob, StemArtifact, TimelinePeriod, Track, User, UserLibraryTrack
from .profile import calculate_profiles, refresh_relationships
from .recommendation import SKIP_REASONS, generate_recommendations
from .timeline import generate_timeline

router = APIRouter(prefix="/api/v1", tags=["music"])
DEFAULT_USER_ID = PERSONAL_USER_ID


class CorrectionRequest(BaseModel):
    action: str = Field(pattern="^(assign|exclude)$")
    track_id: UUID | None = None


class FeedbackRequest(BaseModel):
    event_type: str = Field(pattern="^(like|dislike|skip)$")
    reason: str | None = None


class MemoryRequest(BaseModel):
    target_type: str = Field(pattern="^(track|artist|album|timeline_period)$")
    target_id: UUID
    text: str = Field(min_length=1, max_length=2000)


class MemoryUpdate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class PlaylistImportRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)


class PlaylistTextImportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1_000_000)


def _safe_int(value: object) -> int | None:
    try:
        return int(str(value)) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _safe_ratio(value: object) -> float | None:
    try:
        number = float(str(value)) if value not in (None, "") else None
        return number if number is not None and 0 <= number <= 1 else None
    except (TypeError, ValueError):
        return None


def serialize_batch(batch: ImportBatch) -> dict:
    return {"id": str(batch.id), "status": batch.status, "source_type": batch.source_type, "total_records": batch.total_records, "resolved_records": batch.resolved_records, "ambiguous_records": batch.ambiguous_records, "unresolved_records": batch.unresolved_records, "excluded_records": batch.excluded_records, "created_at": batch.created_at}


def serialize_record(record: RawImportRecord, track: Track | None = None) -> dict:
    payload = record.raw_payload
    return {"id": str(record.id), "batch_id": str(record.batch_id), "artist": payload.get("artist") or payload.get("artist_name"), "title": payload.get("title") or payload.get("track"), "album": payload.get("album") or payload.get("album_title"), "played_at": record.observed_at, "resolution_status": record.resolution_status, "resolution_confidence": record.resolution_confidence, "resolution_note": record.resolution_note, "resolved_track_id": str(record.resolved_track_id) if record.resolved_track_id else None, "excluded": record.excluded, "canonical_title": track.canonical_title if track else None}


@router.post("/imports/csv", status_code=201)
async def create_csv_import(file: UploadFile = File(...), user_id: UUID = Form(DEFAULT_USER_ID), db: Session = Depends(get_db)) -> dict:
    if user_id != DEFAULT_USER_ID:
        raise HTTPException(status_code=403, detail="Personal imports are scoped to the local personal user")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    content = (await file.read()).decode("utf-8-sig")
    rows = parse_csv(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV contains no records")
    batch = import_listening_rows(db, user_id, rows, {"filename": file.filename, "content_type": file.content_type, "source_type": "csv_listening_history"})
    return serialize_batch(batch)


@router.post("/imports/playlist-url")
def create_playlist_url_import(request: PlaylistImportRequest) -> dict:
    """Keep unsupported playlist providers explicit instead of faking an import."""
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(request.url.strip())
    playlist_id = parse_qs(parsed.query).get("id", [None])[0]
    is_netease = parsed.hostname and (parsed.hostname == "music.163.com" or parsed.hostname.endswith(".music.163.com"))
    if not is_netease or not playlist_id:
        raise HTTPException(status_code=400, detail="Unsupported or invalid playlist URL")
    raise HTTPException(status_code=503, detail="NetEase playlist metadata is publicly visible, but the complete track list is not reliably available through a supported local endpoint. Use CSV import for now.")


@router.post("/imports/playlist-text", status_code=201)
def create_playlist_text_import(request: PlaylistTextImportRequest, db: Session = Depends(get_db)) -> dict:
    rows, invalid_lines = parse_playlist_text(request.text)
    if not rows:
        raise HTTPException(status_code=400, detail="No valid `Track - Artist` lines were found")
    batch = import_library_rows(db, DEFAULT_USER_ID, rows, {"source_type": "assisted_playlist_text", "source_name": "pasted playlist", "invalid_lines": invalid_lines, "line_count": len(request.text.splitlines())})
    unique_artists = len({normalize_text(artist) for row in rows for artist in row.get("artists", [row["artist"]])})
    return {**serialize_batch(batch), "invalid_lines": len(invalid_lines), "unique_artists": unique_artists}


@router.get("/imports")
def list_imports(db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_batch(batch) for batch in db.scalars(select(ImportBatch).where(ImportBatch.user_id == DEFAULT_USER_ID).order_by(ImportBatch.created_at.desc())).all()]


@router.get("/imports/{batch_id}")
def get_import(batch_id: UUID, db: Session = Depends(get_db)) -> dict:
    batch = db.get(ImportBatch, batch_id)
    if not batch or batch.user_id != DEFAULT_USER_ID:
        raise HTTPException(status_code=404, detail="Import batch not found")
    records = list(db.scalars(select(RawImportRecord).where(RawImportRecord.batch_id == batch_id).order_by(RawImportRecord.id)))
    tracks = {track.id: track for track in db.scalars(select(Track).where(Track.id.in_([record.resolved_track_id for record in records if record.resolved_track_id])))}
    return {"batch": serialize_batch(batch), "records": [serialize_record(record, tracks.get(record.resolved_track_id)) for record in records]}


@router.get("/records/review")
def review_records(db: Session = Depends(get_db)) -> list[dict]:
    records = list(db.scalars(select(RawImportRecord).join(ImportBatch, RawImportRecord.batch_id == ImportBatch.id).where(ImportBatch.user_id == DEFAULT_USER_ID, RawImportRecord.resolution_status.in_(["ambiguous", "unresolved"]), RawImportRecord.excluded.is_(False)).order_by(RawImportRecord.observed_at.desc().nullslast())))
    return [serialize_record(record) for record in records]


@router.get("/tracks")
def list_tracks(db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": str(track.id), "title": track.canonical_title, "artist_id": str(track.primary_artist_id) if track.primary_artist_id else None, "version_type": track.version_type} for track in db.scalars(select(Track).order_by(Track.canonical_title)).all()]


@router.get("/library")
def list_library(user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> list[dict]:
    memberships = db.scalars(select(UserLibraryTrack).where(UserLibraryTrack.user_id == user_id, UserLibraryTrack.active.is_(True)).order_by(UserLibraryTrack.imported_at.desc())).all()
    tracks = {track.id: track for track in db.scalars(select(Track).where(Track.id.in_([item.track_id for item in memberships] or [None])))}
    artists = {artist.id: artist for artist in db.scalars(select(Artist).where(Artist.id.in_([track.primary_artist_id for track in tracks.values()] or [None])))}
    return [{"id": str(item.id), "track_id": str(item.track_id), "title": tracks[item.track_id].canonical_title, "artist": artists.get(tracks[item.track_id].primary_artist_id).canonical_name if artists.get(tracks[item.track_id].primary_artist_id) else None, "source_type": item.source_type, "source_name": item.source_name, "imported_at": item.imported_at} for item in memberships]


@router.get("/artists/{artist_id}/concerts")
def get_artist_concerts(artist_id: UUID, force_refresh: bool = False, demo: bool = False, db: Session = Depends(get_db)) -> dict:
    artist = db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    return lookup_artist_concerts(db, artist, force_refresh=force_refresh, allow_demo=demo)


@router.get("/concerts")
def get_relevant_concerts(user_id: UUID = DEFAULT_USER_ID, force_refresh: bool = False, demo: bool = False, db: Session = Depends(get_db)) -> dict:
    artist_results = [lookup_artist_concerts(db, artist, force_refresh=force_refresh, allow_demo=demo) for artist in relevant_artists(db, user_id)]
    events = [event for result in artist_results for event in result["events"]]
    events.sort(key=lambda event: (event["date"], event["time"] is None, event["time"] or "", event["artist"]))
    return {"events": events, "artists": [{"id": result["artist"]["id"], "name": result["artist"]["name"], "event_count": len(result["events"]), "provider_status": result["provider_status"], "source": result["source"], "stale": result["stale"]} for result in artist_results]}


@router.get("/concerts/search")
def search_concerts(artist: str, force_refresh: bool = False, demo: bool = False, db: Session = Depends(get_db)) -> dict:
    name = artist.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Artist name is required")
    match = db.scalar(select(Artist).where(Artist.normalized_name == normalize_text(name)))
    if not match:
        match = Artist(canonical_name=name, normalized_name=normalize_text(name), metadata_json={})
        db.add(match)
        db.flush()
    return lookup_artist_concerts(db, match, force_refresh=force_refresh, allow_demo=demo)


@router.post("/records/{record_id}/correction")
def correct_record(record_id: UUID, request: CorrectionRequest, db: Session = Depends(get_db)) -> dict:
    record = db.get(RawImportRecord, record_id)
    batch = db.get(ImportBatch, record.batch_id) if record else None
    if not record or not batch or batch.user_id != DEFAULT_USER_ID:
        raise HTTPException(status_code=404, detail="Import record not found")
    old_track_id = record.resolved_track_id
    event = db.scalar(select(ListeningEvent).where(ListeningEvent.raw_record_id == record.id))
    source_name = str(batch.source_metadata.get("source_name") or batch.source_metadata.get("filename") or batch.source_type)
    is_library = batch.source_type in {"assisted_playlist_text", "playlist_library"} and event is None
    if request.action == "assign":
        if not request.track_id or not db.get(Track, request.track_id):
            raise HTTPException(status_code=400, detail="A valid track_id is required")
        record.resolved_track_id = request.track_id
        record.resolution_status = "manually_corrected"
        record.resolution_confidence = 1.0
        record.excluded = False
        record.resolution_note = "assigned by user"
        if event:
            event.track_id = request.track_id
        elif is_library:
            old_still_supported = old_track_id and db.scalar(select(RawImportRecord.id).where(RawImportRecord.batch_id == batch.id, RawImportRecord.id != record.id, RawImportRecord.resolved_track_id == old_track_id, RawImportRecord.excluded.is_(False)))
            if old_track_id and not old_still_supported:
                for membership in db.scalars(select(UserLibraryTrack).where(UserLibraryTrack.user_id == batch.user_id, UserLibraryTrack.track_id == old_track_id, UserLibraryTrack.source_type == batch.source_type, UserLibraryTrack.source_name == source_name)).all():
                    membership.active = False
            membership = db.scalar(select(UserLibraryTrack).where(UserLibraryTrack.user_id == batch.user_id, UserLibraryTrack.track_id == request.track_id, UserLibraryTrack.source_type == batch.source_type, UserLibraryTrack.source_name == source_name))
            if membership:
                membership.active = True
            else:
                db.add(UserLibraryTrack(user_id=batch.user_id, track_id=request.track_id, source_type=batch.source_type, source_name=source_name, source_metadata=batch.source_metadata, imported_at=batch.created_at, active=True))
        elif record.observed_at is not None:
            db.add(ListeningEvent(user_id=batch.user_id, track_id=request.track_id, raw_record_id=record.id, played_at=record.observed_at, duration_played_ms=_safe_int(record.raw_payload.get("duration_played_ms")), completion_ratio=_safe_ratio(record.raw_payload.get("completion_ratio")), event_type=(record.raw_payload.get("event_type") or "play").casefold(), is_favorite=str(record.raw_payload.get("favorite") or record.raw_payload.get("is_favorite") or "").casefold() in {"1", "true", "yes", "favorite", "favourite"}, context={"source": record.raw_payload.get("source") or batch.source_type}))
    else:
        record.excluded = True
        record.resolution_status = "unresolved"
        record.resolution_note = "excluded by user as invalid or not theirs"
        if event:
            event.track_id = old_track_id
        elif is_library and old_track_id and not db.scalar(select(RawImportRecord.id).where(RawImportRecord.batch_id == batch.id, RawImportRecord.id != record.id, RawImportRecord.resolved_track_id == old_track_id, RawImportRecord.excluded.is_(False))):
            for membership in db.scalars(select(UserLibraryTrack).where(UserLibraryTrack.user_id == batch.user_id, UserLibraryTrack.track_id == old_track_id, UserLibraryTrack.source_type == batch.source_type, UserLibraryTrack.source_name == source_name)).all():
                membership.active = False
    db.commit()
    refresh_relationships(db, DEFAULT_USER_ID)
    return serialize_record(record, db.get(Track, record.resolved_track_id) if record.resolved_track_id else None)


@router.get("/relationships")
def list_relationships(user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> list[dict]:
    relationships = refresh_relationships(db, user_id)
    return [{"id": str(item.id), "track_id": str(item.track_id), "first_seen_at": item.first_seen_at, "last_played_at": item.last_played_at, "play_count": item.play_count, "replay_count": item.replay_count, "completed_count": item.completed_count, "skip_count": item.skip_count, "completion_avg": item.completion_avg, "favorite_state": item.favorite_state, "explicit_feedback": item.explicit_feedback, "discovery_source": item.discovery_source, "in_library": item.in_library, "first_library_imported_at": item.first_library_imported_at, "library_source_count": item.library_source_count, "excluded": item.excluded} for item in relationships]


@router.get("/profile")
def get_profile(user_id: UUID = DEFAULT_USER_ID, as_of: datetime | None = None, db: Session = Depends(get_db)) -> dict:
    snapshots = calculate_profiles(db, user_id, as_of)
    result = {}
    for profile_type, snapshot in snapshots.items():
        features = dict(snapshot.features)
        features.pop("artist_affinity", None)
        features.pop("genre_affinity", None)
        result[profile_type] = features | {"window_start": snapshot.window_start, "window_end": snapshot.window_end, "calculated_at": snapshot.calculated_at}
    return result


@router.post("/profile/snapshots")
def persist_profile_snapshot(user_id: UUID = DEFAULT_USER_ID, as_of: datetime | None = None, db: Session = Depends(get_db)) -> dict:
    snapshots = calculate_profiles(db, user_id, as_of, persist=True)
    return {profile_type: str(snapshot.id) for profile_type, snapshot in snapshots.items()}


@router.get("/profile/snapshots")
def list_profile_snapshots(user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> list[dict]:
    snapshots = db.scalars(select(ProfileSnapshot).where(ProfileSnapshot.user_id == user_id).order_by(ProfileSnapshot.calculated_at.desc())).all()
    return [{"id": str(snapshot.id), "profile_type": snapshot.profile_type, "window_start": snapshot.window_start, "window_end": snapshot.window_end, "window_days": snapshot.window_days, "features": snapshot.features, "calculated_at": snapshot.calculated_at} for snapshot in snapshots]


def serialize_recommendation(item: Recommendation, track: Track, artist: str) -> dict:
    return {"id": str(item.id), "track_id": str(item.track_id), "title": track.canonical_title, "artist": artist, "score": item.score, "role": item.role, "rank": item.rank, "explanation_evidence": item.explanation_evidence, "score_breakdown": item.score_breakdown}


@router.get("/recommendations")
def get_recommendations(user_id: UUID = DEFAULT_USER_ID, exploration_level: float = 50, limit: int = 12, db: Session = Depends(get_db)) -> dict:
    if not 0 <= exploration_level <= 100:
        raise HTTPException(status_code=400, detail="exploration_level must be between 0 and 100")
    if not 1 <= limit <= 30:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 30")
    run, items = generate_recommendations(db, user_id, exploration_level, limit)
    tracks = {track.id: (track, artist) for track, artist in db.execute(select(Track, Artist).join(Artist, Track.primary_artist_id == Artist.id).where(Track.id.in_([item.track_id for item in items]))).all()}
    return {"run": {"id": str(run.id), "exploration_level": run.exploration_level, "created_at": run.created_at}, "recommendations": [serialize_recommendation(item, tracks[item.track_id][0], tracks[item.track_id][1].canonical_name) for item in items]}


@router.post("/recommendations/{recommendation_id}/feedback")
def add_recommendation_feedback(recommendation_id: UUID, request: FeedbackRequest, user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> dict:
    recommendation = db.get(Recommendation, recommendation_id)
    run = db.get(RecommendationRun, recommendation.run_id) if recommendation else None
    if not recommendation or not run or run.user_id != user_id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if request.reason and request.reason not in SKIP_REASONS:
        raise HTTPException(status_code=400, detail="Unsupported feedback reason")
    event = FeedbackEvent(user_id=user_id, track_id=recommendation.track_id, recommendation_id=recommendation.id, event_type=request.event_type, reason=request.reason, context={"recommendation_run_id": str(recommendation.run_id)})
    db.add(event)
    db.commit()
    return {"id": str(event.id), "track_id": str(event.track_id), "event_type": event.event_type, "reason": event.reason}


def serialize_period(period: TimelinePeriod) -> dict:
    return {"id": str(period.id), "start_at": period.start_at, "end_at": period.end_at, "label": period.label, "change_score": period.change_score, "evidence": period.evidence, "metrics": period.metrics, "is_demo": bool((period.metrics or {}).get("is_demo")), "calculated_at": period.calculated_at}


@router.get("/timeline")
def get_timeline(user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_period(period) for period in db.scalars(select(TimelinePeriod).where(TimelinePeriod.user_id == user_id, TimelinePeriod.active.is_(True)).order_by(TimelinePeriod.start_at.desc())).all()]


@router.post("/timeline/recalculate")
def recalculate_timeline(user_id: UUID = DEFAULT_USER_ID, threshold: float = 0.20, db: Session = Depends(get_db)) -> list[dict]:
    if not 0 <= threshold <= 1:
        raise HTTPException(status_code=400, detail="threshold must be between 0 and 1")
    return [serialize_period(period) for period in generate_timeline(db, user_id, threshold)]


@router.get("/timeline/{period_id}")
def get_timeline_period(period_id: UUID, user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> dict:
    period = db.get(TimelinePeriod, period_id)
    if not period or period.user_id != user_id:
        raise HTTPException(status_code=404, detail="Timeline period not found")
    return serialize_period(period)


def validate_memory_target(db: Session, target_type: str, target_id: UUID, user_id: UUID) -> None:
    target_models = {"track": Track, "artist": Artist, "album": Album, "timeline_period": TimelinePeriod}
    target = db.get(target_models[target_type], target_id)
    if not target or (target_type == "timeline_period" and target.user_id != user_id):
        raise HTTPException(status_code=400, detail="Memory target was not found")


def serialize_memory(memory: Memory) -> dict:
    return {"id": str(memory.id), "target_type": memory.target_type, "target_id": str(memory.target_id), "text": memory.text, "created_at": memory.created_at, "updated_at": memory.updated_at}


def serialize_audio_asset(asset: AudioAsset) -> dict:
    return {"id": str(asset.id), "original_filename": asset.original_filename, "source_size_bytes": asset.source_size_bytes, "duration_seconds": asset.duration_seconds, "sample_rate": asset.sample_rate, "channels": asset.channels, "source_codec": asset.source_codec, "effective_deleted": asset.effective_deleted, "created_at": asset.created_at}


def serialize_separation_job(job: SeparationJob) -> dict:
    return {"id": str(job.id), "asset_id": str(job.asset_id), "status": job.status, "separator": job.separator, "separator_version": job.separator_version, "model_checkpoint": job.model_checkpoint, "configuration": job.configuration, "fingerprint": job.fingerprint, "error_message": job.error_message, "created_at": job.created_at, "started_at": job.started_at, "completed_at": job.completed_at}


@router.post("/audio-assets", status_code=201)
async def create_audio_asset(file: UploadFile = File(...), user_id: UUID = Form(DEFAULT_USER_ID), db: Session = Depends(get_db)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")
    if not db.get(User, user_id):
        raise HTTPException(status_code=400, detail="User was not found")
    try:
        asset = store_uploaded_audio(file.file, file.filename, file.content_type, user_id)
    except AudioProcessingError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    return serialize_audio_asset(asset)


@router.get("/audio-assets")
def list_audio_assets(user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> list[dict]:
    assets = db.scalars(select(AudioAsset).where(AudioAsset.user_id == user_id, AudioAsset.effective_deleted.is_(False)).order_by(AudioAsset.created_at.desc())).all()
    return [serialize_audio_asset(asset) for asset in assets]


@router.delete("/audio-assets/{asset_id}", status_code=204)
def delete_audio_asset(asset_id: UUID, user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> None:
    asset = db.get(AudioAsset, asset_id)
    if not asset or asset.user_id != user_id or asset.effective_deleted:
        raise HTTPException(status_code=404, detail="Audio asset not found")
    asset_dir = storage_path(asset.source_storage_key).parent
    db.delete(asset)
    db.commit()
    import shutil
    shutil.rmtree(asset_dir, ignore_errors=True)


@router.post("/audio-assets/{asset_id}/separate", status_code=202)
def create_separation_job(asset_id: UUID, user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> dict:
    asset = db.get(AudioAsset, asset_id)
    if not asset or asset.user_id != user_id or asset.effective_deleted:
        raise HTTPException(status_code=404, detail="Audio asset not found")
    fingerprint = separation_fingerprint(asset)
    existing = db.scalar(select(SeparationJob).join(AudioAsset, SeparationJob.asset_id == AudioAsset.id).where(SeparationJob.user_id == user_id, SeparationJob.fingerprint == fingerprint, AudioAsset.effective_deleted.is_(False)))
    if existing:
        stale = existing.status == "PROCESSING" and existing.started_at and existing.started_at < datetime.now(timezone.utc) - timedelta(hours=2)
        if stale:
            existing.status = "FAILED"
            existing.error_message = "Separation interrupted; retry is available"
            existing.completed_at = datetime.now(timezone.utc)
        if existing.status == "FAILED":
            existing.status = "PENDING"
            existing.error_message = None
            existing.error_detail = {}
            existing.started_at = None
            existing.completed_at = None
            db.commit()
            submit_separation(existing.id)
        elif existing.status == "PENDING":
            submit_separation(existing.id)
        return serialize_separation_job(existing)
    settings = separation_configuration()
    job = SeparationJob(user_id=user_id, asset_id=asset.id, status="PENDING", separator=str(settings["separator"]), separator_version=str(settings["separator_version"]), model_checkpoint=str(settings["checkpoint"]), configuration=settings, fingerprint=fingerprint)
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(SeparationJob).where(SeparationJob.user_id == user_id, SeparationJob.fingerprint == fingerprint))
        if not existing:
            raise HTTPException(status_code=409, detail="A separation job could not be created")
        if existing.status == "PENDING":
            submit_separation(existing.id)
        return serialize_separation_job(existing)
    db.refresh(job)
    submit_separation(job.id)
    return serialize_separation_job(job)


@router.get("/separation-jobs/{job_id}")
def get_separation_job(job_id: UUID, user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> dict:
    job = db.get(SeparationJob, job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Separation job not found")
    return serialize_separation_job(job)


@router.get("/separation-jobs/{job_id}/manifest")
def get_separation_manifest(job_id: UUID, user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> dict:
    job = db.get(SeparationJob, job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Separation job not found")
    if job.status != "COMPLETED":
        raise HTTPException(status_code=409, detail="Separation is not completed")
    asset = db.get(AudioAsset, job.asset_id)
    artifacts = db.scalars(select(StemArtifact).where(StemArtifact.job_id == job.id)).all()
    by_name = {artifact.stem_name: artifact for artifact in artifacts}
    if not asset or asset.effective_deleted or set(by_name) != {"vocals", "instrumental"}:
        raise HTTPException(status_code=500, detail="Completed separation artifacts are incomplete")
    return {"job_id": str(job.id), "asset_id": str(asset.id), "duration_seconds": by_name["vocals"].duration_seconds, "sample_rate": by_name["vocals"].sample_rate, "channels": by_name["vocals"].channels, "separator": job.separator, "model_checkpoint": job.model_checkpoint, "fingerprint": job.fingerprint, "stems": {name: {"url": f"/api/v1/separation-jobs/{job.id}/artifacts/{name}", "duration_seconds": artifact.duration_seconds, "sample_rate": artifact.sample_rate, "channels": artifact.channels, "byte_size": artifact.byte_size} for name, artifact in by_name.items()}}


@router.get("/separation-jobs/{job_id}/artifacts/{stem_name}")
def serve_separation_artifact(job_id: UUID, stem_name: str, user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> FileResponse:
    if stem_name not in {"vocals", "instrumental"}:
        raise HTTPException(status_code=404, detail="Stem not found")
    job = db.get(SeparationJob, job_id)
    asset = db.get(AudioAsset, job.asset_id) if job else None
    if not job or not asset or asset.effective_deleted or job.user_id != user_id or job.status != "COMPLETED":
        raise HTTPException(status_code=404, detail="Audio artifact not found")
    artifact = db.scalar(select(StemArtifact).where(StemArtifact.job_id == job.id, StemArtifact.stem_name == stem_name))
    if not artifact:
        raise HTTPException(status_code=404, detail="Audio artifact not found")
    path = storage_path(artifact.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio artifact not found")
    return FileResponse(path, media_type="audio/wav", filename=f"{stem_name}.wav", headers={"Accept-Ranges": "bytes"})


@router.get("/memories")
def list_memories(user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_memory(memory) for memory in db.scalars(select(Memory).where(Memory.user_id == user_id).order_by(Memory.updated_at.desc())).all()]


@router.post("/memories", status_code=201)
def create_memory(request: MemoryRequest, user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> dict:
    validate_memory_target(db, request.target_type, request.target_id, user_id)
    memory = Memory(user_id=user_id, target_type=request.target_type, target_id=request.target_id, text=request.text)
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return serialize_memory(memory)


@router.patch("/memories/{memory_id}")
def update_memory(memory_id: UUID, request: MemoryUpdate, user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> dict:
    memory = db.get(Memory, memory_id)
    if not memory or memory.user_id != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    memory.text = request.text
    memory.updated_at = datetime.now(timezone.utc)
    db.commit()
    return serialize_memory(memory)


@router.delete("/memories/{memory_id}", status_code=204)
def delete_memory(memory_id: UUID, user_id: UUID = DEFAULT_USER_ID, db: Session = Depends(get_db)) -> None:
    memory = db.get(Memory, memory_id)
    if not memory or memory.user_id != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(memory)
    db.commit()
