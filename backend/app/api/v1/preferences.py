"""User preferences and personalization profile endpoints (Phase 9)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal

from ...schemas.music import UserPreferenceSchema, UserPreferenceProfile
from ...services.personalization_service import personalization_service
from ...services.music_provider import music_provider

router = APIRouter(prefix="/preferences", tags=["Preferences & Personalization"])


class UserFeedbackActionRequest(BaseModel):
    track_id: str
    action: Literal["like", "dislike", "skip", "play", "complete"]
    seconds_played: float = Field(default=0.0, ge=0.0)
    mood: Optional[str] = None


@router.get("", response_model=UserPreferenceSchema)
async def get_preferences(user_id: str = "default_user"):
    """Returns user listening preferences."""
    return personalization_service.get_preferences(user_id)


@router.put("", response_model=UserPreferenceSchema)
async def update_preferences(prefs: UserPreferenceSchema, user_id: str = "default_user"):
    """Updates user listening preferences."""
    personalization_service.update_preferences(user_id, prefs)
    return personalization_service.get_preferences(user_id)


@router.get("/profile", response_model=UserPreferenceProfile)
async def get_user_profile(user_id: str = "default_user"):
    """
    Returns the comprehensive UserPreferenceProfile:
    {
      "preferred_genres": ["pop", "lofi"],
      "preferred_energy": 0.64,
      "preferred_tempo": 0.58,
      "skip_rate_by_genre": {}
    }
    """
    return personalization_service.get_user_profile(user_id)


@router.post("/feedback", response_model=UserPreferenceProfile)
async def record_feedback(req: UserFeedbackActionRequest, user_id: str = "default_user"):
    """Records interaction feedback (like, dislike, skip, complete, play) and updates telemetry."""
    track = await music_provider.get_track(req.track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    personalization_service.record_interaction(
        user_id=user_id,
        track=track,
        feedback_type=req.action,
        seconds_played=req.seconds_played,
        mood_at_time=req.mood
    )
    return personalization_service.get_user_profile(user_id)
