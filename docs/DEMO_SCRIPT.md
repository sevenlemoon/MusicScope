# MusicScope V3 graduation demo script

This is the reproducible local demonstration path for the completed MVP.

1. Start PostgreSQL with `docker compose up -d postgres` and apply migrations with `cd apps/api && ../../.venv/bin/alembic upgrade head`.
2. Seed the deterministic catalog with `make demo-seed` only when backend evaluation data is needed. It belongs exclusively to DEMO_USER_ID (`00000000-0000-0000-0000-000000000999`) and never mixes with the personal library.
3. Start the API with `PYTHONPATH=apps/api .venv/bin/uvicorn app.main:app --reload --port 8000` and the web app with `cd apps/web && npm run dev`.
4. Open `http://localhost:3000`. Show the personal library, or paste a representative sample copied from the permitted NetEase helper into the assisted playlist import. Explain that playlist membership is not listening history. The import presents honest stages rather than invented record-by-record backend progress.
5. Open My Music to browse tracks and artists, then For You to show traceable recommendation reasons and the exploration control. Search for a library artist from Concert Search; live results may honestly be unavailable when providers cannot be reached. The primary navigation is Home, For You, My Music, Concert Search, and Stem Separation. `/timeline` redirects to My Music and `/discover` redirects to For You.
6. For audio, open Stem Separation and use a permitted local audio file. The final validated offline path is `make audio-smoke`; it produces cached vocals and instrumental stems for synchronized playback and independent gain controls.

The core demo does not require external music APIs, concert credentials, or copyrighted audio fixtures. Live concert lookup is an optional flourish and may honestly show provider-unavailable; it must never be replaced with fictional personal events.
