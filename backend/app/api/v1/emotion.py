"""Emotion Estimation API Endpoint (Phase 3).
Integrates facial expression estimation strictly in-memory.

HUMAN-CENTERED PRINCIPLE:
Estimates visible facial expressions from camera frames.
Does NOT claim to represent the user's actual internal emotional state.
"""
from fastapi import APIRouter
from ...schemas.emotion import EmotionAnalyzeRequest, EmotionEstimationResponse
from ...services.emotion_detection_service import emotion_detection_service

router = APIRouter(prefix="/emotion", tags=["Emotion Estimation"])


@router.post("/detect", response_model=EmotionEstimationResponse)
async def detect_emotion(request: EmotionAnalyzeRequest):
    """
    Estimates visible facial expressions from an in-memory webcam frame.

    HUMAN-CENTERED & PRIVACY GUARANTEES:
    - Frames are processed strictly in RAM and immediately deallocated.
    - Result represents an 'estimated facial expression', not internal emotional truth.
    - Missing faces, timeouts, or corrupt frames safely return fallback neutral states with 0.0 confidence.
    """
    result = emotion_detection_service.estimate_emotion(request.image_base64)
    return EmotionEstimationResponse(**result)
