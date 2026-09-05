"""Normalize BPI Challenge 2017 events and derive process features."""

import csv
import hashlib
import json
import os
import uuid
from argparse import ArgumentParser
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

DATASET_ID = "BPI_CHALLENGE_2017_CLEANED"
DATASET_SNAPSHOT_AT = "2026-09-05T00:00:00+00:00"
NORMALIZER_VERSION = "1.0"
ID_NAMESPACE = uuid.UUID("924dc17b-b331-4e55-8ced-d2cbf058a4af")

ACTIVITY_MAP = {
    "A_Create Application": "APPLICATION_CREATED",
    "A_Submitted": "APPLICATION_SUBMITTED",
    "A_Concept": "APPLICATION_CONCEPT_CREATED",
    "A_Accepted": "APPLICATION_ACCEPTED",
    "A_Complete": "APPLICATION_COMPLETED",
    "A_Validating": "APPLICATION_VALIDATING",
    "A_Pending": "APPLICATION_PENDING",
    "A_Incomplete": "APPLICATION_INCOMPLETE",
    "A_Cancelled": "APPLICATION_CANCELLED",
    "A_Denied": "APPLICATION_DENIED",
    "O_Create Offer": "OFFER_CREATE_REQUESTED",
    "O_Created": "OFFER_CREATED",
    "O_Sent (mail and online)": "OFFER_SENT_MAIL_AND_ONLINE",
    "O_Sent (online only)": "OFFER_SENT_ONLINE",
    "O_Returned": "OFFER_RETURNED",
    "O_Accepted": "OFFER_ACCEPTED",
    "O_Cancelled": "OFFER_CANCELLED",
    "O_Refused": "OFFER_REFUSED",
    "W_Handle leads": "WORK_HANDLE_LEADS",
    "W_Complete application": "WORK_COMPLETE_APPLICATION",
    "W_Call after offers": "WORK_CALL_AFTER_OFFERS",
    "W_Validate application": "WORK_VALIDATE_APPLICATION",
    "W_Call incomplete files": "WORK_CALL_INCOMPLETE_FILES",
    "W_Assess potential fraud": "WORK_ASSESS_POTENTIAL_FRAUD",
    "W_Shortened completion ": "WORK_SHORTENED_COMPLETION",
    "W_Personal Loan collection": "WORK_PERSONAL_LOAN_COLLECTION",
}

TERMINAL_OUTCOMES = {
    "APPLICATION_DENIED": "DENIED",
    "APPLICATION_CANCELLED": "CANCELLED",
    "APPLICATION_ACCEPTED": "ACCEPTED",
}

REWORK_SIGNAL_ACTIVITIES = {
    "APPLICATION_VALIDATING",
    "APPLICATION_INCOMPLETE",
    "WORK_COMPLETE_APPLICATION",
    "WORK_VALIDATE_APPLICATION",
    "WORK_CALL_INCOMPLETE_FILES",
}


def parse_optional_float(value: str) -> Optional[float]:
    return float(value) if value.strip() else None


def parse_optional_bool(value: str) -> Optional[bool]:
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError("unsupported boolean value: %s" % value)


def normalize_timestamp(value: str) -> str:
    return datetime.fromisoformat(value).isoformat()


def stable_uuid(record_type: str, source_id: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "%s:%s" % (record_type, source_id)))


def canonical_activity(activity: str) -> str:
    try:
        return ACTIVITY_MAP[activity]
    except KeyError as error:
        raise ValueError("unmapped BPI activity: %r" % activity) from error


def event_family(origin: str) -> str:
    mapping = {"Application": "APPLICATION", "Offer": "OFFER", "Workflow": "WORKFLOW"}
    try:
        return mapping[origin]
    except KeyError as error:
        raise ValueError("unmapped BPI event origin: %r" % origin) from error


