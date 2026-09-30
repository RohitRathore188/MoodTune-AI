"""Playlist Agent (Phase 10: AI Agent Orchestration).
Enforces transition policy, anti-thrashing rules, and queue sequencing.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

from .base import BaseAgent
from ..schemas.music import Track, PlaybackState
from ..config import settings


class PlaylistAgentInput(BaseModel):
    candidate_tracks: List[Track]
    current_queue: List[Track] = Field(default_factory=list)
    playback_state: Optional[PlaybackState] = None
    transition_decision: str = "continue"  # continue, transition, retrieve_new_candidates
    min_play_seconds: int = settings.MIN_PLAY_SECONDS_BEFORE_TRANSITION


class PlaylistProposal(BaseModel):
    should_switch_now: bool
    next_track: Optional[Track] = None
    updated_queue: List[Track]
    action_reason: str


class PlaylistAgent(BaseAgent[PlaylistAgentInput, PlaylistProposal]):
    def __init__(self):
        super().__init__(
            name="PlaylistAgent",
            purpose="Enforces transition policy, anti-thrashing rules, and queue sequencing before playback actions.",
            allowed_tools=["playback_manager.evaluate_transition", "queue_sequencer"],
            timeout_seconds=1.0,
            max_retries=1
        )

    async def execute(self, input_data: PlaylistAgentInput) -> PlaylistProposal:
        # Tool authorization check
        self.verify_tool_allowed("queue_sequencer")

        current_state = input_data.playback_state
        candidates = input_data.candidate_tracks

        if not candidates and not input_data.current_queue:
            return PlaylistProposal(
                should_switch_now=False,
                next_track=None,
                updated_queue=[],
                action_reason="No tracks available."
            )

        # Merge new candidates into queue (deduplicating)
        existing_ids = {t.id for t in input_data.current_queue}
        new_tracks = [t for t in candidates if t.id not in existing_ids]
        combined_queue = list(input_data.current_queue) + new_tracks

        # Check if no song is currently playing
        if not current_state or not current_state.current_track:
            next_track = combined_queue.pop(0) if combined_queue else (candidates[0] if candidates else None)
            return PlaylistProposal(
                should_switch_now=True,
                next_track=next_track,
                updated_queue=combined_queue,
                action_reason="No track active. Starting initial playback."
            )

        # Song is playing. Check anti-thrashing guardrails:
        pos = current_state.position_seconds
        cur_track = current_state.current_track
        play_ratio = pos / max(1.0, float(cur_track.duration_seconds))

        if input_data.transition_decision == "transition" or input_data.transition_decision == "retrieve_new_candidates":
            if pos < input_data.min_play_seconds and play_ratio < settings.FORCE_TRANSITION_PLAY_RATIO:
                # Anti-thrashing triggered: played for too short a time
                return PlaylistProposal(
                    should_switch_now=False,
                    next_track=None,
                    updated_queue=combined_queue,
                    action_reason=f"Transition held to prevent thrashing ({pos:.0f}s played < {input_data.min_play_seconds}s threshold)."
                )

            # Transition permitted
            next_track = combined_queue.pop(0) if combined_queue else None
            return PlaylistProposal(
                should_switch_now=True,
                next_track=next_track,
                updated_queue=combined_queue,
                action_reason=f"Transitioning to '{next_track.title if next_track else 'none'}' based on stable mood shift."
            )

        # Default action: continue current song
        return PlaylistProposal(
            should_switch_now=False,
            next_track=None,
            updated_queue=combined_queue,
            action_reason="Current track aligns with mood. Continuing playback."
        )

    def fallback(self, input_data: PlaylistAgentInput, error: Optional[str] = None) -> PlaylistProposal:
        return PlaylistProposal(
            should_switch_now=False,
            next_track=None,
            updated_queue=input_data.current_queue,
            action_reason=f"Playlist safety fallback: {error or 'unknown'}. Maintaining status quo."
        )


playlist_agent = PlaylistAgent()
