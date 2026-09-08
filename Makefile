.PHONY: venv api-install api-test api-lint web-install web-lint web-test test lint db-up db-down demo-seed recommendation-evaluation audio-smoke

PYTHON ?= .venv/bin/python

venv:
	uv venv .venv
	uv pip install --python $(PYTHON) -r apps/api/requirements.txt

api-install:
	uv pip install --python $(PYTHON) -r apps/api/requirements.txt

api-test:
	$(PYTHON) -m pytest apps/api/tests

api-lint:
	$(PYTHON) -m ruff check apps/api

web-install:
	cd apps/web && npm install

web-lint:
	cd apps/web && npm run lint

web-test:
	cd apps/web && npm test

test: api-test web-test

lint: api-lint web-lint

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

demo-seed:
	PYTHONPATH=apps/api $(PYTHON) scripts/seed_demo.py

recommendation-evaluation:
	PYTHONPATH=apps/api $(PYTHON) scripts/evaluate_recommendations.py

audio-smoke:
	PYTHONPATH=apps/api $(PYTHON) scripts/audio_smoke.py
