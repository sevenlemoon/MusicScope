# MusicScope Roadmap v1.0

## Definition of Done
A graduation-project-quality build is complete when a reviewer can import/seed music data, see a meaningful profile, receive explainable recommendations affected by exploration level, give feedback, inspect a taste timeline, correct personal data, and successfully demo vocal/instrumental separation with live mixing.

## Milestone 0 — Architecture validation
- inspect specs
- confirm stack
- create ADRs for any deviations
- identify metadata/import/concert providers available for the project
- benchmark source-separation candidates
- define demo dataset strategy

## Milestone 1 — Foundation
- repository structure
- Next.js frontend
- FastAPI backend
- PostgreSQL + migrations
- Docker Compose
- health checks, lint/test scripts, environment templates

## Milestone 2 — Music domain + import
- canonical artist/album/track models
- import batches/raw records
- one practical import source plus manual/CSV fallback
- entity resolution with unresolved state
- correction workflow

## Milestone 3 — User music intelligence
- listening events
- User–Track Relationship
- long-term profile
- short-term state
- user-facing profile view

## Milestone 4 — Recommendation MVP
- candidate generation
- hybrid scoring
- exploration slider
- diversity/re-ranking
- four recommendation roles
- evidence-based explanations
- feedback capture

## Milestone 5 — Timeline + memories
- profile snapshots
- change detection
- evidence-first Timeline
- personal memories
- archive correction integration

## Milestone 6 — Audio separation (priority)
- upload/normalization
- 2-stem separation
- caching/jobs
- synchronized player
- real-time vocal/instrumental level control
- performance measurements

## Milestone 7 — Lightweight concerts
- favorite-artist lookup
- upcoming events adapter
- date/time/venue/location display
- source link

## Milestone 8 — Polish/evaluation
- end-to-end tests
- demo seed data
- empty/error/loading states
- performance checks
- README/setup
- screenshots/demo script
- recommendation/audio evaluation results

## Stretch goals
- progressive/true real-time neural separation
- 4-stem mode
- more import providers
- smarter session sequencing
- richer change-point algorithms

## Scope rule
Do not start stretch goals until Milestones 1–6 are demonstrably working.
