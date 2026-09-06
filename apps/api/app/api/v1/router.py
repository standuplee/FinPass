from fastapi import APIRouter

from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.contracts import router as contracts_router
from app.api.v1.routes.journeys import router as journeys_router

router = APIRouter()
router.include_router(contracts_router, prefix="/contracts", tags=["contracts"])
router.include_router(journeys_router, prefix="/journeys", tags=["journeys"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
