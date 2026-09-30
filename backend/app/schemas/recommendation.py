"""Recommendation Schemas."""
from typing import List, Optional
from pydantic import BaseModel, Field
from .music import Track, MusicProfile
from .jev import JevDecisionBundle


class RecommendationExplanation(BaseModel):
    reason_codes: List[str] = Field(
        default_factory=lambda: ["MOOD_MATCH", "ENERGY_MATCH", "USER_PREFERENCE"]
    )
    human_summary: str = "Recommended because it matches your current estimated mood and your listening preferences."


class ScoredTrack(BaseModel):
    track: Track
    match_score: float = Field(ge=0.0, le=1.0)
    explanation: RecommendationExplanation = Field(default_factory=RecommendationExplanation)
    match_reasons: List[str] = Field(default_factory=list)
    is_exploration: bool = False


class RecommendationRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    limit: int = 5
    force_transition: bool = False


class RecommendationResponse(BaseModel):
    recommendations: List[ScoredTrack]
    target_profile: MusicProfile
    jev_decision: JevDecisionBundle
    transition_decision: str  # continue, transition, retrieve_new_candidates
    reasoning_summary: str  # human-friendly explanation of why these songs were recommended
    evaluation_confidence: float


class FeedbackRequest(BaseModel):
    track_id: str
    feedback_type: str  # "like", "dislike", "skip", "complete"
    seconds_played: float
    mood_at_time: Optional[str] = None
