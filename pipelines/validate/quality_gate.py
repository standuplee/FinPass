"""Validate every normalized dataset against the pinned snapshot contract."""

import hashlib
import json
from argparse import ArgumentParser
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class Check:
    dataset: str
    name: str
    passed: bool
    expected: Any
    actual: Any


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def line_count(path: Path) -> int:
    with path.open("rb") as source:
        return sum(1 for _ in source)


def add_mapping_checks(
    checks: List[Check], dataset: str, prefix: str, expected: Dict[str, Any], actual: Dict[str, Any]
) -> None:
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        checks.append(
            Check(
                dataset=dataset,
                name="%s.%s" % (prefix, key),
                passed=actual_value == expected_value,
                expected=expected_value,
                actual=actual_value,
            )
        )


def validate_output_files(
    checks: List[Check], dataset: str, report: Dict[str, Any], expected_rows: Dict[str, int]
) -> None:
    output_paths = report.get("outputs", {})
    expected_hashes = report.get("output_sha256", {})
    for output_name, rows in expected_rows.items():
        raw_path = output_paths.get(output_name)
        path = Path(raw_path) if raw_path else Path("__missing_output__")
        exists = bool(raw_path) and path.is_file()
        checks.append(Check(dataset, "outputs.%s.exists" % output_name, exists, True, exists))
        if not exists:
            continue
        actual_rows = line_count(path)
        checks.append(
            Check(dataset, "outputs.%s.rows" % output_name, actual_rows == rows, rows, actual_rows)
        )
        expected_hash = expected_hashes.get(output_name)
        actual_hash = file_sha256(path)
        checks.append(
            Check(
                dataset,
                "outputs.%s.sha256" % output_name,
                bool(expected_hash) and actual_hash == expected_hash,
                expected_hash,
                actual_hash,
            )
        )


def evaluate(contract: Dict[str, Any]) -> List[Check]:
    checks: List[Check] = []
    for dataset, rules in contract["datasets"].items():
        report_path = Path(rules["report"])
        exists = report_path.is_file()
        checks.append(Check(dataset, "report.exists", exists, True, exists))
        if not exists:
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        add_mapping_checks(
            checks, dataset, "counts", rules.get("expected_counts", {}), report.get("counts", {})
        )
        add_mapping_checks(
            checks, dataset, "top_level", rules.get("expected_top_level", {}), report
        )
        add_mapping_checks(
            checks,
            dataset,
            "split_counts",
            rules.get("expected_split_counts", {}),
            report.get("split_counts", {}),
        )
        add_mapping_checks(
            checks,
            dataset,
            "label_scope_counts",
            rules.get("expected_label_scope_counts", {}),
            report.get("label_scope_counts", {}),
        )
        validate_output_files(checks, dataset, report, rules.get("jsonl_rows", {}))

        if dataset == "financial_products":
            persisted = report.get("privacy", {}).get("individual_consumer_rows_persisted")
            checks.append(
                Check(
                    dataset,
                    "privacy.individual_consumer_rows_persisted",
                    persisted is False,
                    False,
                    persisted,
                )
            )
        if dataset == "consultations":
            pii_scope = report.get("pii_scope", "")
            checks.append(
                Check(
                    dataset,
                    "privacy.pii_scope_disclosed",
                    "regex-only" in pii_scope,
                    "contains regex-only disclosure",
                    pii_scope,
                )
            )
    return checks


def render_report(contract_path: Path, checks: Iterable[Check]) -> Dict[str, Any]:
    check_list = list(checks)
    failed = [check for check in check_list if not check.passed]
    return {
        "gate_version": "1.0",
        "contract": str(contract_path),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASSED" if not failed else "FAILED",
        "total_checks": len(check_list),
        "passed_checks": len(check_list) - len(failed),
        "failed_checks": len(failed),
        "checks": [asdict(check) for check in check_list],
    }


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--contract", type=Path, default=Path("data/contracts/quality-gates.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/quality-gate.json")
    )
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    report = render_report(args.contract, evaluate(contract))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in report if key != "checks"}, indent=2))
    if report["status"] != "PASSED":
        for check in report["checks"]:
            if not check["passed"]:
                print(json.dumps(check, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
