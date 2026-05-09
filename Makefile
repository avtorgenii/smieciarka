PYTHON = uv run
ALEMBIC = $(PYTHON) alembic

# Server and DB
run-server-dev:
	uvicorn app.main:app --reload

# Production-like run (no reload, multiple workers)
run-server:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers $${WEB_CONCURRENCY:-2}
run-db:
	docker compose up -d

# Alembic migrations
revision:
	@if [ -z "$(name)" ]; then echo "Error: specify migration name, like: make revision name=offers-test"; exit 1; fi
	$(ALEMBIC) revision -m "$(name)"

migrate:
	$(ALEMBIC) upgrade head

seed:
	$(PYTHON) python scripts/seed_offers.py

rollback:
	$(ALEMBIC) downgrade -1

history:
	$(ALEMBIC) history --verbose

current:
	$(ALEMBIC) current