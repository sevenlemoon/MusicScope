# Codex First Prompt

Read `AGENTS.md` and every file under `docs/` before making major changes.

This repository is the MusicScope graduation project. Do not implement the entire application in one pass.

First:
1. Inspect the current repository.
2. Summarize your understanding of MusicScope in no more than 15 bullets.
3. Validate the proposed technical architecture against the current development environment.
4. Identify unresolved external dependencies/providers, especially music metadata/import data, concert data, and audio source-separation model choice.
5. Propose the concrete repository structure.
6. Propose the initial PostgreSQL schema and migration strategy.
7. Define frontend/backend module boundaries and API boundaries.
8. Define the recommendation pipeline and how it will be testable with a demo dataset.
9. Define an audio separation benchmark plan before choosing the final separation engine.
10. Identify the top technical risks and mitigations.
11. Produce a milestone plan consistent with `docs/ROADMAP.md`.

Do not begin large-scale implementation yet. Small inspection/setup changes are fine, but wait for approval before executing Milestone 1.

When reporting, clearly distinguish:
- decisions already fixed by the product spec
- engineering recommendations
- unresolved choices requiring approval
