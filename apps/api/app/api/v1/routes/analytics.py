from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database import get_session
from app.modules.journey.analytics import failures, insight, summarize
from app.modules.journey.schemas import AnalyticsFailure, AnalyticsInsight, AnalyticsSummary

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get("/journeys", response_model=AnalyticsSummary)
def get_journey_analytics(session: DatabaseSession) -> AnalyticsSummary:
    return summarize(session)


@router.get("/failures", response_model=list[AnalyticsFailure])
def get_failure_analytics(session: DatabaseSession) -> list[AnalyticsFailure]:
    return failures(session)


@router.get("/insights", response_model=AnalyticsInsight)
def get_analytics_insight(session: DatabaseSession) -> AnalyticsInsight:
    return insight(session)
