"""Jev Bounded Decision Schemas."""
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .mood import MoodClass


class EnergyChoice(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TransitionChoice(str, Enum):
    CONTINUE = "continue"
    TRANSITION = "transition"
    RETRIEVE_NEW_CANDIDATES = "retrieve_new_candidates"


class RecommendationStrategyChoice(str, Enum):
    MOOD_MATCH = "mood_match"
    PREFERENCE_MATCH = "preference_match"
    EXPLORATION = "exploration"
    SAFE_DEFAULT = "safe_default"


class ConfidenceTier(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class JevCurrentSongState(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    genre: Optional[str] = None
    energy: Optional[float] = None
    valence: Optional[float] = None
    seconds_played: float = 0.0
    duration: float = 0.0


class JevDecisionState(BaseModel):
    emotion_probabilities: Dict[str, float]
    smoothed_mood: str
    mood_confidence: float = Field(ge=0.0, le=1.0)
    current_song: Optional[JevCurrentSongState] = None
    recent_skips: int = 0
    recent_likes: int = 0
    seconds_played: float = 0.0
    preferred_genres: List[str] = Field(default_factory=list)


class DecisionResultItem(BaseModel):
    value: str
    confidence: float
    probabilities: Optional[Dict[str, float]] = None


class JevDecisionBundle(BaseModel):
    mood: DecisionResultItem
    energy: DecisionResultItem
    transition: DecisionResultItem
    strategy: DecisionResultItem
    confidence_tier: ConfidenceTier
    decision_source: str  # "jev_system_one" or "deterministic_fallback"
    latency_ms: float = 0.0
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

    @property
    def mood_class(self) -> DecisionResultItem:
        return self.mood

    @property
    def music_energy(self) -> DecisionResultItem:
        return self.energy

    @property
    def transition_decision(self) -> DecisionResultItem:
        return self.transition

    @property
    def recommendation_strategy(self) -> DecisionResultItem:
        return self.strategy

