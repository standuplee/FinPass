"""Validate generated FinPass journey, event, and failure feature records."""

import hashlib
import json
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterator


def rows(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        for line in source:
            yield json.loads(line)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(contract_path: Path, generated: Path) -> Dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    generation_report = json.loads((generated / "quality-report.json").read_text(encoding="utf-8"))
    errors = []
    journeys: Dict[str, Dict[str, Any]] = {}
    journey_scenarios: Counter = Counter()
    for journey in rows(generated / "journeys.jsonl"):
        journey_id = journey["journey_id"]
        if journey_id in journeys:
            errors.append("duplicate journey_id: %s" % journey_id)
        journeys[journey_id] = journey
        journey_scenarios[journey["scenario"]] += 1

    event_ids = set()
    event_counts: Counter = Counter()
    event_types: Counter = Counter()
    last_timestamp: Dict[str, str] = {}
    event_by_id: Dict[str, str] = {}
    support_journeys = set()
    resumed_journeys = set()
    event_rows = 0
    for event in rows(generated / "events.jsonl"):
        event_rows += 1
        event_id = event["event_id"]
        journey_id = event["journey_id"]
        if event_id in event_ids:
            errors.append("duplicate event_id: %s" % event_id)
        event_ids.add(event_id)
        event_by_id[event_id] = journey_id
        if journey_id not in journeys:
            errors.append("event references missing journey: %s" % journey_id)
        if journey_id in last_timestamp and event["occurred_at"] < last_timestamp[journey_id]:
            errors.append("event time reversal: %s" % journey_id)
        last_timestamp[journey_id] = event["occurred_at"]
        if event["status"] == "FAILED" and not event.get("error_code"):
            errors.append("failed event lacks error_code: %s" % event_id)
        if event["status"] != "FAILED" and event.get("error_code"):
            errors.append("non-failed event has error_code: %s" % event_id)
        if event["retry_count"] < 0 or (event.get("duration_ms") or 0) < 0:
            errors.append("negative event metric: %s" % event_id)
        event_counts[journey_id] += 1
        event_types[event["event_type"]] += 1
        if event["event_type"] == "SUPPORT_REQUESTED":
            support_journeys.add(journey_id)
        if event["event_type"] == "JOURNEY_RESUMED":
            resumed_journeys.add(journey_id)

    for journey_id, journey in journeys.items():
        if event_counts[journey_id] != journey["event_count"]:
            errors.append("journey event_count mismatch: %s" % journey_id)

    feature_ids = set()
    feature_targets: Counter = Counter()
    feature_rows = 0
    for feature in rows(generated / "failure_features.jsonl"):
        feature_rows += 1
        journey_id = feature["journey_id"]
        if journey_id in feature_ids:
            errors.append("duplicate feature journey_id: %s" % journey_id)
        feature_ids.add(journey_id)
        if journey_id not in journeys:
            errors.append("feature references missing journey: %s" % journey_id)
        if event_by_id.get(feature["as_of_event_id"]) != journey_id:
            errors.append("feature as_of event mismatch: %s" % journey_id)
        if journey_id in journeys and feature["target"] != journeys[journey_id]["scenario"]:
            errors.append("feature target mismatch: %s" % journey_id)
        feature_targets[feature["target"]] += 1

    expected_scenarios = contract["scenario_counts"]
    if dict(journey_scenarios) != expected_scenarios:
        errors.append("journey scenario distribution mismatch")
    if dict(feature_targets) != expected_scenarios:
        errors.append("feature target distribution mismatch")
    expected_support = expected_scenarios["ASSISTANCE_RECOMMENDED"] + expected_scenarios["CRITICAL_FAILURE"]
    if len(support_journeys) != expected_support:
        errors.append("support journey count mismatch")
    if support_journeys != resumed_journeys:
        errors.append("every support journey must resume in the generated end-to-end set")

    output_paths = {
        "journeys": generated / "journeys.jsonl",
        "events": generated / "events.jsonl",
        "failure_features": generated / "failure_features.jsonl",
    }
    actual_hashes = {key: file_sha256(path) for key, path in output_paths.items()}
    if actual_hashes != generation_report["output_sha256"]:
        errors.append("generated output hash mismatch")

    report = {
        "validator_version": "1.0",
        "status": "PASSED" if not errors else "FAILED",
        "errors": errors,
        "counts": {
            "journeys": len(journeys),
            "events": event_rows,
            "failure_features": feature_rows,
            "unique_event_ids": len(event_ids),
            "support_journeys": len(support_journeys),
            "resumed_journeys": len(resumed_journeys),
        },
        "scenario_counts": dict(journey_scenarios),
        "event_type_counts": dict(sorted(event_types.items())),
        "output_sha256": actual_hashes,
    }
    (generated / "validation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--contract", type=Path, default=Path("data/contracts/synthetic-journey-v1.json")
    )
    parser.add_argument(
        "--generated", type=Path, default=Path("data/synthetic/generated/v1")
    )
    args = parser.parse_args()
    report = validate(args.contract, args.generated)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "PASSED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
