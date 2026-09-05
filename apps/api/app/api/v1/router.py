from fastapi import APIRouter

from app.api.v1.routes.contracts import router as contracts_router

router = APIRouter()
router.include_router(contracts_router, prefix="/contracts", tags=["contracts"])
