# MusicScope — Codex Instructions

## Mission
Build MusicScope as a graduation-project-quality personal music intelligence system.
Prioritize a working, demonstrable product, simple UX, maintainability, and clear technical reasoning over feature count.

## Product principles
1. Keep the visible UX simple; hide algorithmic complexity behind clear controls.
2. User data is user-owned and editable.
3. Separate system-observed facts from user-authored meaning/memories.
4. Recommendations must be explainable.
5. Long-term taste and short-term listening state are separate concepts.
6. Exploration is user-controlled; the system may suggest changes but must not silently override the user's setting.
7. Concert discovery is lightweight. Audio source separation is a major technical feature.
8. Do not block imports because a minority of music entities cannot be resolved.

## Development rules
- Read this file and all relevant files under /docs before major implementation.
- Work milestone by milestone. Do not implement the entire product in one pass.
- Before a milestone: inspect current repository state and state the plan.
- After a milestone: run relevant tests/checks and report files changed, decisions, tests, and remaining issues.
- Prefer typed interfaces, migrations, reproducible setup, and small modules.
- Keep external providers behind adapters/interfaces.
- Never hard-code secrets; use environment variables and provide .env.example.
- Preserve provenance for imported data and user corrections.
- Treat real-time source separation as a stretch goal until offline/preprocessed separation is stable.
- Avoid unnecessary microservices for the MVP.

## Suggested stack
- Web: Next.js + TypeScript
- API/ML: Python + FastAPI
- Database: PostgreSQL
- Local development: Docker Compose
- Audio: FFmpeg + a Python source-separation model (benchmark before final choice)
- Tests: pytest + frontend unit/component tests

The stack may be changed only when there is a clear implementation reason; document the decision.
