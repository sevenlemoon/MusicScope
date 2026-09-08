# MusicScope Product Specification v1.0

## 1. Vision
MusicScope is a personal music intelligence system that learns a user's musical world over time. It combines imported listening data, explicit feedback, long-term preferences, short-term state, music discovery, personal music memories, and audio source separation.

The core question is not only “what song should I hear next?” but also:
- What do I tend to like?
- What do I want recently?
- How far outside my comfort zone do I want to explore?
- How has my taste changed?
- What relationship have I built with particular songs?
- Can I interact with the music itself through stem separation?

## 2. Product principles
- Complex underneath, simple on the surface.
- System facts and user meaning are distinct.
- Recommendations are controllable and explainable.
- Imported data is fallible and correctable.
- A failed entity match must not block an import.
- Architecture supports multiple music sources; MVP implements only one or two practical sources.

## 3. Primary navigation
### For You
Personal recommendations, lightweight listening session, exploration control, recommendation explanations.

### My Music
Songs, artists, albums, user-track relationships, favorites, personal memories, and entry point to source separation.

### Discover
New music discovery with an exploration slider and recommendation roles.

### Timeline
Evidence-first view of how taste changes over time, plus user-authored music memories.

## 4. Music profile
Two-layer model:
- User-facing profile: understandable labels, percentages, trends, listening patterns.
- Internal profile vector: genre, artist, era, language, tempo/energy-related features when available, instrumental/vocal preference, novelty tolerance, etc.

Maintain:
- Long-term profile: stable preferences accumulated over time.
- Short-term state: recent listening behavior with stronger recency weighting.

## 5. Track and relationship model
### Track Profile
Represents what a track is: canonical identity, artist, album, versions, metadata and available audio/features.

### User–Track Relationship
A first-class entity representing what a track means behaviorally to this user:
- first seen/heard
- last played
- play count
- completion behavior
- skips
- favorites/likes
- explicit feedback
- discovery source
- relationship to timeline periods/memories
- correction/exclusion state

## 6. Music entity resolution
Normalize imported records into canonical entities.
Handle:
- spelling/metadata differences
- live versions
- remixes
- covers
- alternate editions
- unresolved/ambiguous matches

Use confidence/status fields. Low-confidence records can remain unresolved and be corrected later without blocking the import.

## 7. Recommendation system
Use a hybrid ranking pipeline rather than simple if/else logic.

Inputs:
- long-term user profile
- short-term state
- track/content similarity
- user-track relationships
- explicit feedback
- exploration level
- novelty/diversity constraints

### Exploration slider
Continuous value, conceptually 0–100:
- low = familiar/safe
- high = increasingly novel/cross-boundary

The user controls it. The system may suggest a new value based on acceptance/rejection patterns, but does not change it silently.

### Recommendation roles
A recommendation set is intentionally structured:
- Precise Match
- Adjacent Exploration
- Cross-boundary Discovery
- Bold Try

The mixture changes with exploration level.

### Feedback
A skip is contextual evidence, not automatically a hard dislike.
Offer optional lightweight reasons such as:
- too loud
- too slow
- dislike vocals
- not for today
- simply dislike

Feedback updates the appropriate layer: long-term preference, short-term state, or exploration tolerance.

### Explainability
Each recommendation should expose a concise reason derived from real signals, not generated fluff.

## 8. Timeline
A true music-taste timeline, but evidence-first rather than over-interpreting the user.

Detect and display meaningful change points/periods using measurable signals such as:
- genre/artist share changes
- novelty rate
- new-artist count
- listening-time patterns
- feature-distribution changes

Do not assign psychological meaning automatically.

## 9. Music memories
Users may attach personal meaning to:
- track
- album
- artist
- playlist/collection
- time period

Memories are user-authored and can be linked to Timeline. They are distinct from system observations.

## 10. Archive correction
Users can:
- delete/exclude erroneous imported records
- correct entity matches
- change feedback
- edit/delete memories
- mark data as not theirs

Preserve useful provenance/audit information internally while current analyses use the corrected effective state.

## 11. Listening experience
Support individual recommendations and a lightweight generated session/playlist.
Do not make sequencing/session orchestration overly complex in MVP.

## 12. Concert discovery — lightweight
For favorite artists, surface upcoming concert:
- date/time
- venue
- city/location
- source link when available

Keep provider integration behind an adapter. No ticketing/payment/seat-selection system in MVP.

## 13. Audio source separation — major feature
Primary technical showcase.

Target experience:
1. User selects/uploads an audio track they are permitted to process.
2. System separates at minimum Vocals + Instrumental.
3. User can play the separated result.
4. User can independently adjust vocal/instrumental levels during playback.
5. Cache separation results to avoid repeated expensive inference.

Stretch goal:
- progressive/streaming separation with playback beginning before full processing finishes
- lower-latency real-time experience
- optional 4-stem separation (vocals/drums/bass/other)

MVP must stabilize preprocessed 2-stem separation before attempting true real-time inference.

## 14. Out of scope for MVP
- full ticket marketplace
- social network
- complex collaborative playlists
- supporting every streaming platform
- production-scale music licensing infrastructure
- mandatory true real-time neural separation
