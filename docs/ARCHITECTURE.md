# MusicScope Technical Architecture v1.0

## Recommended MVP architecture
Use a modular monolith plus a separate web client, not microservices.

### Frontend
Next.js + TypeScript.
Responsibilities:
- navigation/UI
- profile and timeline visualization
- recommendation interactions
- exploration slider
- audio mixer/player UI
- import/correction workflows

### Backend
FastAPI + Python.
Modules:
- auth/user
- catalog/entity resolution
- imports
- profiles
- recommendations
- feedback
- timeline/memories
- audio separation
- concerts/provider adapters

### Database
PostgreSQL. Use migrations.

### Background work
Source separation and large imports should run as jobs. MVP may use a simple database-backed/background worker design; introduce a queue only if needed.

### Storage
Store original permitted uploads and generated stems outside relational rows (local object-like storage in development; adapter for cloud object storage later). Database stores references and processing metadata.

## Core flow
Import -> RawImportRecord -> Entity Resolution -> Canonical Music Entity -> UserTrackRelationship -> Profile/State computation -> Candidate generation -> Ranking/diversification -> Recommendation explanation -> Feedback -> Profile updates.

## Audio flow
Upload/select -> validate -> normalize/transcode with FFmpeg -> separation job -> stem artifacts -> cached manifest -> web audio playback/mixing.

## Provider abstraction
Define interfaces for:
- MusicImportProvider
- MetadataProvider
- ConcertProvider
Avoid coupling domain models to one vendor.

## Security/privacy basics
- secrets in environment variables
- validate uploads and file sizes/types
- user-scoped access to personal records/stems
- explicit delete/exclude flows
- provenance fields for imported data
