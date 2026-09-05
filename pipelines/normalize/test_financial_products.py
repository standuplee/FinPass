import unittest

from pipelines.normalize.financial_products import canonical_json, normalize_product_fields


class FinancialProductNormalizationTest(unittest.TestCase):
    def test_repairs_known_source_field_typographical_errors(self) -> None:
        normalized = normalize_product_fields(
            {"minimum_insured _premium": " 10000 ", "srarting_age": " 20 "}
        )
        self.assertEqual(normalized["minimum_insured_premium"], "10000")
        self.assertEqual(normalized["starting_age"], "20")

    def test_canonical_json_is_independent_of_key_order(self) -> None:
        self.assertEqual(canonical_json({"b": 2, "a": 1}), canonical_json({"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main()
