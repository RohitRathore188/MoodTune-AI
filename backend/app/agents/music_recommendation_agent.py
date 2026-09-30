"""Recommendation Agent (Phase 10: AI Agent Orchestration).
Translates stable mood state, active music profile, and user preferences
into a ranked candidate recommendation proposal.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

from .base import BaseAgent
from ..schemas.mood import MoodState
from ..schemas.music import PlaybackState, Track, MusicProfile
from ..schemas.recommendation import ScoredTrack, RecommendationResponse
from ..services.recommendation_engine import recommendation_engine


class RecommendationAgentInput(BaseModel):
    mood_state: MoodState
    playback_state: Optional[PlaybackState] = None
    user_id: str = "default_user"
    limit: int = 5
    force_transition: bool = False


# Backward compatibility alias
MusicRecommendationAgentInput = RecommendationAgentInput


class RecommendationProposal(BaseModel):
    recommendations: List[ScoredTrack]
    target_profile: MusicProfile
    transition_decision: str
    reasoning: str
    confidence: float


# Backward compatibility alias
MusicRecommendationProposal = RecommendationProposal


class RecommendationAgent(BaseAgent[RecommendationAgentInput, RecommendationProposal]):
    def __init__(self):
        super().__init__(
            name="RecommendationAgent",
            purpose="Translates stable mood state, audio features, and user preferences into ranked candidate recommendation proposals.",
            allowed_tools=[
                "recommendation_engine.generate_recommendations",
                "music_profile_service.synthesize_profile",
                "candidate_retrieval_service.retrieve_candidates",
                "recommendation_scoring_service.score_candidates"
            ],
            timeout_seconds=2.5,
            max_retries=1
        )

    async def execute(self, input_data: RecommendationAgentInput) -> RecommendationProposal:
        # Tool authorization check
        self.verify_tool_allowed("recommendation_engine.generate_recommendations")

        resp: RecommendationResponse = await recommendation_engine.generate_recommendations(
            mood_state=input_data.mood_state,
            playback_state=input_data.playback_state,
            user_id=input_data.user_id,
            limit=input_data.limit,
            force_transition=input_data.force_transition
        )

        return RecommendationProposal(
            recommendations=resp.recommendations,
            target_profile=resp.target_profile,
            transition_decision=resp.transition_decision,
            reasoning=resp.reasoning_summary,
            confidence=resp.evaluation_confidence
        )

    def fallback(self, input_data: RecommendationAgentInput, error: Optional[str] = None) -> RecommendationProposal:
        # Fallback to neutral safe catalog
        safe_profile = MusicProfile(
            genre="lofi", energy=0.40, valence=0.50, tempo=0.45,
            instrumental=True, danceability=0.45, mood_tags=["safe_fallback"]
        )
        return RecommendationProposal(
            recommendations=[],
            target_profile=safe_profile,
            transition_decision="continue",
            reasoning=f"Recommendation fallback engaged: {error or 'service timeout'}.",
            confidence=0.30
        )


# Aliases
MusicRecommendationAgent = RecommendationAgent
recommendation_agent = RecommendationAgent()
music_recommendation_agent = recommendation_agent
