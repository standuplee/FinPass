from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.events import JourneyEvent
from app.contracts.journey import JourneyFixture

FIXTURES = Path(__file__).parents[3] / "data" / "synthetic" / "fixtures"


@pytest.mark.parametrize("fixture_path", sorted(FIXTURES.glob("*.json")))
def test_journey_fixture_contract(fixture_path: Path) -> None:
    fixture = JourneyFixture.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    assert fixture.events
    assert len({event.event_id for event in fixture.events}) == len(fixture.events)
    assert all(event.journey_id == fixture.events[0].journey_id for event in fixture.events)
    assert fixture.events == sorted(fixture.events, key=lambda event: event.occurred_at)


def test_failed_event_requires_error_code() -> None:
    valid = JourneyFixture.model_validate_json(
        (FIXTURES / "income-verification-failure.json").read_text(encoding="utf-8")
    )
    invalid = valid.events[-2].model_dump(mode="json")
    invalid["error_code"] = None

    with pytest.raises(ValidationError):
        JourneyEvent.model_validate(invalid)