def write_jsonl(stream: Any, record: Dict[str, Any]) -> None:
    stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def new_case(row: Dict[str, str], occurred_at: str) -> Dict[str, Any]:
    return {
        "source_case_id": row["case:concept:name"],
        "case_id": stable_uuid("case", row["case:concept:name"]),
        "loan_goal": row["case:LoanGoal"],
        "application_type": row["case:ApplicationType"],
        "requested_amount": parse_optional_float(row["case:RequestedAmount"]),
        "first_event_at": occurred_at,
        "last_event_at": occurred_at,
        "event_count": 0,
        "application_event_count": 0,
        "offer_event_count": 0,
        "workflow_event_count": 0,
        "offers_created": 0,
        "offers_accepted": 0,
        "incomplete_file_work_events": 0,
        "activity_counts": Counter(),
        "activity_lifecycle_counts": Counter(),
        "lifecycle_counts": Counter(),
        "outcome": "UNKNOWN",
    }


def update_case(case: Dict[str, Any], event: Dict[str, Any]) -> None:
    case["event_count"] += 1
    family_key = event["event_family"].lower() + "_event_count"
    case[family_key] += 1
    case["first_event_at"] = min(case["first_event_at"], event["occurred_at"])
    case["last_event_at"] = max(case["last_event_at"], event["occurred_at"])
    case["activity_counts"][event["activity"]] += 1
    case["activity_lifecycle_counts"][(event["activity"], event["lifecycle"])] += 1
    case["lifecycle_counts"][event["lifecycle"]] += 1
    case["offers_created"] += event["activity"] == "OFFER_CREATED"
    case["offers_accepted"] += event["activity"] == "OFFER_ACCEPTED"
    case["incomplete_file_work_events"] += event["activity"] == "WORK_CALL_INCOMPLETE_FILES"
    if event["activity"] in TERMINAL_OUTCOMES:
        case["outcome"] = TERMINAL_OUTCOMES[event["activity"]]


