"""Mood & Emotion Schemas adhering to Human-Centered vocabulary."""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MoodClass(str, Enum):
    ENERGETIC = "energetic"
    POSITIVE = "positive"
    CALM = "calm"
    NEUTRAL = "neutral"
    REFLECTIVE = "reflective"
    LOW_ENERGY = "low_energy"
    TENSE = "tense"


class EmotionType(str, Enum):
    HAPPY = "happy"
    NEUTRAL = "neutral"
    SURPRISE = "surprise"
    SAD = "sad"
    ANGRY = "angry"
    FEAR = "fear"
    DISGUST = "disgust"


class EmotionProbabilities(BaseModel):
    happy: float = Field(default=0.0, ge=0.0, le=1.0)
    neutral: float = Field(default=0.0, ge=0.0, le=1.0)
    surprise: float = Field(default=0.0, ge=0.0, le=1.0)
    sad: float = Field(default=0.0, ge=0.0, le=1.0)
    angry: float = Field(default=0.0, ge=0.0, le=1.0)
    fear: float = Field(default=0.0, ge=0.0, le=1.0)
    disgust: float = Field(default=0.0, ge=0.0, le=1.0)

    def to_dict(self) -> Dict[str, float]:
        return self.model_dump()


class FaceBoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class FaceDetectionResult(BaseModel):
    detected: bool
    face_count: int = 0
    bounding_box: Optional[FaceBoundingBox] = None
    expression_estimate: str
    emotion_probabilities: EmotionProbabilities
    confidence: float = Field(ge=0.0, le=1.0)
    inference_time_ms: float = 0.0


class MoodState(BaseModel):
    estimated_mood: MoodClass
    mood_confidence: float = Field(ge=0.0, le=1.0)
    smoothed_emotion_probabilities: EmotionProbabilities
    is_stable: bool
    stable_duration_seconds: float
    previous_mood: Optional[MoodClass] = None
    transition_occurred: bool = False


class MoodAnalysisRequest(BaseModel):
    image_base64: Optional[str] = Field(default=None, max_length=7_000_000, description="In-memory base64 frame (max ~5MB)")
    manual_mood_override: Optional[MoodClass] = None
    session_id: Optional[str] = None
    timestamp: Optional[float] = None


class MoodAnalysisResponse(BaseModel):
    face_detection: FaceDetectionResult
    mood_state: MoodState
    explanation: str  # Human-centered explanation: "Detected visible smile; mood estimated as positive"
    recommendation_trigger_needed: bool = False


class StableMoodResponse(BaseModel):
    mood: str
    confidence: float = Field(ge=0.0, le=1.0)
    stable_for_seconds: float
    is_stable: bool = True
    transition_detected: bool = False
    previous_mood: Optional[str] = None
    smoothed_emotions: Dict[str, float] = Field(default_factory=dict)
    face_detected: bool = True
    status_message: str = "Stable mood state"


class MoodSmoothRequest(BaseModel):
    emotions: Dict[str, float]
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    face_detected: bool = True
    timestamp: Optional[float] = None
    session_id: Optional[str] = "default_session"

