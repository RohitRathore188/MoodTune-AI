"""Health and status endpoint."""
from fastapi import APIRouter
import time
from ...config import settings
from ...services.jev_service import HAS_TYPESAFE_SDK, jev_decision_service

router = APIRouter(prefix="/health", tags=["Health"])
START_TIME = time.time()


@router.get("")
async def get_health():
    uptime = time.time() - START_TIME
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(uptime, 1),
        "ai_providers": {
            "jev": {
                "configured": bool(jev_decision_service.api_key),
                "sdk_available": HAS_TYPESAFE_SDK,
                "model": settings.JEV_MODEL,
                "fallback_active": (jev_decision_service.client is None)
            },
            "music_provider": {
                "type": settings.MUSIC_PROVIDER_TYPE,
                "status": "active"
            },
            "camera_cv": {
                "status": "ready",
                "storage_policy": "in_memory_only (never persisted to disk/db)"
            }
        }
    }
