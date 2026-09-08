# Deterministic demo data

Run the seed script after applying migrations:

```bash
PYTHONPATH=apps/api .venv/bin/python scripts/seed_demo.py
```

It creates a local user, 50 artists, 200 canonical tracks, multiple genre/period groupings, repeated plays, favorites, low-completion plays, recent plays, and two unresolved records for correction demonstrations. The fixed names, dates, and source record IDs make the result repeatable.

