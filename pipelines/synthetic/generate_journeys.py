"""Generate deterministic sole proprietor loan journeys from approved data."""

import hashlib
import json
import math
import os
import random
import uuid
from argparse import ArgumentParser
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

GENERATOR_VERSION = "1.0"
ID_NAMESPACE = uuid.UUID("1870de29-7856-4168-be0f-13d27e22c88a")
PRODUCT_TYPE = "SOLE_PROPRIETOR_LOAN"


def stable_uuid(record_type: str, index: int, suffix: str = "") -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "%s:%s:%s" % (record_type, index, suffix)))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source]


def weighted_choice(randomizer: random.Random, values: List[Tuple[str, int]]) -> str:
    return randomizer.choices(
        population=[value for value, _ in values],
        weights=[weight for _, weight in values],
        k=1,
    )[0]


def load_segment_distributions(path: Path) -> Dict[str, List[Tuple[str, int]]]:
    distributions: Dict[str, List[Tuple[str, int]]] = {}
    for row in read_jsonl(path):
        dimensions = row["dimensions"]
        if len(dimensions) != 1:
            continue
        key, value = next(iter(dimensions.items()))
        distributions.setdefault(key, []).append((value, row["count"]))
    required = {"customer_type", "age", "gender", "income_bracket", "occupation_group", "risk_grade"}
    missing = required - set(distributions)
    if missing:
        raise ValueError("missing segment distributions: %s" % sorted(missing))
    return distributions


def sample_segment(
    randomizer: random.Random, distributions: Dict[str, List[Tuple[str, int]]]
) -> Dict[str, str]:
    return {
        key: weighted_choice(randomizer, distributions[key])
        for key in (
            "customer_type",
            "age",
            "gender",
            "income_bracket",
            "occupation_group",
            "risk_grade",
        )
    }


def sample_duration_ms(randomizer: random.Random, median_seconds: float) -> int:
    seconds = randomizer.lognormvariate(math.log(median_seconds), 0.35)
    return max(500, int(seconds * 1000))


