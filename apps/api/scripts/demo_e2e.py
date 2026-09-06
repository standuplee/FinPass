"""Run the representative Customer -> Agent -> Admin MVP flow."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)
    journey = client.post(
        "/api/v1/journeys", json={"customer_segment": {"demo": "e2e"}}
    ).json()
    journey_id = journey["id"]
    now = datetime.now(UTC) - timedelta(seconds=10)
    for retry in range(1, 4):
        response = client.post(
            f"/api/v1/journeys/{journey_id}/events",
            json={
                "event_id": str(uuid4()),
                "customer_id": journey["customer_id"],
                "journey_id": journey_id,
                "session_id": str(uuid4()),
                "channel": "CUSTOMER_APP",
                "event_type": "INCOME_VERIFICATION_FAILED",
                "product_type": "SOLE_PROPRIETOR_LOAN",
                "journey_step": "INCOME_VERIFICATION",
                "status": "FAILED",
                "error_code": "A104",
                "retry_count": retry,
                "occurred_at": (now + timedelta(seconds=retry)).isoformat(),
                "attributes": {},
            },
        )
        response.raise_for_status()
    consent = client.post(f"/api/v1/journeys/{journey_id}/consents", json={}).json()
    context = client.post(
        f"/api/v1/journeys/{journey_id}/context-pass",
        params={"consent_id": consent["id"]},
    ).json()
    consultation = client.post(
        f"/api/v1/journeys/context-pass/{context['id']}/consultations"
    ).json()
    completed = client.post(
        f"/api/v1/journeys/consultations/{consultation['id']}/complete",
        json={"outcome": "대체 소득증빙 안내", "next_step": "DOCUMENT_SUBMISSION"},
    ).json()
    resumed = client.get(f"/api/v1/journeys/{journey_id}").json()
    analytics = client.get("/api/v1/analytics/journeys").json()
    print(
        {
            "journey_id": journey_id,
            "context_pass_id": context["id"],
            "consultation_status": completed["status"],
            "resume_status": resumed["status"],
            "resume_step": resumed["current_step"],
            "analytics_total": analytics["total_journeys"],
        }
    )


if __name__ == "__main__":
    main()
