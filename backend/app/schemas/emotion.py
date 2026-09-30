"""Pydantic Schemas for Facial Expression & Emotion Estimation (Phase 3).
Strictly adheres to Human-Centered Principles:
Does not claim to know actual internal emotional state.
Uses: "estimated facial expression".
"""
from typing import Dict, Optional, Any
import numpy as np
from pydantic import BaseModel, Field, model_validator


class EmotionsDistribution(BaseModel):
    happy: float = Field(default=0.0, ge=0.0, le=1.0)
    sad: float = Field(default=0.0, ge=0.0, le=1.0)
    angry: float = Field(default=0.0, ge=0.0, le=1.0)
    neutral: float = Field(default=0.0, ge=0.0, le=1.0)
    fear: float = Field(default=0.0, ge=0.0, le=1.0)
    surprise: float = Field(default=0.0, ge=0.0, le=1.0)
    disgust: float = Field(default=0.0, ge=0.0, le=1.0)

    @model_validator(mode="before")
    @classmethod
    def sanitize_and_normalize(cls, data: Any):
        if not isinstance(data, dict):
            return data
        keys = ("happy", "sad", "angry", "neutral", "fear", "surprise", "disgust")
        cleaned = {}
        for k in keys:
            v = data.get(k, 0.0)
            try:
                fv = float(v)
                if np.isnan(fv) or np.isinf(fv) or fv < 0.0:
                    fv = 0.0
            except (ValueError, TypeError):
                fv = 0.0
            cleaned[k] = fv

        total = sum(cleaned.values())
        if total <= 0.0:
            cleaned["neutral"] = 1.0
            return cleaned

        norm = {k: round(v / total, 4) for k, v in cleaned.items()}
        diff = round(1.0 - sum(norm.values()), 4)
        norm["neutral"] = round(norm["neutral"] + diff, 4)
        return norm

    def to_dict(self) -> Dict[str, float]:
        return {
            "happy": round(self.happy, 4),
            "sad": round(self.sad, 4),
            "angry": round(self.angry, 4),
            "neutral": round(self.neutral, 4),
            "fear": round(self.fear, 4),
            "surprise": round(self.surprise, 4),
            "disgust": round(self.disgust, 4),
        }


class EmotionEstimationResponse(BaseModel):
    emotions: EmotionsDistribution
    dominant_emotion: str
    confidence: float = Field(ge=0.0, le=1.0)
    expression_type: str = "estimated facial expression"
    face_detected: bool = False
    inference_time_ms: float = 0.0
    status_message: str = "Estimated visible facial expression"


class EmotionAnalyzeRequest(BaseModel):
    image_base64: Optional[str] = Field(default=None, max_length=7_000_000, description="In-memory base64 frame (max ~5MB)")
    timestamp: Optional[float] = None