def make_event(
    journey_index: int,
    event_index: int,
    customer_id: str,
    journey_id: str,
    session_id: str,
    channel: str,
    event_type: str,
    step: str,
    status: str,
    occurred_at: datetime,
    duration_ms: Optional[int] = None,
    retry_count: int = 0,
    error_code: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": stable_uuid("event", journey_index, str(event_index)),
        "customer_id": customer_id,
        "journey_id": journey_id,
        "session_id": session_id,
        "channel": channel,
        "event_type": event_type,
        "product_type": PRODUCT_TYPE,
        "journey_step": step,
        "status": status,
        "error_code": error_code,
        "retry_count": retry_count,
        "occurred_at": occurred_at.astimezone(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "attributes": attributes or {},
    }


def append_event(
    events: List[Dict[str, Any]],
    journey_index: int,
    customer_id: str,
    journey_id: str,
    session_id: str,
    channel: str,
    event_type: str,
    step: str,
    status: str,
    clock: datetime,
    duration_ms: int = 0,
    retry_count: int = 0,
    error_code: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> datetime:
    occurred_at = clock + timedelta(milliseconds=duration_ms)
    events.append(
        make_event(
            journey_index=journey_index,
            event_index=len(events),
            customer_id=customer_id,
            journey_id=journey_id,
            session_id=session_id,
            channel=channel,
            event_type=event_type,
            step=step,
            status=status,
            occurred_at=occurred_at,
            duration_ms=duration_ms,
            retry_count=retry_count,
            error_code=error_code,
            attributes=attributes,
        )
    )
    return occurred_at


def base_application_events(
    randomizer: random.Random,
    journey_index: int,
    customer_id: str,
    journey_id: str,
    session_id: str,
    started_at: datetime,
) -> Tuple[List[Dict[str, Any]], datetime]:
    events: List[Dict[str, Any]] = []
    clock = append_event(
        events, journey_index, customer_id, journey_id, session_id,
        "CUSTOMER_APP", "JOURNEY_STARTED", "PRODUCT_SELECTION", "STARTED", started_at,
    )
    for event_type, step, status, median in (
        ("PRODUCT_VIEWED", "PRODUCT_SELECTION", "SUCCEEDED", 8),
        ("BUSINESS_INFORMATION_COMPLETED", "BUSINESS_INFORMATION", "COMPLETED", 45),
        ("IDENTITY_VERIFICATION_STARTED", "IDENTITY_VERIFICATION", "STARTED", 2),
        ("IDENTITY_VERIFICATION_COMPLETED", "IDENTITY_VERIFICATION", "COMPLETED", 35),
        ("LIMIT_CHECK_STARTED", "LIMIT_CHECK", "STARTED", 2),
        ("LIMIT_CHECK_COMPLETED", "LIMIT_CHECK", "COMPLETED", 18),
        ("INCOME_VERIFICATION_STARTED", "INCOME_VERIFICATION", "STARTED", 3),
    ):
        clock = append_event(
            events, journey_index, customer_id, journey_id, session_id,
            "CUSTOMER_APP", event_type, step, status, clock,
            sample_duration_ms(randomizer, median),
        )
    return events, clock


def append_completion(
    randomizer: random.Random,
    events: List[Dict[str, Any]],
    journey_index: int,
    customer_id: str,
    journey_id: str,
    session_id: str,
    clock: datetime,
) -> datetime:
    for event_type, step, status, median in (
        ("DOCUMENT_UPLOAD_STARTED", "DOCUMENT_SUBMISSION", "STARTED", 3),
        ("DOCUMENT_UPLOAD_COMPLETED", "DOCUMENT_SUBMISSION", "COMPLETED", 75),
        ("JOURNEY_COMPLETED", "APPLICATION_COMPLETION", "COMPLETED", 5),
    ):
        clock = append_event(
            events, journey_index, customer_id, journey_id, session_id,
            "CUSTOMER_APP", event_type, step, status, clock,
            sample_duration_ms(randomizer, median),
        )
    return clock


def append_support_and_resume(
    randomizer: random.Random,
    events: List[Dict[str, Any]],
    journey_index: int,
    customer_id: str,
    journey_id: str,
    app_session_id: str,
    clock: datetime,
) -> Tuple[datetime, str]:
    clock = append_event(
        events, journey_index, customer_id, journey_id, app_session_id,
        "CUSTOMER_APP", "SUPPORT_REQUESTED", "SUPPORT", "REQUESTED", clock, 5000,
        attributes={"source_step": "INCOME_VERIFICATION"},
    )
    clock = append_event(
        events, journey_index, customer_id, journey_id, app_session_id,
        "CUSTOMER_APP", "CONTEXT_SHARING_CONSENTED", "SUPPORT", "COMPLETED", clock, 7000,
        attributes={"consent_scope": "JOURNEY_CONTEXT", "expires_in_minutes": 60},
    )
    call_session_id = stable_uuid("call-session", journey_index)
    clock = append_event(
        events, journey_index, customer_id, journey_id, call_session_id,
        "CALL_CENTER", "CALL_STARTED", "SUPPORT", "STARTED", clock,
        sample_duration_ms(randomizer, 20),
    )
    clock = append_event(
        events, journey_index, customer_id, journey_id, call_session_id,
        "CALL_CENTER", "DOCUMENT_REQUIRED", "DOCUMENT_SUBMISSION", "REQUESTED", clock,
        sample_duration_ms(randomizer, 180),
        attributes={"document_type": "ALTERNATIVE_INCOME_PROOF"},
    )
    clock = append_event(
        events, journey_index, customer_id, journey_id, call_session_id,
        "CALL_CENTER", "CALL_COMPLETED", "SUPPORT", "COMPLETED", clock,
        sample_duration_ms(randomizer, 45),
        attributes={"resume_step": "DOCUMENT_SUBMISSION"},
    )
    resume_session_id = stable_uuid("resume-session", journey_index)
    clock = append_event(
        events, journey_index, customer_id, journey_id, resume_session_id,
        "CUSTOMER_APP", "JOURNEY_RESUMED", "DOCUMENT_SUBMISSION", "STARTED", clock,
        sample_duration_ms(randomizer, 600),
        attributes={"resume_step": "DOCUMENT_SUBMISSION"},
    )
    clock = append_completion(
        randomizer, events, journey_index, customer_id, journey_id, resume_session_id, clock
    )
    return clock, resume_session_id


def generate_one(
    randomizer: random.Random,
    contract: Dict[str, Any],
    scenario: str,
    journey_index: int,
    bpi_case: Dict[str, Any],
    segment: Dict[str, str],
    started_at: datetime,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    customer_id = stable_uuid("customer", journey_index)
    journey_id = stable_uuid("journey", journey_index)
    session_id = stable_uuid("app-session", journey_index)
    events, clock = base_application_events(
        randomizer, journey_index, customer_id, journey_id, session_id, started_at
    )
    intervention_event_index = len(events) - 1
    retry_count = 0
    error_count = 0
    error_code = None

    if scenario == "NORMAL":
        clock = append_event(
            events, journey_index, customer_id, journey_id, session_id,
            "CUSTOMER_APP", "INCOME_VERIFICATION_COMPLETED", "INCOME_VERIFICATION",
            "COMPLETED", clock, sample_duration_ms(randomizer, 40),
        )
        intervention_event_index = len(events) - 1
        clock = append_completion(
            randomizer, events, journey_index, customer_id, journey_id, session_id, clock
        )
    elif scenario == "RETRY_EXPECTED":
        retry_count = 1
        error_count = 1
        error_code = contract["error_codes"]["retryable_income_verification"]
        clock = append_event(
            events, journey_index, customer_id, journey_id, session_id,
            "CUSTOMER_APP", "INCOME_VERIFICATION_FAILED", "INCOME_VERIFICATION", "FAILED",
            clock, sample_duration_ms(randomizer, 35), retry_count, error_code,
        )
        intervention_event_index = len(events) - 1
        clock = append_event(
            events, journey_index, customer_id, journey_id, session_id,
            "CUSTOMER_APP", "INCOME_VERIFICATION_COMPLETED", "INCOME_VERIFICATION",
            "COMPLETED", clock, sample_duration_ms(randomizer, 35), retry_count,
        )
        clock = append_completion(
            randomizer, events, journey_index, customer_id, journey_id, session_id, clock
        )
    elif scenario == "ASSISTANCE_RECOMMENDED":
        retry_count = 3
        error_count = 3
        error_code = contract["error_codes"]["retryable_income_verification"]
        for retry in range(1, 4):
            clock = append_event(
                events, journey_index, customer_id, journey_id, session_id,
                "CUSTOMER_APP", "INCOME_VERIFICATION_FAILED", "INCOME_VERIFICATION", "FAILED",
                clock, sample_duration_ms(randomizer, 35), retry, error_code,
            )
        intervention_event_index = len(events) - 1
        clock, _ = append_support_and_resume(
            randomizer, events, journey_index, customer_id, journey_id, session_id, clock
        )
    elif scenario == "CRITICAL_FAILURE":
        retry_count = 1
        error_count = 1
        error_code = contract["error_codes"]["critical_income_verification"]
        clock = append_event(
            events, journey_index, customer_id, journey_id, session_id,
            "CUSTOMER_APP", "INCOME_VERIFICATION_FAILED", "INCOME_VERIFICATION", "FAILED",
            clock, sample_duration_ms(randomizer, 60), retry_count, error_code,
        )
        intervention_event_index = len(events) - 1
        clock, _ = append_support_and_resume(
            randomizer, events, journey_index, customer_id, journey_id, session_id, clock
        )
    else:
        raise ValueError("unknown scenario: %s" % scenario)

    intervention_at = datetime.fromisoformat(events[intervention_event_index]["occurred_at"])
    feature = {
        "journey_id": journey_id,
        "as_of_event_id": events[intervention_event_index]["event_id"],
        "as_of_event_index": intervention_event_index,
        "retry_count": retry_count,
        "error_count": error_count,
        "step_duration_ms": sum(
            event["duration_ms"] or 0
            for event in events[: intervention_event_index + 1]
            if event["journey_step"] == "INCOME_VERIFICATION"
        ),
        "back_navigation_count": 0,
        "same_screen_repeat_count": retry_count,
        "session_duration_ms": int((intervention_at - started_at).total_seconds() * 1000),
        "previous_failure_count": int(bool(bpi_case.get("has_rework"))),
        "channel_transition_count": 0,
        "error_code": error_code,
        "target": scenario,
    }
    journey = {
        "schema_version": "1.0",
        "journey_id": journey_id,
        "customer_id": customer_id,
        "product_type": PRODUCT_TYPE,
        "scenario": scenario,
        "status": "COMPLETED",
        "started_at": started_at.isoformat(),
        "completed_at": clock.isoformat(),
        "event_count": len(events),
        "customer_segment": segment,
        "process_reference": {
            "bpi_case_id": bpi_case["case_id"],
            "bpi_outcome": bpi_case["outcome"],
            "bpi_event_count": bpi_case["event_count"],
            "bpi_has_rework": bpi_case["has_rework"],
        },
        "failure_feature_target": scenario,
        "generator_version": GENERATOR_VERSION,
        "seed": contract["seed"],
    }
    return journey, events, feature


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_prerequisites(contract: Dict[str, Any]) -> None:
    gate_path = Path(contract["source_reports"]["quality_gate"])
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASSED" or gate.get("failed_checks") != 0:
        raise ValueError("processed data quality gate must pass before generation")


def generate(contract_path: Path, output: Path) -> Dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    validate_prerequisites(contract)
    randomizer = random.Random(contract["seed"])
    bpi_cases = read_jsonl(Path(contract["source_reports"]["bpi_cases"]))
    distributions = load_segment_distributions(
        Path(contract["source_reports"]["consumer_segments"])
    )
    scenarios = [
        scenario
        for scenario, count in contract["scenario_counts"].items()
        for _ in range(count)
    ]
    if len(scenarios) != contract["journey_count"]:
        raise ValueError("scenario counts do not sum to journey_count")
    randomizer.shuffle(scenarios)
    start = datetime.fromisoformat(contract["time_window"]["start"])
    end = datetime.fromisoformat(contract["time_window"]["end"])
    window_seconds = int((end - start).total_seconds())
    output.mkdir(parents=True, exist_ok=True)
    temps = {
        "journeys": output / "journeys.jsonl.tmp",
        "events": output / "events.jsonl.tmp",
        "failure_features": output / "failure_features.jsonl.tmp",
    }
    counts: Counter = Counter()
    event_types: Counter = Counter()

    streams = {key: path.open("w", encoding="utf-8") for key, path in temps.items()}
    try:
        for index, scenario in enumerate(scenarios):
            bpi_case = randomizer.choice(bpi_cases)
            segment = sample_segment(randomizer, distributions)
            started_at = start + timedelta(seconds=randomizer.randint(0, window_seconds))
            journey, events, feature = generate_one(
                randomizer, contract, scenario, index, bpi_case, segment, started_at
            )
            streams["journeys"].write(json.dumps(journey, ensure_ascii=False, separators=(",", ":")) + "\n")
            streams["failure_features"].write(
                json.dumps(feature, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            for event in events:
                streams["events"].write(
                    json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
                )
                event_types[event["event_type"]] += 1
            counts[scenario] += 1
            counts["events"] += len(events)
    finally:
        for stream in streams.values():
            stream.close()

    outputs = {key: output / (key + ".jsonl") for key in temps}
    for key, temp in temps.items():
        os.replace(temp, outputs[key])
    report = {
        "schema_version": contract["schema_version"],
        "generator_version": GENERATOR_VERSION,
        "dataset_snapshot": contract["dataset_snapshot"],
        "seed": contract["seed"],
        "counts": {
            "journeys": contract["journey_count"],
            "events": counts["events"],
            "failure_features": contract["journey_count"],
        },
        "scenario_counts": {key: counts[key] for key in contract["scenario_counts"]},
        "event_type_counts": dict(sorted(event_types.items())),
        "source_counts": {"bpi_cases": len(bpi_cases)},
        "outputs": {key: str(path) for key, path in outputs.items()},
        "output_sha256": {key: file_sha256(path) for key, path in outputs.items()},
        "limitations": [
            "Customer segment dimensions are sampled independently from aggregate marginals.",
            "BPI references provide process complexity, not direct mobile event labels.",
            "Scenario prevalence is an MVP configuration, not an observed bank failure rate.",
        ],
    }
    (output / "quality-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--contract", type=Path, default=Path("data/contracts/synthetic-journey-v1.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/synthetic/generated/v1")
    )
    args = parser.parse_args()
    print(json.dumps(generate(args.contract, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
