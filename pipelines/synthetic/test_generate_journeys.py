import json
import random
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pipelines.synthetic.generate_journeys import generate_one, stable_uuid


CONTRACT = json.loads(Path("data/contracts/synthetic-journey-v1.json").read_text())
BPI_CASE = {"case_id": "case-1", "outcome": "ACCEPTED", "event_count": 20, "has_rework": False}
SEGMENT = {
    "customer_type": "sample",
    "age": "30",
    "gender": "M",
    "income_bracket": "sample",
    "occupation_group": "sample",
    "risk_grade": "sample",
}


class SyntheticJourneyTest(unittest.TestCase):
    def test_ids_are_stable(self) -> None:
        self.assertEqual(stable_uuid("journey", 1), stable_uuid("journey", 1))
        self.assertNotEqual(stable_uuid("journey", 1), stable_uuid("journey", 2))

    def test_assistance_journey_resumes_at_document_submission(self) -> None:
        journey, events, feature = generate_one(
            random.Random(1), CONTRACT, "ASSISTANCE_RECOMMENDED", 1, BPI_CASE, SEGMENT,
            datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        event_types = [event["event_type"] for event in events]
        self.assertEqual(event_types.count("INCOME_VERIFICATION_FAILED"), 3)
        self.assertIn("SUPPORT_REQUESTED", event_types)
        self.assertIn("JOURNEY_RESUMED", event_types)
        self.assertEqual(journey["status"], "COMPLETED")
        self.assertEqual(feature["target"], "ASSISTANCE_RECOMMENDED")
        self.assertEqual(feature["retry_count"], 3)

    def test_normal_journey_has_no_failure(self) -> None:
        _, events, feature = generate_one(
            random.Random(1), CONTRACT, "NORMAL", 2, BPI_CASE, SEGMENT,
            datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(any(event["status"] == "FAILED" for event in events))
        self.assertEqual(feature["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
