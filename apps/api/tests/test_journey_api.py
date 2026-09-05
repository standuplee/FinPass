from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def event_payload(
    journey_id: str,
    customer_id: str,
    session_id: str,
    event_type: str,
    step: str,
    status: str,
    occurred_at: datetime,
    retry_count: int = 0,
    error_code: str | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "event_id": str(uuid4()),
        "customer_id": customer_id,
        "journey_id": journey_id,
        "session_id": session_id,
        "channel": "CUSTOMER_APP",
        "event_type": event_type,
        "product_type": "SOLE_PROPRIETOR_LOAN",
        "journey_step": step,
        "status": status,
        "error_code": error_code,
        "retry_count": retry_count,
        "occurred_at": occurred_at.isoformat(),
        "duration_ms": 1000,
        "attributes": {},
    }


def test_create_append_replay_and_read_journey() -> None:
    created = client.post(
        "/api/v1/journeys",
        json={"customer_segment": {"customer_type": "SOLE_PROPRIETOR"}},
    )
    assert created.status_code == 201
    journey = created.json()
    journey_id = journey["id"]
    customer_id = journey["customer_id"]
    session_id = str(uuid4())
    clock = datetime(2026, 9, 6, tzinfo=UTC)

    started = event_payload(
        journey_id,
        customer_id,
        session_id,
        "JOURNEY_STARTED",
        "PRODUCT_SELECTION",
        "STARTED",
        clock,
    )
    first = client.post(
        f"/api/v1/journeys/{journey_id}/events",
        headers={"Idempotency-Key": "start-1"},
        json=started,
    )
    assert first.status_code == 200
    assert first.json()["idempotent_replay"] is False

    for retry in range(1, 4):
        clock += timedelta(seconds=30)
        failed = event_payload(
            journey_id,
            customer_id,
            session_id,
            "INCOME_VERIFICATION_FAILED",
            "INCOME_VERIFICATION",
            "FAILED",
            clock,
            retry_count=retry,
            error_code="A104",
        )
        response = client.post(
            f"/api/v1/journeys/{journey_id}/events",
            headers={"Idempotency-Key": f"income-failure-{retry}"},
            json=failed,
        )
        assert response.status_code == 200

    assert response.json()["journey_status"] == "ASSISTANCE_RECOMMENDED"
    replay = client.post(
        f"/api/v1/journeys/{journey_id}/events",
        headers={"Idempotency-Key": "income-failure-3"},
        json=failed,
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True

    timeline = client.get(f"/api/v1/journeys/{journey_id}")
    assert timeline.status_code == 200
    assert timeline.json()["status"] == "ASSISTANCE_RECOMMENDED"
    assert len(timeline.json()["events"]) == 4


def test_reused_idempotency_key_with_different_payload_conflicts() -> None:
    journey = client.post("/api/v1/journeys", json={}).json()
    payload = event_payload(
        journey["id"],
        journey["customer_id"],
        str(uuid4()),
        "JOURNEY_STARTED",
        "PRODUCT_SELECTION",
        "STARTED",
        datetime(2026, 9, 6, tzinfo=UTC),
    )
    endpoint = f"/api/v1/journeys/{journey['id']}/events"
    first = client.post(endpoint, headers={"Idempotency-Key": "same-key"}, json=payload)
    assert first.status_code == 200
    payload["event_id"] = str(uuid4())
    conflict = client.post(endpoint, headers={"Idempotency-Key": "same-key"}, json=payload)
    assert conflict.status_code == 409


def test_event_rejects_body_journey_mismatch_and_naive_timestamp() -> None:
    journey = client.post("/api/v1/journeys", json={}).json()
    payload = event_payload(
        str(uuid4()),
        journey["customer_id"],
        str(uuid4()),
        "JOURNEY_STARTED",
        "PRODUCT_SELECTION",
        "STARTED",
        datetime(2026, 9, 6, tzinfo=UTC),
    )
    endpoint = f"/api/v1/journeys/{journey['id']}/events"
    assert client.post(endpoint, json=payload).status_code == 409
    payload["journey_id"] = journey["id"]
    payload["occurred_at"] = "2026-09-06T00:00:00"
    assert client.post(endpoint, json=payload).status_code == 422
