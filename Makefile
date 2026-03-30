PYTHON = uv run
ALEMBIC = $(PYTHON) alembic

# Server and DB
run-server:
	uvicorn app.main:app --reload
run-db:
	docker compose up -d

# Alembic migrations
revision:
	@if [ -z "$(name)" ]; then echo "Error: specify migration name, like: make revision name=offers-test"; exit 1; fi
	$(ALEMBIC) revision -m "$(name)"

migrate:
	$(ALEMBIC) upgrade head

rollback:
	$(ALEMBIC) downgrade -1

history:
	$(ALEMBIC) history --verbose

current:
	$(ALEMBIC) current