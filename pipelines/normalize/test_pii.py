import unittest

from pipelines.normalize.pii import contains_structured_pii, redact_text


class PiiRedactionTest(unittest.TestCase):
    def test_redacts_supported_structured_identifiers(self) -> None:
        source = "user@example.com 010-1234-5678 900101-1234567"
        redacted, counts = redact_text(source)

        self.assertEqual(counts, {"email": 1, "resident_id": 1, "phone": 1})
        self.assertFalse(contains_structured_pii(redacted))
        self.assertNotIn("user@example.com", redacted)

    def test_plain_financial_text_is_unchanged(self) -> None:
        source = "소득인증 단계에서 오류가 세 번 발생했습니다."
        redacted, counts = redact_text(source)

        self.assertEqual(redacted, source)
        self.assertEqual(counts, {})


if __name__ == "__main__":
    unittest.main()
