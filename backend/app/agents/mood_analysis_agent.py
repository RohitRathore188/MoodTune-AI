"""Mood Analysis Agent (Phase 10: AI Agent Orchestration).
Estimates stable mood from facial expression probabilities and temporal history
using temporal smoothing without side effects.
"""
from typing import Optional, List
from pydantic import BaseModel, Field

from .base import BaseAgent
from ..schemas.mood import MoodClass, EmotionProbabilities, MoodState
from ..services.temporal_smoothing_service import temporal_smoothing_service


class MoodAnalysisAgentInput(BaseModel):
    session_id: str
    emotion_probabilities: EmotionProbabilities
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: Optional[float] = None
    manual_override: Optional[MoodClass] = None


class MoodAnalysisProposal(BaseModel):
    mood_state: MoodState
    reasoning: str
    requires_recommendation_update: bool


class MoodAnalysisAgent(BaseAgent[MoodAnalysisAgentInput, MoodAnalysisProposal]):
    def __init__(self):
        super().__init__(
            name="MoodAnalysisAgent",
            purpose="Estimates stable mood state from facial expression probabilities and temporal history without side effects.",
            allowed_tools=["temporal_smoothing_service.smooth_observation"],
            timeout_seconds=1.5,
            max_retries=1
        )

    async def execute(self, input_data: MoodAnalysisAgentInput) -> MoodAnalysisProposal:
        # Tool authorization check
        self.verify_tool_allowed("temporal_smoothing_service.smooth_observation")

        # Run temporal smoothing
        state = temporal_smoothing_service.smooth_observation(
            session_id=input_data.session_id,
            raw_probabilities=input_data.emotion_probabilities,
            confidence=input_data.confidence,
            timestamp=input_data.timestamp,
            manual_override=input_data.manual_override
        )

        reasoning = (
            f"Evaluated visible expressions. Stable mood: {state.estimated_mood.value} "
            f"(confidence={state.mood_confidence:.2f}, stable_for={state.stable_duration_seconds:.1f}s)"
        )

        return MoodAnalysisProposal(
            mood_state=state,
            reasoning=reasoning,
            requires_recommendation_update=state.transition_occurred
        )

    def fallback(self, input_data: MoodAnalysisAgentInput, error: Optional[str] = None) -> MoodAnalysisProposal:
        baseline_state = MoodState(
            estimated_mood=MoodClass.NEUTRAL,
            mood_confidence=0.35,
            smoothed_emotion_probabilities=input_data.emotion_probabilities,
            is_stable=True,
            stable_duration_seconds=1.0,
            transition_occurred=False
        )
        return MoodAnalysisProposal(
            mood_state=baseline_state,
            reasoning=f"Fallback engaged due to: {error or 'unknown error'}. Defaulting to neutral state.",
            requires_recommendation_update=False
        )


mood_analysis_agent = MoodAnalysisAgent()
