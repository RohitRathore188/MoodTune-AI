"""Recommendations and feedback endpoints."""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from ...schemas.recommendation import (
    RecommendationResponse,
    FeedbackRequest
)
from ...schemas.mood import MoodState, MoodClass, EmotionProbabilities
from ...schemas.music import PlaybackState
from ...services.recommendation_engine import recommendation_engine
from ...services.music_provider import music_provider
from ...agents.personalization_agent import personalization_agent, PersonalizationAgentInput
from ...agents.evaluation_agent import evaluation_agent
from ...services.evaluation_service import evaluation_service

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("", response_model=RecommendationResponse)
async def get_recommendations(
    mood: MoodClass = Query(default=MoodClass.NEUTRAL),
    confidence: float = Query(default=0.85, ge=0.0, le=1.0),
    current_song_id: Optional[str] = Query(default=None),
    seconds_played: float = Query(default=0.0),
    limit: int = Query(default=5, ge=1, le=15),
    force_transition: bool = Query(default=False)
):
    """
    Computes context-aware music recommendations based on estimated mood,
    Jev bounded decision, and current playback state.
    """
    # Build playback state if current track specified
    playback_state = None
    if current_song_id:
        track = await music_provider.get_track(current_song_id)
        if track:
            playback_state = PlaybackState(
                current_track=track,
                is_playing=True,
                position_seconds=seconds_played
            )

    # Reconstruct MoodState
    mood_state = MoodState(
        estimated_mood=mood,
        mood_confidence=confidence,
        smoothed_emotion_probabilities=EmotionProbabilities(
            happy=0.8 if mood in [MoodClass.POSITIVE, MoodClass.ENERGETIC] else 0.1,
            neutral=0.8 if mood == MoodClass.NEUTRAL else 0.2,
            sad=0.7 if mood == MoodClass.LOW_ENERGY else 0.05,
            angry=0.7 if mood == MoodClass.TENSE else 0.05
        ),
        is_stable=True,
        stable_duration_seconds=5.0
    )

    resp = await recommendation_engine.generate_recommendations(
        mood_state=mood_state,
        playback_state=playback_state,
        user_id="default_user",
        limit=limit,
        force_transition=force_transition
    )

    # Record telemetry
    evaluation_agent.record_decision(resp.jev_decision.decision_source)
    evaluation_service.record_recommendations_served(len(resp.recommendations))
    evaluation_service.record_jev_decision(
        latency_ms=resp.jev_decision.latency_ms,
        success=(resp.jev_decision.error_message is None),
        is_fallback=(resp.jev_decision.decision_source != "jev_system_one")
    )
    return resp


@router.post("/feedback")
async def record_feedback(feedback: FeedbackRequest):
    """
    Records explicit user feedback (like, dislike, skip, complete)
    to update personalization weights.
    """
    track = await music_provider.get_track(feedback.track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    input_data = PersonalizationAgentInput(
        user_id="default_user",
        track=track,
        feedback_type=feedback.feedback_type,
        seconds_played=feedback.seconds_played,
        mood_at_time=feedback.mood_at_time
    )
    result = await personalization_agent.run(input_data)

    evaluation_service.record_playback_event(
        event_type=feedback.feedback_type,
        seconds_played=feedback.seconds_played
    )

    return {
        "status": "success",
        "acknowledged": result.proposal.acknowledged,
        "impact": result.proposal.impact_summary
    }
