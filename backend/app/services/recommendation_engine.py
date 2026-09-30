"""Music Recommendation Engine (Phase 6: Music Recommendation Engine).
Orchestrates the structured recommendation pipeline:
1. Stable Mood + Jev Decision + Current Song + User Preferences + Recent Interactions
2. MusicProfileService -> Synthesizes target MusicProfile
3. CandidateRetrievalService -> Retrieves candidate tracks from catalog
4. RecommendationScoringService -> Multi-factor candidate scoring with configurable weights
5. Ranked Recommendations with RecommendationExplanation
"""
import time
import logging
from typing import List, Optional, Tuple

from ..config import settings
from ..schemas.mood import MoodState, MoodClass
from ..schemas.music import MusicProfile, Track, PlaybackState
from ..schemas.jev import (
    JevDecisionState,
    JevCurrentSongState,
    JevDecisionBundle,
    ConfidenceTier
)
from ..schemas.recommendation import (
    ScoredTrack,
    RecommendationResponse,
    RecommendationExplanation
)
from .jev_service import jev_decision_service, JevDecisionService
from .personalization_service import personalization_service
from .music_profile_service import music_profile_service, MusicProfileService
from .candidate_retrieval_service import candidate_retrieval_service, CandidateRetrievalService
from .recommendation_scoring_service import recommendation_scoring_service, RecommendationScoringService

logger = logging.getLogger("moodtune.recommendation_engine")


class RecommendationEngine:
    def __init__(
        self,
        jev: Optional[JevDecisionService] = None,
        profile_service: Optional[MusicProfileService] = None,
        candidate_service: Optional[CandidateRetrievalService] = None,
        scoring_service: Optional[RecommendationScoringService] = None
    ):
        self.jev = jev or jev_decision_service
        self.profile_service = profile_service or music_profile_service
        self.candidate_service = candidate_service or candidate_retrieval_service
        self.scoring_service = scoring_service or recommendation_scoring_service
        self.personalization = personalization_service

    async def generate_recommendations(
        self,
        mood_state: MoodState,
        playback_state: Optional[PlaybackState] = None,
        user_id: str = "default_user",
        limit: int = 5,
        force_transition: bool = False
    ) -> RecommendationResponse:
        start_time = time.perf_counter()

        # 1. Personalization context & recent interactions
        stats = self.personalization.get_recent_stats(user_id)
        prefs = self.personalization.get_preferences(user_id)

        # 2. Package current song state
        current_song_state = None
        current_track = None
        if playback_state and playback_state.current_track:
            cur = playback_state.current_track
            current_track = cur
            current_song_state = JevCurrentSongState(
                id=cur.id,
                title=cur.title,
                genre=cur.profile.genre,
                energy=cur.profile.energy,
                valence=cur.profile.valence,
                seconds_played=playback_state.position_seconds,
                duration=float(cur.duration_seconds)
            )

        # 3. Bounded Jev decision state
        jev_state = JevDecisionState(
            emotion_probabilities=mood_state.smoothed_emotion_probabilities.to_dict(),
            smoothed_mood=mood_state.estimated_mood.value,
            mood_confidence=mood_state.mood_confidence,
            current_song=current_song_state,
            recent_skips=stats["recent_skips"],
            recent_likes=stats["recent_likes"],
            seconds_played=playback_state.position_seconds if playback_state else 0.0,
            preferred_genres=prefs.preferred_genres
        )

        # 4. Jev Decision Execution
        jev_decision: JevDecisionBundle = self.jev.decide(jev_state)

        # 5. Synthesize target music profile via MusicProfileService
        target_profile, reasoning_text = self.profile_service.synthesize_profile(
            stable_mood=mood_state.estimated_mood.value,
            jev_decision=jev_decision,
            current_song=current_track,
            user_preferences=prefs,
            recent_skips=stats["recent_skips"],
            recent_likes=stats["recent_likes"]
        )

        # 6. Retrieve candidate pool via CandidateRetrievalService
        is_exploration = (getattr(jev_decision.strategy, "value", "mood_match") == "exploration")
        candidates = await self.candidate_service.retrieve_candidates(
            target_profile=target_profile,
            user_preferences=prefs,
            is_exploration=is_exploration,
            limit=limit * 3
        )

        # 7. Score & Rank candidates via RecommendationScoringService
        recent_track_ids = stats.get("recent_track_ids", [])
        recent_skipped_ids = stats.get("recent_skipped_ids", [])
        current_track_id = current_track.id if current_track else None

        scored_tracks = self.scoring_service.score_candidates(
            candidates=candidates,
            target_profile=target_profile,
            user_preferences=prefs,
            recent_played_ids=recent_track_ids,
            recent_skipped_ids=recent_skipped_ids,
            current_track_id=current_track_id,
            is_exploration=is_exploration
        )

        # Limit to requested count
        final_recommendations = scored_tracks[:limit]

        # 8. Determine final transition action
        transition_action = getattr(jev_decision.transition, "value", "continue")
        if force_transition:
            transition_action = "transition"

        return RecommendationResponse(
            recommendations=final_recommendations,
            target_profile=target_profile,
            jev_decision=jev_decision,
            transition_decision=transition_action,
            reasoning_summary=reasoning_text,
            evaluation_confidence=jev_decision.mood.confidence
        )


recommendation_engine = RecommendationEngine()
