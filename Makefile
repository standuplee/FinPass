.PHONY: api-dev api-test api-lint api-migrate rag-index evaluate-ai demo-e2e web-dev web-check db-up db-down validate-fixtures banking77 profile-data normalize-consultations normalize-financial-products normalize-bpi normalize-banking77 validate-data generate-synthetic validate-synthetic test-pipelines

api-dev:
	cd apps/api && uv run uvicorn app.main:app --reload

api-test:
	cd apps/api && uv run pytest

api-lint:
	cd apps/api && uv run ruff check .

api-migrate:
	cd apps/api && uv run alembic upgrade head

rag-index:
	cd apps/api && uv run python -m scripts.index_rag

evaluate-ai:
	cd apps/api && PYTHONPATH=../.. uv run python -m ai.evals.evaluate

demo-e2e:
	cd apps/api && uv run python -m scripts.demo_e2e

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

validate-data:
	python3 -m pipelines.validate.quality_gate

generate-synthetic:
	python3 -m pipelines.synthetic.generate_journeys

validate-synthetic:
	python3 -m pipelines.synthetic.validate_journeys

test-pipelines:
	python3 -m unittest pipelines.normalize.test_pii pipelines.normalize.test_financial_products pipelines.normalize.test_bpi2017 pipelines.normalize.test_banking77_intents pipelines.validate.test_quality_gate pipelines.synthetic.test_generate_journeys
