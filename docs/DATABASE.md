# MusicScope Database Model v1.0

Suggested core tables/entities:

## users
id, created_at, settings, exploration_level

## artists
id, canonical_name, external_ids, metadata

## albums
id, artist_id, canonical_title, release_date, external_ids

## tracks
id, canonical_title, primary_artist_id, album_id, duration_ms, version_type, external_ids, metadata

## track_artists
track_id, artist_id, role

## track_features
track_id, feature_source, genre/features/vector payload, updated_at

## import_batches
id, user_id, source_type, source_metadata, status, created_at

## raw_import_records
id, batch_id, raw_payload, source_record_id, observed_at, resolution_status, resolution_confidence, resolved_track_id

## listening_events
id, user_id, track_id, raw_record_id, played_at, duration_played_ms, completion_ratio, context

## user_library_tracks
id, user_id, track_id, source_type, source_name, source_metadata, saved_at, imported_at, active

## user_track_relationships
user_id, track_id, library state, first/last played, play/replay counts, completion stats, favorite_state, effective_feedback, discovery_source, excluded

## feedback_events
id, user_id, track_id, event_type, reason, context, created_at

## profile_snapshots
id, user_id, profile_type(long_term/short_term), vector/features, window_start, window_end, created_at

## recommendation_runs
id, user_id, exploration_level, context, created_at

## recommendations
id, run_id, track_id, score, role, explanation_evidence, rank

## timeline_periods
id, user_id, start_at, end_at, metrics, change_score

## memories
id, user_id, target_type, target_id/period_id, text, created_at, updated_at

## corrections
id, user_id, target_type, target_id, correction_type, previous_value, new_value, created_at

## audio_assets
id, user_id, track_id(optional), source_path, normalized_path, duration, status

## separation_jobs
id, audio_asset_id, model_name, model_version, stem_mode, status, progress, error, created_at, completed_at

## stems
id, separation_job_id, stem_type, storage_path, duration

## concert_events
id, artist_id, provider, provider_event_id, starts_at, venue_name, city, country, location, source_url, fetched_at

## Milestone 4 additions

### user_track_relationships
Derived per-user aggregates over effective listening events: first/last played, plays, replays, completion/skips, favorite state, feedback, discovery source, and exclusion state.

### profile_snapshots
Deliberately persisted long-term or short-term profile observations. Profile GET requests calculate read-only features and do not create rows; explicit snapshot persistence is a separate operation.

### recommendation_runs
Stores user, exploration level, generation context, and timestamp.

### recommendations
Stores track, final score, role, rank, structured explanation evidence, and score breakdown for a run.

### feedback_events
Stores lightweight recommendation feedback and optional skip reasons without turning every skip into a permanent dislike.

## Milestone 5 additions

### timeline_periods
Persisted, recalculable evidence periods with start/end boundaries, measurable change score, structured evidence, metrics, and active state. Recalculation deactivates obsolete periods rather than deleting them.

### memories
User-authored text attached polymorphically to a track, artist, album, or timeline period. Memories are never mixed into system-observation metrics.

Add indexes around user/time, track identity/external IDs, unresolved imports, recommendation runs, and artist/event date.
