"""Mood history and explicit privacy controls."""
from fastapi import APIRouter, Query
from ...services.temporal_smoothing_service import temporal_smoothing_service

router = APIRouter(prefix="/history", tags=["History & Privacy"])


@router.get("")
async def get_mood_history(session_id: str = Query(default="default_session")):
    """Returns recent smoothed mood timeline for visualization."""
    history = temporal_smoothing_service.get_session_history(session_id)
    return {
        "session_id": session_id,
        "observations_count": len(history),
        "history": history
    }


@router.post("/clear")
async def clear_mood_history(session_id: str = Query(default="default_session")):
    """
    EXPLICIT PRIVACY CONTROL:
    Wipes all temporal smoothing buffers, candidate hypotheses, and observation history.
    """
    temporal_smoothing_service.reset_session(session_id)
    return {
        "status": "cleared",
        "session_id": session_id,
        "message": "All mood history and ephemeral buffers have been securely cleared."
    }
