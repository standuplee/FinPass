.PHONY: api-dev api-test api-lint web-dev web-check db-up db-down validate-fixtures banking77 profile-data

api-dev:
	cd apps/api && uv run uvicorn app.main:app --reload

api-test:
	cd apps/api && uv run pytest

api-lint:
	cd apps/api && uv run ruff check .

web-dev:
	pnpm dev:web

web-check:
	pnpm typecheck:web

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

validate-fixtures:
	cd apps/api && uv run python -m app.contracts.validate_fixtures ../../data/synthetic/fixtures

banking77:
	uv run --project apps/api --group data python pipelines/inspect/banking77.py

profile-data:
	python3 pipelines/inspect/local_datasets.py
