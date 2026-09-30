"""AI Agent Orchestration Package (Phase 10: AI Agent Orchestration).
Exposes bounded, controlled AI agents and the central agent orchestrator.
"""
from .base import BaseAgent, AgentExecutionResult
from .mood_analysis_agent import (
    MoodAnalysisAgent, mood_analysis_agent,
    MoodAnalysisAgentInput, MoodAnalysisProposal
)
from .music_recommendation_agent import (
    RecommendationAgent, recommendation_agent,
    MusicRecommendationAgent, music_recommendation_agent,
    RecommendationAgentInput, RecommendationProposal,
    MusicRecommendationAgentInput, MusicRecommendationProposal
)
from .playlist_agent import (
    PlaylistAgent, playlist_agent,
    PlaylistAgentInput, PlaylistProposal
)
from .personalization_agent import (
    PersonalizationAgent, personalization_agent,
    PersonalizationAgentInput, PersonalizationProposal
)
from .evaluation_agent import (
    EvaluationAgent, evaluation_agent,
    EvaluationAgentInput, EvaluationProposal
)
from .orchestrator import (
    AgentOrchestrator, agent_orchestrator,
    OrchestrationCycleResult
)

__all__ = [
    "BaseAgent", "AgentExecutionResult",
    "MoodAnalysisAgent", "mood_analysis_agent", "MoodAnalysisAgentInput", "MoodAnalysisProposal",
    "RecommendationAgent", "recommendation_agent", "MusicRecommendationAgent", "music_recommendation_agent",
    "RecommendationAgentInput", "RecommendationProposal", "MusicRecommendationAgentInput", "MusicRecommendationProposal",
    "PlaylistAgent", "playlist_agent", "PlaylistAgentInput", "PlaylistProposal",
    "PersonalizationAgent", "personalization_agent", "PersonalizationAgentInput", "PersonalizationProposal",
    "EvaluationAgent", "evaluation_agent", "EvaluationAgentInput", "EvaluationProposal",
    "AgentOrchestrator", "agent_orchestrator", "OrchestrationCycleResult"
]
