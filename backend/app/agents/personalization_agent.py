"""Personalization Agent (Phase 10: AI Agent Orchestration).
Evaluates explicit user feedback and non-sensitive listening duration,
generating structured personalization proposals without arbitrary execution.
"""
from typing import Optional, Dict
from pydantic import BaseModel

from .base import BaseAgent
from ..schemas.music import Track
from ..services.personalization_service import personalization_service


class PersonalizationAgentInput(BaseModel):
    user_id: str
    track: Track
    feedback_type: str  # like, dislike, skip, complete, play
    seconds_played: float
    mood_at_time: Optional[str] = None


class PersonalizationProposal(BaseModel):
    acknowledged: bool
    genre_updated: str
    feedback_type: str
    impact_summary: str


class PersonalizationAgent(BaseAgent[PersonalizationAgentInput, PersonalizationProposal]):
    def __init__(self):
        super().__init__(
            name="PersonalizationAgent",
            purpose="Evaluates explicit user feedback and non-sensitive listening duration to safely update user preference profiles.",
            allowed_tools=[
                "personalization_service.record_interaction",
                "personalization_service.get_user_profile"
            ],
            timeout_seconds=1.0,
            max_retries=1
        )

    async def execute(self, input_data: PersonalizationAgentInput) -> PersonalizationProposal:
        # Tool authorization check
        self.verify_tool_allowed("personalization_service.record_interaction")

        personalization_service.record_interaction(
            user_id=input_data.user_id,
            track=input_data.track,
            feedback_type=input_data.feedback_type,
            seconds_played=input_data.seconds_played,
            mood_at_time=input_data.mood_at_time
        )

        genre = input_data.track.profile.genre
        summary = f"Recorded {input_data.feedback_type.upper()} on '{input_data.track.title}' ({genre}). Personalization profile updated."

        return PersonalizationProposal(
            acknowledged=True,
            genre_updated=genre,
            feedback_type=input_data.feedback_type,
            impact_summary=summary
        )

    def fallback(self, input_data: PersonalizationAgentInput, error: Optional[str] = None) -> PersonalizationProposal:
        return PersonalizationProposal(
            acknowledged=False,
            genre_updated=input_data.track.profile.genre,
            feedback_type=input_data.feedback_type,
            impact_summary=f"Personalization update queued; fallback due to: {error}"
        )


personalization_agent = PersonalizationAgent()
