import unittest
from pathlib import Path

from pipelines.validate.quality_gate import Check, render_report


class QualityGateTest(unittest.TestCase):
    def test_report_passes_when_all_checks_pass(self) -> None:
        report = render_report(
            contract_path=Path("contract.json"),
            checks=[Check("sample", "rows", True, 10, 10)],
        )
        self.assertEqual(report["status"], "PASSED")
        self.assertEqual(report["failed_checks"], 0)

    def test_report_fails_when_a_check_fails(self) -> None:
        report = render_report(
            contract_path=Path("contract.json"),
            checks=[Check("sample", "rows", False, 10, 9)],
        )
        self.assertEqual(report["status"], "FAILED")
        self.assertEqual(report["failed_checks"], 1)


if __name__ == "__main__":
    unittest.main()
