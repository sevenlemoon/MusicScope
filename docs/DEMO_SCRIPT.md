# MusicScope MVP demo script

This is the reproducible local demonstration path for the completed MVP.

1. Start PostgreSQL with `docker compose up -d postgres` and apply migrations with `cd apps/api && ../../.venv/bin/alembic upgrade head`.
2. Seed the deterministic catalog with `make demo-seed`. The seed creates data only for DEMO_USER_ID (`00000000-0000-0000-0000-000000000999`): 50 artists, 200 tracks, multiple historical periods, replay/favorite/skip variation, unresolved import records, timeline periods, and one example user memory. Running it again is safe and leaves existing demo data unchanged.
3. Start the API with `PYTHONPATH=apps/api .venv/bin/uvicorn app.main:app --reload --port 8000` and the web app with `cd apps/web && npm run dev`.
4. Open `http://localhost:3000`. Paste a small representative sample copied from the permitted NetEase helper into the assisted playlist import. Explain that playlist membership is not listening history. Use My Music to show the library and long-term profile, then For You to demonstrate exploration at 10, 50, and 90. The recommendation evaluation can be reproduced with `make recommendation-evaluation` using the seeded demo user.
5. In the personal UI, Timeline honestly shows an empty timestamp-required state until listening history is imported. The seeded historical Timeline is available through the explicit demo API/data path, not a frontend user switch. In My Music, show import status and unresolved-record correction. The accepted primary navigation is Home, For You, My Music, Timeline, and Lab; `/discover` redirects to For You. Memories are currently API/backend-managed, not a visible editing screen. Concerts are shown as a narrow milet official-provider showcase; generic Ticketmaster support is optional.
6. For audio, use the Audio panel with a permitted local audio file. The final validated offline path is `make audio-smoke`; it produces cached vocals and instrumental stems for synchronized playback and independent gain controls.

The demo does not require external music APIs, concert credentials, or copyrighted audio fixtures. Live milet concert lookup is an optional final flourish and may honestly show provider-unavailable when the network/provider is unavailable; it must never be replaced with fictional personal events.
