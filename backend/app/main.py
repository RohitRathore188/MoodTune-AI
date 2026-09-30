"""MoodTune AI - Main FastAPI Application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import init_db
from .api.v1.health import router as health_router
from .api.v1.mood import router as mood_router
from .api.v1.recommendations import router as recs_router
from .api.v1.music import router as music_router
from .api.v1.preferences import router as prefs_router
from .api.v1.history import router as history_router
from .api.v1.metrics import router as metrics_router
from .api.v1.camera import router as camera_router
from .api.v1.emotion import router as emotion_router
from .api.v1.evaluation import router as evaluation_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("moodtune.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MoodTune AI database and providers...")
    await init_db()
    logger.info("MoodTune AI application ready.")
    yield
    logger.info("Shutting down MoodTune AI.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Your mood. Your music. Production AI music recommendation system.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    if settings.DEBUG:
        import re
        raw_msg = str(exc)
        sanitized = re.sub(r'([A-Za-z]:\\[^\s]+|/(?:[^\s/]+/)+[^\s]+)', '[REDACTED_PATH]', raw_msg)
        sanitized = re.sub(r'(?:sqlite|postgres|mysql)(?:\+[a-z]+)?://\S+', '[REDACTED_DB_URL]', sanitized)
        client_msg = f"{type(exc).__name__}: {sanitized}"
    else:
        client_msg = "An unexpected error occurred. Please try again."

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": client_msg
        }
    )

# Register API v1 Routers
api_v1_prefix = settings.API_V1_STR
app.include_router(health_router, prefix=api_v1_prefix)
app.include_router(mood_router, prefix=api_v1_prefix)
app.include_router(recs_router, prefix=api_v1_prefix)
app.include_router(music_router, prefix=api_v1_prefix)
app.include_router(prefs_router, prefix=api_v1_prefix)
app.include_router(history_router, prefix=api_v1_prefix)
app.include_router(metrics_router, prefix=api_v1_prefix)
app.include_router(camera_router, prefix=api_v1_prefix)
app.include_router(emotion_router, prefix=api_v1_prefix)
app.include_router(evaluation_router, prefix=api_v1_prefix)


@app.get("/")
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "tagline": "Your mood. Your music.",
        "version": "1.0.0",
        "docs": "/docs",
        "health": f"{api_v1_prefix}/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
