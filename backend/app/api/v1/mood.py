"""Mood analysis and session endpoints."""
import uuid
import time
from typing import Optional, Dict
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from ...schemas.mood import (
    MoodAnalysisRequest,
    MoodAnalysisResponse,
    MoodClass,
    MoodSmoothRequest,
    StableMoodResponse
)
from ...services.face_emotion_service import face_emotion_service
from ...services.mood_smoothing_service import mood_smoothing_service
from ...agents.mood_analysis_agent import mood_analysis_agent, MoodAnalysisAgentInput
from ...agents.evaluation_agent import evaluation_agent
from ...services.evaluation_service import evaluation_service
from ...services.rate_limiter import check_rate_limit

router = APIRouter(prefix="/mood", tags=["Mood Analysis"])

# Active sessions store
ACTIVE_SESSIONS = {}


@router.post("/analyze", response_model=MoodAnalysisResponse, dependencies=[Depends(check_rate_limit)])
async def analyze_mood(request: MoodAnalysisRequest):
    """
    Analyzes visible facial expressions from an in-memory webcam frame or manual override.
    PRIVACY GUARANTEE: Raw frames are strictly processed in-memory and immediately freed.
    """
    session_id = request.session_id or "default_session"

    # 1. Computer Vision & Affect Estimation
    face_result = face_emotion_service.analyze_frame(
        image_input=request.image_base64,
        manual_override=request.manual_mood_override
    )
    evaluation_agent.record_frame_analyzed(face_result.detected)
    evaluation_service.record_emotion_inference(
        latency_ms=face_result.inference_time_ms,
        confidence=face_result.confidence,
        detected=face_result.detected
    )

    # 2. Mood Analysis Agent (Temporal smoothing + hysteresis)
    agent_input = MoodAnalysisAgentInput(
        session_id=session_id,
        emotion_probabilities=face_result.emotion_probabilities,
        confidence=face_result.confidence,
        timestamp=request.timestamp,
        manual_override=request.manual_mood_override
    )
    agent_result = await mood_analysis_agent.run(agent_input)
    proposal = agent_result.proposal

    evaluation_service.record_mood_observation(
        confidence=proposal.mood_state.mood_confidence,
        is_stable=proposal.mood_state.is_stable,
        duration_sec=proposal.mood_state.stable_duration_seconds,
        transition_occurred=proposal.mood_state.transition_occurred
    )

    # Human-centered explanation formulation
    mood_name = proposal.mood_state.estimated_mood.value
    if face_result.detected:
        expr = face_result.expression_estimate
        explanation = (
            f"Detected visible expression '{expr}' with confidence {face_result.confidence:.2f}. "
            f"Estimated mood stabilized as '{mood_name}'."
        )
    else:
        explanation = (
            f"Face currently out of frame. Estimated mood safely maintained as '{mood_name}'."
        )

    return MoodAnalysisResponse(
        face_detection=face_result,
        mood_state=proposal.mood_state,
        explanation=explanation,
        recommendation_trigger_needed=proposal.requires_recommendation_update
    )


@router.post("/smooth", response_model=StableMoodResponse)
async def smooth_mood(request: MoodSmoothRequest):
    """
    Ingests emotion probabilities and updates the temporal mood smoothing engine.
    Returns the stabilized mood state with confidence and stable_for_seconds.
    """
    session_id = request.session_id or "default_session"
    result = mood_smoothing_service.process_observation(
        emotion_probabilities=request.emotions,
        confidence=request.confidence,
        face_detected=request.face_detected,
        timestamp=request.timestamp,
        session_id=session_id
    )
    return StableMoodResponse(**result)


@router.get("/current", response_model=StableMoodResponse)
async def get_current_stable_mood(session_id: str = "default_session"):
    """
    Returns the currently established stable mood state for a session.
    """
    result = mood_smoothing_service.get_current_mood(session_id)
    return StableMoodResponse(**result)


@router.post("/session/start")
async def start_session():
    """Initiates a new listening and mood estimation session."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    ACTIVE_SESSIONS[session_id] = {
        "started_at": time.time(),
        "frames": 0
    }
    return {
        "session_id": session_id,
        "status": "started",
        "message": "Session initialized. Camera frames are processed strictly in-memory."
    }


@router.post("/session/stop")
async def stop_session(session_id: str):
    """Stops the active session and clears ephemeral smoothing buffers."""
    from ...services.temporal_smoothing_service import temporal_smoothing_service
    temporal_smoothing_service.reset_session(session_id)
    mood_smoothing_service.reset_session(session_id)
    session_data = ACTIVE_SESSIONS.pop(session_id, None)
    return {
        "session_id": session_id,
        "status": "stopped",
        "duration_seconds": round(time.time() - session_data["started_at"], 1) if session_data else 0.0
    }


class OrchestrateRequest(BaseModel):
    image_base64: Optional[str] = None
    emotions: Optional[Dict[str, float]] = None
    confidence: float = 0.85
    session_id: str = "default_session"
    user_id: str = "default_user"
    manual_mood_override: Optional[MoodClass] = None
    auto_execute_playback: bool = True


@router.post("/orchestrate")
async def orchestrate_mood_and_music(req: OrchestrateRequest):
    """
    Executes the full controlled agent orchestration pipeline:
    Emotion Model -> Mood Analysis Agent -> JEV Decision Layer -> Recommendation Agent -> Music Provider -> Playback Manager
    """
    from ...agents.orchestrator import agent_orchestrator
    from ...schemas.mood import EmotionProbabilities

    # If raw frame provided, analyze affect
    if req.image_base64:
        face_res = face_emotion_service.analyze_frame(
            image_input=req.image_base64,
            manual_override=req.manual_mood_override
        )
        raw_emotions = face_res.emotion_probabilities
        conf = face_res.confidence
    elif req.emotions:
        raw_emotions = EmotionProbabilities(**req.emotions)
        conf = req.confidence
    else:
        raw_emotions = EmotionProbabilities(neutral=1.0)
        conf = 0.50

    cycle_result = await agent_orchestrator.run_pipeline(
        emotion_probabilities=raw_emotions,
        emotion_confidence=conf,
        session_id=req.session_id,
        user_id=req.user_id,
        manual_mood_override=req.manual_mood_override,
        auto_execute_playback=req.auto_execute_playback
    )
    return cycle_result
