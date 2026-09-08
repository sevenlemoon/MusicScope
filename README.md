# MusicScope

MusicScope is a local, single-user music intelligence graduation project. It will combine listening imports, explainable recommendations, taste timelines, personal memories, lightweight concert discovery, and cached two-stem audio separation.

The foundation uses a Next.js/TypeScript web client, a FastAPI/Python API, PostgreSQL, and Alembic migrations. External music providers are optional adapters; CSV/manual import and deterministic demo data remain independent of them.

## Local setup

Requirements:

- Node.js 20+
- Python 3.13 for the API (a project-local environment is recommended)
- Python 3.12 for the isolated audio separator runtime
- [uv](https://docs.astral.sh/uv/)
- FFmpeg 9+ available on `PATH` for audio validation and normalization
- Docker Desktop with the Docker daemon running

1. Copy `.env.example` to `.env`.
2. Start PostgreSQL:

   ```bash
   docker compose up -d postgres
   ```

3. Install API dependencies and run migrations:

   ```bash
   uv venv .venv
   uv pip install --python .venv/bin/python -r apps/api/requirements.txt
   cd apps/api
   ../../.venv/bin/alembic upgrade head
   ../../.venv/bin/uvicorn app.main:app --reload --port 8000
   ```

4. In another terminal, install and start the web app:

   ```bash
   cd apps/web
   npm install
   npm run dev
   ```

Open [http://localhost:3000](http://localhost:3000). The API health endpoint is [http://localhost:8000/health](http://localhost:8000/health), and interactive API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Audio separation runtime

The API keeps audio dependencies out of the main Python environment. Install
FFmpeg and create the approved isolated separator environment once:

```bash
brew install ffmpeg python@3.12
/opt/homebrew/bin/python3.12 -m venv .audio-venv312
.audio-venv312/bin/python -m pip install demucs-infer==4.2.0 soundfile==0.14.0
```

The first real separation downloads the `htdemucs` checkpoint. The API uses
MPS when PyTorch reports it available and otherwise falls back to CPU. Audio
uploads are normalized to stereo 44.1 kHz WAV, then separated into cached
Vocals and Instrumental artifacts. The local demo accepts WAV, MP3, M4A/AAC,
and FLAC files up to 250 MB and 15 minutes.

Run the real one-file smoke test from the repository root after PostgreSQL,
FFmpeg, and the isolated runtime are ready:

```bash
PYTHONPATH=apps/api .venv/bin/python scripts/audio_smoke.py
```

## CSV import

The baseline importer accepts CSV files with `artist` and `title` columns. Optional columns include `album`, `played_at`, `duration_played_ms`, `completion_ratio`, `event_type`, `favorite`, `source_record_id`, and `source`. Records that do not resolve remain reviewable and do not block the batch.

To load the deterministic demo catalog and listening history:

```bash
PYTHONPATH=apps/api .venv/bin/python scripts/seed_demo.py
```

NetEase Cloud Music playlist URLs are detected in the web UI, but the public page currently does not expose the complete track list through a stable supported endpoint. MusicScope reports that limitation and keeps CSV import as the reliable path; see `docs/NETEASE_IMPORT.md`.

## Profile calculation

The profile API keeps long-term and short-term state separate. Long-term state uses all effective historical events. Short-term state uses a configurable 30-day window with a 14-day exponential recency half-life. When `as_of` is omitted, the latest effective event is used as the reference time, which keeps the deterministic demo reproducible.

`GET /api/v1/profile` calculates a read-only view and does not persist a snapshot. Deliberate snapshot persistence uses `POST /api/v1/profile/snapshots`. Recommendations are generated through `GET /api/v1/recommendations?exploration_level=50`, with feedback posted to `/api/v1/recommendations/{id}/feedback`.

The evidence-first Timeline is generated deliberately with `POST /api/v1/timeline/recalculate`. It compares yearly genre/artist shares, new-artist rate, completion, skips, and listening frequency using a configurable change threshold. `GET /api/v1/timeline` is read-only. Music Memories are user-authored and managed independently through `/api/v1/memories`.

## Concert discovery

Concert discovery is deliberately lightweight and user-scoped. By default it
uses deterministic fictional fixtures for the demo, so it works without
internet access or credentials. To enable optional live Ticketmaster Discovery
lookups, set `CONCERT_PROVIDER=ticketmaster` and provide
`TICKETMASTER_API_KEY` in `.env`. Results are cached for six hours and fall
back to stale cached data or demo fixtures when the provider is unavailable.

The API endpoints are `GET /api/v1/concerts` for relevant artists and
`GET /api/v1/artists/{artist_id}/concerts` for one artist. MusicScope only
links to external event details; it does not sell tickets or process checkout.

To run the full containerized foundation instead:

```bash
docker compose up --build
```

## Checks

```bash
make api-test
make api-lint
make web-lint
make web-test
```

The database health endpoint is `/health/db`; it requires PostgreSQL to be running. Recommendations, timeline, memories, concerts, and cached audio separation are available in the MVP. External concert data remains optional.
