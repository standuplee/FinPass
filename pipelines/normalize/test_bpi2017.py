import unittest

from pipelines.normalize.bpi2017 import (
    canonical_activity,
    event_family,
    parse_optional_bool,
    parse_optional_float,
)


class BpiNormalizationTest(unittest.TestCase):
    def test_maps_known_activities_without_changing_semantics(self) -> None:
        self.assertEqual(canonical_activity("A_Create Application"), "APPLICATION_CREATED")
        self.assertEqual(canonical_activity("O_Created"), "OFFER_CREATED")
        self.assertEqual(event_family("Workflow"), "WORKFLOW")

    def test_parses_optional_offer_values(self) -> None:
        self.assertIsNone(parse_optional_float(""))
        self.assertEqual(parse_optional_float("20000.0"), 20000.0)
        self.assertIsNone(parse_optional_bool(""))
        self.assertTrue(parse_optional_bool("true"))
        self.assertFalse(parse_optional_bool("false"))

    def test_unknown_activity_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            canonical_activity("A_Unknown")


if __name__ == "__main__":
    unittest.main()
