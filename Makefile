.PHONY: api-dev api-test api-lint web-dev web-check db-up db-down validate-fixtures banking77 profile-data normalize-consultations normalize-financial-products normalize-bpi normalize-banking77 test-pipelines

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

normalize-consultations:
	python3 -m pipelines.normalize.consultations

normalize-financial-products:
	python3 -m pipelines.normalize.financial_products

normalize-bpi:
	python3 -m pipelines.normalize.bpi2017

normalize-banking77:
	python3 -m pipelines.normalize.banking77_intents

test-pipelines:
	python3 -m unittest pipelines.normalize.test_pii pipelines.normalize.test_financial_products pipelines.normalize.test_bpi2017 pipelines.normalize.test_banking77_intents
