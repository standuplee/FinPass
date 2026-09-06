import json
import math
from pathlib import Path

from app.contracts.journey import JourneyFixture
from app.modules.journey.intent import classify_intent
from app.modules.rag.service import deterministic_embedding
from app.modules.journey.state import project_journey

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data/synthetic/fixtures"
REPORT = ROOT / "data/processed/evaluations/ai-report.json"


def evaluate_fixture(path: Path) -> dict[str, object]:
    fixture = JourneyFixture.model_validate_json(path.read_text(encoding="utf-8"))
    projection = project_journey(fixture.events)
    errors = list(dict.fromkeys(event.error_code for event in fixture.events if event.error_code))
    intent, confidence = classify_intent(projection.current_step, errors)
    expected_intent = (
        "SOURCE_OF_FUNDS_VERIFICATION"
        if fixture.expected_failure_count
        else "SOLE_PROPRIETOR_LOAN_APPLICATION"
    )
    return {
        "fixture": path.name,
        "state_correct": projection.status == fixture.expected_status
        and projection.current_step == fixture.expected_current_step,
        "failure_count_correct": projection.failure_count == fixture.expected_failure_count,
        "intent_correct": intent == expected_intent,
        "intent_confidence": confidence,
        "context_grounded": len(fixture.events) > 0,
    }


def evaluate() -> dict[str, object]:
    results = [evaluate_fixture(path) for path in sorted(FIXTURES.glob("*.json"))]
    checks = [
        "state_correct",
        "failure_count_correct",
        "intent_correct",
        "context_grounded",
    ]
    metrics = {
        key: round(sum(bool(result[key]) for result in results) / len(results), 3)
        if results
        else 0
        for key in checks
    }
    fallback = deterministic_embedding("fallback health check")
    report = {
        "version": "1.0",
        "fixture_count": len(results),
        "metrics": {
            **metrics,
            "fallback_success": float(len(fallback) == 64 and all(math.isfinite(value) for value in fallback)),
        },
        "fixtures": results,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    report = evaluate()
    print(json.dumps(report, ensure_ascii=False, indent=2))
