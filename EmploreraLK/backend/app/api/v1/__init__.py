from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.profile import router as profile_router
from app.api.v1.forecast import router as forecast_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.matching import router as matching_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(profile_router)
api_router.include_router(forecast_router)
api_router.include_router(notifications_router)
api_router.include_router(matching_router)

