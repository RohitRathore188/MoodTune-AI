"""Recommendation Scoring Service (Phase 6: Music Recommendation Engine).
Implements the multi-factor candidate scoring model:

score = (
      mood_match * w_mood
    + energy_match * w_energy
    + preference_match * w_pref
    + diversity * w_div
    + freshness * w_fresh
    - recent_skip_penalty * w_skip
)

NOTE ON WEIGHTS:
Weights are configurable via Settings or constructor injection for experimental
evaluation and A/B tuning. They are NOT claimed to be scientifically optimal.
"""
import logging
from typing import List, Optional, Dict, Any, Set

from ..config import settings
from ..schemas.music import Track, MusicProfile, UserPreferenceSchema
from ..schemas.recommendation import ScoredTrack, RecommendationExplanation

logger = logging.getLogger("moodtune.recommendation_scoring")


class ScoringWeights:
    """Configurable weights for the multi-factor scoring model."""
    def __init__(
        self,
        mood_match: Optional[float] = None,
        energy_match: Optional[float] = None,
        preference_match: Optional[float] = None,
        diversity: Optional[float] = None,
        freshness: Optional[float] = None,
        recent_skip_penalty: Optional[float] = None
    ):
        self.mood_match = mood_match if mood_match is not None else getattr(settings, "REC_WEIGHT_MOOD_MATCH", 0.35)
        self.energy_match = energy_match if energy_match is not None else getattr(settings, "REC_WEIGHT_ENERGY_MATCH", 0.25)
        self.preference_match = preference_match if preference_match is not None else getattr(settings, "REC_WEIGHT_PREFERENCE_MATCH", 0.20)
        self.diversity = diversity if diversity is not None else getattr(settings, "REC_WEIGHT_DIVERSITY", 0.10)
        self.freshness = freshness if freshness is not None else getattr(settings, "REC_WEIGHT_FRESHNESS", 0.10)
        self.recent_skip_penalty = recent_skip_penalty if recent_skip_penalty is not None else getattr(settings, "REC_PENALTY_RECENT_SKIP", 0.30)


class RecommendationScoringService:
    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()

    def score_candidates(
        self,
        candidates: List[Track],
        target_profile: MusicProfile,
        user_preferences: Optional[UserPreferenceSchema] = None,
        recent_played_ids: Optional[List[str]] = None,
        recent_skipped_ids: Optional[List[str]] = None,
        current_track_id: Optional[str] = None,
        is_exploration: bool = False
    ) -> List[ScoredTrack]:
        """
        Scores candidate tracks according to the configurable multi-factor model
        and generates explainable reason codes.
        """
        played_set: Set[str] = set(recent_played_ids or [])
        skipped_set: Set[str] = set(recent_skipped_ids or [])
        pref_genres = [g.lower() for g in (user_preferences.preferred_genres if user_preferences else ["lofi", "ambient"])]

        scored: List[ScoredTrack] = []

        for track in candidates:
            p = track.profile

            # 1. Mood Match (valence, tempo, danceability, and tag overlap)
            v_match = max(0.0, 1.0 - abs(p.valence - target_profile.valence))
            t_match = max(0.0, 1.0 - abs(p.tempo - target_profile.tempo))
            d_match = max(0.0, 1.0 - abs(p.danceability - target_profile.danceability))

            tag_overlap = 0.0
            if target_profile.mood_tags and p.mood_tags:
                common = set(target_profile.mood_tags) & set(p.mood_tags)
                tag_overlap = len(common) / max(1, len(target_profile.mood_tags))

            mood_match = (v_match * 0.40) + (t_match * 0.25) + (d_match * 0.15) + (tag_overlap * 0.20)
            mood_match = max(0.0, min(1.0, mood_match))

            # 2. Energy Match
            energy_match = max(0.0, 1.0 - abs(p.energy - target_profile.energy))

            # 3. Preference Match (genre alignment & user bias)
            genre_in_pref = 1.0 if p.genre.lower() in pref_genres else 0.2
            pref_match = genre_in_pref

            # 4. Diversity (encourage varied artists / exploration)
            diversity = 0.85
            if current_track_id and track.id == current_track_id:
                diversity = 0.10
            elif is_exploration:
                diversity = 1.0

            # 5. Freshness (bonus for unplayed tracks)
            freshness = 0.25 if track.id in played_set else 1.0

            # 6. Skip Penalty
            skip_penalty = 1.0 if track.id in skipped_set else 0.0

            # Compute weighted sum
            raw_score = (
                (mood_match * self.weights.mood_match)
                + (energy_match * self.weights.energy_match)
                + (pref_match * self.weights.preference_match)
                + (diversity * self.weights.diversity)
                + (freshness * self.weights.freshness)
                - (skip_penalty * self.weights.recent_skip_penalty)
            )

            # Clamp final match score in [0.05, 0.99]
            final_score = float(max(0.05, min(0.99, round(raw_score, 3))))

            # Formulate structured explanation reason codes
            reason_codes: List[str] = []
            if mood_match >= 0.65:
                reason_codes.append("MOOD_MATCH")
            if energy_match >= 0.70:
                reason_codes.append("ENERGY_MATCH")
            if pref_match >= 0.60:
                reason_codes.append("USER_PREFERENCE")
            if diversity >= 0.80 and is_exploration:
                reason_codes.append("DIVERSITY_DISCOVERY")
            if freshness >= 0.90:
                reason_codes.append("FRESHNESS")

            if not reason_codes:
                reason_codes = ["SAFE_DEFAULT"]

            # Human-friendly explanation adhering strictly to requirements:
            # "Recommended because it matches your current estimated mood and your listening preferences."
            # Never claims "This song will make you happy."
            human_summary = (
                "Recommended because it matches your current estimated mood and your listening preferences."
            )

            explanation = RecommendationExplanation(
                reason_codes=reason_codes,
                human_summary=human_summary
            )

            legacy_reasons = [
                f"Energy: {p.energy:.2f} (target {target_profile.energy:.2f})",
                f"Genre: {p.genre}"
            ]
            if "USER_PREFERENCE" in reason_codes:
                legacy_reasons.append("Matches preferred genres")

            scored.append(ScoredTrack(
                track=track,
                match_score=final_score,
                explanation=explanation,
                match_reasons=legacy_reasons,
                is_exploration=is_exploration
            ))

        # Sort descending by match score
        scored.sort(key=lambda item: item.match_score, reverse=True)
        return scored


recommendation_scoring_service = RecommendationScoringService()
