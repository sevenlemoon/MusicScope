# Phase 3 — Real-data usability and demo reliability

## Supported personal-data path

MusicScope does not scrape or reverse-engineer the NetEase playlist URL. The
reliable workflow is:

```text
NetEase playlist URL
  -> permitted music.unmeta.cn helper
  -> copied Track - Artist text
  -> assisted playlist-text import
```

The importer accepts approximately 2,500–3,000 lines in one request. It uses
the final clearly separated ` - `, ` – `, or ` — ` delimiter so title text
such as `Savage Love (Laxed – Siren Beat) ...` is preserved. Only slash
separators (`/` and full-width `／`) are treated as supported featured-artist
delimiters; the first artist remains primary. Ampersands, commas, and other
punctuation stay inside one artist name because they can be ambiguous.

Playlist imports create `UserLibraryTrack` membership, canonical catalog
entities, and raw provenance. They create zero `ListeningEvent` rows and do
not infer timestamps from playlist order. Repeating an import reuses tracks,
artists, albums, and library memberships; each import batch remains available
as provenance.

## Personal versus demo data

| Mode | Data | Timeline | Concert behavior |
|---|---|---|---|
| PERSONAL | Real imported library and timestamped history | Empty until timestamped history exists | Effective personal artists only; no fictional fallback |
| DEMO | Deterministic catalog, history, and evidence periods | Explicitly available for the graduation walkthrough | Demo fixtures only when explicitly selected |

The user IDs and API defaults are defined in `apps/api/app/constants.py`. The
two modes are never merged.

## Profile and recommendation truth

Library membership contributes to long-term library/profile signals. It does
not create recent listening state, Timeline events, or play counts. The short-
term profile remains empty when no timestamped listening events exist.

The current recommendation scope is personalized library rediscovery and
ranking. Exploration levels 10, 50, and 90 change novelty, role composition,
and diversity within the available personal/demo catalog; they do not claim
to search the whole internet. Missing genre metadata stays missing, and
explanations use artist/library evidence or a neutral balanced explanation
instead of inventing genre preferences.

## Bounded local benchmark

A local PostgreSQL smoke run with 2,500 synthetic playlist rows produced:

| Measure | Result |
|---|---:|
| First import | 30.991 s |
| Identical re-import | 22.915 s |
| Library memberships after both imports | 2,500 |
| Listening events added | 0 |

The run used a temporary user and was deleted afterward. This is practical for
a graduation demo, though not a production bulk-loader benchmark; database
query batching can be revisited later if much larger imports become a goal.

## Stable 5–8 minute walkthrough

1. Start in PERSONAL mode and explain the system boundary.
2. Paste a small representative list from the assisted helper and import it.
3. Open My Music: show tracks, artists, long-term library signal, and zero
   recent state without claiming fabricated plays.
4. Open For You: compare exploration 10, 50, and 90 and explain library
   rediscovery evidence.
5. Open Timeline: show the personal timestamp-required empty state.
6. Use the explicit DEMO path if historical Timeline evidence is needed.
7. Search milet in Concerts; show the official result or the honest provider
   unavailable state if live lookup is unavailable.
8. Open Lab and run the already validated vocals/instrumental separation
   smoke path with a permitted local audio file.
