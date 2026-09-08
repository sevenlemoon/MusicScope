# MusicScope MVP demo script

This is the reproducible local demonstration path for the completed MVP.

1. Start PostgreSQL with `docker compose up -d postgres` and apply migrations with `cd apps/api && ../../.venv/bin/alembic upgrade head`.
2. Seed the deterministic catalog with `make demo-seed`. The seed creates 50 artists, 200 tracks, multiple historical periods, replay/favorite/skip variation, unresolved import records, timeline periods, and one example user memory. Running it again is safe and leaves existing demo data unchanged.
3. Start the API with `PYTHONPATH=apps/api .venv/bin/uvicorn app.main:app --reload --port 8000` and the web app with `cd apps/web && npm run dev`.
4. Open `http://localhost:3000`. Use the four navigation links to show For You, My Music, Discover, and Timeline. Demonstrate the exploration slider at 10, 50, and 90; the recommendation evaluation can be reproduced with `make recommendation-evaluation`.
5. In Timeline, inspect evidence and add a user memory. In My Music, show import status and unresolved-record correction. In Discover, distinguish deterministic concert fixtures from live provider data.
6. For audio, use the Audio panel with a permitted local audio file. The final validated offline path is `make audio-smoke`; it produces cached vocals and instrumental stems for synchronized playback and independent gain controls.

The demo does not require external music APIs, concert credentials, or copyrighted audio fixtures.
