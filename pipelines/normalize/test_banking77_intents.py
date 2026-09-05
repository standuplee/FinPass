import unittest
from pathlib import Path

from pipelines.normalize.banking77_intents import load_mapping


MAPPING = Path("knowledge/taxonomy/banking77-map.json")


class Banking77IntentMappingTest(unittest.TestCase):
    def test_mapping_covers_all_labels(self) -> None:
        mapping = load_mapping(MAPPING)
        self.assertEqual(len(mapping), 77)

    def test_mvp_identity_and_income_labels_are_direct(self) -> None:
        mapping = load_mapping(MAPPING)
        self.assertEqual(mapping["unable_to_verify_identity"]["scope"], "DIRECT")
        self.assertEqual(
            mapping["verify_source_of_funds"]["journey_step"], "INCOME_VERIFICATION"
        )

    def test_out_of_scope_label_has_no_internal_intent(self) -> None:
        mapping = load_mapping(MAPPING)
        self.assertEqual(mapping["card_arrival"], {"scope": "OUT_OF_SCOPE"})


if __name__ == "__main__":
    unittest.main()
