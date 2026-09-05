import pytest
from sqlalchemy import text

from app.infrastructure.database import engine


@pytest.fixture(autouse=True)
def clean_database() -> None:
    if not (engine.url.database or "").endswith("_test"):
        raise RuntimeError("API tests require a database name ending in _test")
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE idempotency_records, journey_events, journeys, "
                "financial_products, customers RESTART IDENTITY CASCADE"
            )
        )
