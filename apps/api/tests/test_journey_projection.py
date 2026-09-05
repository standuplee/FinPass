from pathlib import Path

import pytest

from app.contracts.journey import JourneyFixture
from app.modules.journey.state import project_journey

FIXTURES = Path(__file__).parents[3] / "data" / "synthetic" / "fixtures"


@pytest.mark.parametrize("fixture_path", sorted(FIXTURES.glob("*.json")))
def test_fixture_projects_to_expected_state(fixture_path: Path) -> None:
    fixture = JourneyFixture.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    projection = project_journey(fixture.events)

    assert projection.status == fixture.expected_status
    assert projection.current_step == fixture.expected_current_step
    assert projection.failure_count == fixture.expected_failure_count
