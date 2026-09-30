"""Music catalog, intelligent playback manager, and transition endpoints (Phase 8)."""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ...schemas.music import Track, PlaybackState, TransitionDecisionResult
from ...services.music_provider import music_provider
from ...services.playback_manager import playback_manager
from ...agents.evaluation_agent import evaluation_agent

router = APIRouter(prefix="/music", tags=["Music & Playback"])


class PlayActionRequest(BaseModel):
    track_id: Optional[str] = None
    position_seconds: float = 0.0


class SkipActionRequest(BaseModel):
    current_track_id: Optional[str] = None
    seconds_played: float = 0.0
    reason: str = "user_skip"


class AddToQueueRequest(BaseModel):
    track_id: str
    prepend: bool = False


class EvaluateTransitionRequest(BaseModel):
    current_mood: str
    mood_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    mood_stability: float = Field(default=5.0, ge=0.0)
    is_stable: bool = True
    current_track_progress: Optional[float] = None
    current_track_compatibility: Optional[float] = None
    auto_execute: bool = False


@router.get("/tracks", response_model=List[Track])
async def list_tracks():
    """Returns the full catalog available from the music provider."""
    return await music_provider.search_tracks(limit=50)


@router.get("/track/{track_id}", response_model=Track)
async def get_track(track_id: str):
    track = await music_provider.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@router.get("/search", response_model=List[Track])
async def search_music(
    q: Optional[str] = Query(default=None),
    genre: Optional[str] = Query(default=None),
    min_energy: Optional[float] = Query(default=None),
    max_energy: Optional[float] = Query(default=None),
    limit: int = Query(default=10)
):
    return await music_provider.search_tracks(
        query=q,
        genre=genre,
        min_energy=min_energy,
        max_energy=max_energy,
        limit=limit
    )


@router.get("/playback", response_model=PlaybackState)
async def get_playback_state():
    """Returns current active playback state enriched with queue and manual pause flags."""
    return playback_manager.get_playback_state()


@router.post("/play")
async def play_track(req: PlayActionRequest):
    track = None
    if req.track_id:
        track = await music_provider.get_track(req.track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

    state = await playback_manager.play(req.track_id, req.position_seconds)
    evaluation_agent.record_song_played()
    return {
        "status": "playing",
        "track": state.current_track,
        "position_seconds": state.position_seconds,
        "playback_state": state
    }


@router.post("/pause")
async def pause_track():
    state = await playback_manager.pause()
    return {
        "status": "paused",
        "position_seconds": state.position_seconds,
        "playback_state": state
    }


@router.post("/resume")
async def resume_track():
    state = await playback_manager.resume()
    return {
        "status": "playing" if state.is_playing else "idle",
        "playback_state": state
    }


@router.post("/skip")
async def skip_track(req: SkipActionRequest):
    state = await playback_manager.skip(reason=req.reason)
    return {
        "status": "skipped",
        "previous_track_id": req.current_track_id,
        "seconds_played": req.seconds_played,
        "playback_state": state
    }


@router.get("/queue", response_model=List[Track])
async def get_queue():
    """Returns upcoming queue tracks."""
    return playback_manager.get_queue()


@router.post("/queue/add")
async def add_to_queue(req: AddToQueueRequest):
    track = await music_provider.get_track(req.track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    playback_manager.add_to_queue(track, prepend=req.prepend)
    return {"status": "added", "track": track, "queue_size": len(playback_manager.queue)}


@router.post("/evaluate-transition", response_model=TransitionDecisionResult)
async def evaluate_transition_endpoint(req: EvaluateTransitionRequest):
    """
    Evaluates whether playback should transition given current mood and stability.
    Applies anti-thrashing rules, compatibility scoring, and Jev bounded decision.
    """
    return await playback_manager.evaluate_transition(
        current_mood=req.current_mood,
        mood_confidence=req.mood_confidence,
        mood_stability=req.mood_stability,
        is_stable=req.is_stable,
        current_track_progress=req.current_track_progress,
        current_track_compatibility=req.current_track_compatibility,
        auto_execute=req.auto_execute
    )