def finalize_case(case: Dict[str, Any]) -> Dict[str, Any]:
    start = datetime.fromisoformat(case["first_event_at"])
    end = datetime.fromisoformat(case["last_event_at"])
    repeated_completed = sorted(
        activity
        for (activity, lifecycle), count in case["activity_lifecycle_counts"].items()
        if lifecycle == "complete" and count > 1
    )
    rework_signals = sorted(set(repeated_completed) & REWORK_SIGNAL_ACTIVITIES)
    return {
        **{key: value for key, value in case.items() if not isinstance(value, Counter)},
        "duration_seconds": (end - start).total_seconds(),
        "activity_counts": dict(sorted(case["activity_counts"].items())),
        "lifecycle_counts": dict(sorted(case["lifecycle_counts"].items())),
        "repeated_completed_activities": repeated_completed,
        "rework_signal_activities": rework_signals,
        "has_rework": bool(rework_signals),
        "dataset_id": DATASET_ID,
        "normalizer_version": NORMALIZER_VERSION,
        "normalized_at": DATASET_SNAPSHOT_AT,
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(source_path: Path, output: Path) -> Dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    event_temp = output / "events.jsonl.tmp"
    case_temp = output / "case_features.jsonl.tmp"
    transition_temp = output / "transition_counts.jsonl.tmp"
    cases: Dict[str, Dict[str, Any]] = {}
    last_activity: Dict[str, str] = {}
    transitions: Counter = Counter()
    activity_counts: Counter = Counter()
    lifecycle_counts: Counter = Counter()
    origin_counts: Counter = Counter()
    seen_source_event_ids = set()
    seen_normalized_event_keys = set()
    repeated_source_event_ids = 0
    duplicate_normalized_events = 0
    rows = 0

    with source_path.open(encoding="utf-8-sig", newline="") as source, event_temp.open(
        "w", encoding="utf-8"
    ) as event_stream:
        reader = csv.DictReader(source)
        for row in reader:
            rows += 1
            source_event_id = row["EventID"]
            if source_event_id in seen_source_event_ids:
                repeated_source_event_ids += 1
            seen_source_event_ids.add(source_event_id)
            source_case_id = row["case:concept:name"]
            occurred_at = normalize_timestamp(row["time:timestamp"])
            activity = canonical_activity(row["concept:name"])
            family = event_family(row["EventOrigin"])
            normalized_event_key = "|".join(
                [source_event_id, row["concept:name"], row["lifecycle:transition"], occurred_at]
            )
            if normalized_event_key in seen_normalized_event_keys:
                duplicate_normalized_events += 1
            seen_normalized_event_keys.add(normalized_event_key)
            event = {
                "event_id": stable_uuid("event", normalized_event_key),
                "case_id": stable_uuid("case", source_case_id),
                "activity": activity,
                "event_family": family,
                "action": row["Action"],
                "lifecycle": row["lifecycle:transition"],
                "occurred_at": occurred_at,
                "resource": row["org:resource"] or None,
                "offer_id": row["OfferID"] or None,
                "offer": {
                    "first_withdrawal_amount": parse_optional_float(row["FirstWithdrawalAmount"]),
                    "number_of_terms": parse_optional_float(row["NumberOfTerms"]),
                    "accepted": parse_optional_bool(row["Accepted"]),
                    "monthly_cost": parse_optional_float(row["MonthlyCost"]),
                    "selected": parse_optional_bool(row["Selected"]),
                    "credit_score": parse_optional_float(row["CreditScore"]),
                    "offered_amount": parse_optional_float(row["OfferedAmount"]),
                },
                "provenance": {
                    "dataset_id": DATASET_ID,
                    "source_event_id": source_event_id,
                    "source_activity": row["concept:name"],
                    "normalizer_version": NORMALIZER_VERSION,
                    "normalized_at": DATASET_SNAPSHOT_AT,
                },
            }
            write_jsonl(event_stream, event)
            case = cases.setdefault(source_case_id, new_case(row, occurred_at))
            update_case(case, event)
            previous = last_activity.get(source_case_id)
            if previous:
                transitions[(previous, activity)] += 1
            last_activity[source_case_id] = activity
            activity_counts[activity] += 1
            lifecycle_counts[event["lifecycle"]] += 1
            origin_counts[family] += 1

    with case_temp.open("w", encoding="utf-8") as case_stream:
        for source_case_id in sorted(cases):
            write_jsonl(case_stream, finalize_case(cases[source_case_id]))

    with transition_temp.open("w", encoding="utf-8") as transition_stream:
        for (source_activity, target_activity), count in sorted(transitions.items()):
            write_jsonl(
                transition_stream,
                {"source_activity": source_activity, "target_activity": target_activity, "count": count},
            )

    outputs = {
        "events": output / "events.jsonl",
        "case_features": output / "case_features.jsonl",
        "transition_counts": output / "transition_counts.jsonl",
    }
    os.replace(event_temp, outputs["events"])
    os.replace(case_temp, outputs["case_features"])
    os.replace(transition_temp, outputs["transition_counts"])

    report = {
        "dataset_id": DATASET_ID,
        "normalizer_version": NORMALIZER_VERSION,
        "normalized_at": DATASET_SNAPSHOT_AT,
        "source_sha256": file_sha256(source_path),
        "counts": {
            "events": rows,
            "cases": len(cases),
            "unique_source_event_ids": len(seen_source_event_ids),
            "repeated_source_event_ids": repeated_source_event_ids,
            "unique_normalized_event_keys": len(seen_normalized_event_keys),
            "duplicate_normalized_events": duplicate_normalized_events,
            "transitions": sum(transitions.values()),
            "transition_types": len(transitions),
        },
        "activity_counts": dict(activity_counts.most_common()),
        "lifecycle_counts": dict(lifecycle_counts.most_common()),
        "origin_counts": dict(origin_counts.most_common()),
        "outputs": {key: str(path) for key, path in outputs.items()},
        "output_sha256": {key: file_sha256(path) for key, path in outputs.items()},
    }
    (output / "quality-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--source", type=Path, default=Path("data/raw/bpi2017/bpi_2017_cleaned.csv")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/process-events")
    )
    args = parser.parse_args()
    print(json.dumps(normalize(args.source, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
