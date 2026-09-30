"""Music Profile Service (Phase 6: Music Recommendation Engine).
Synthesizes a target MusicProfile by integrating:
- Stable Mood
- Jev Decision (bounded target energy, strategy, confidence tier)
- Current Song State (acoustic continuity)
- User Preferences (energy bias, preferred/disliked genres)
- Recent Interactions (skips, likes)

Never uses simplistic: if happy -> happy_song.
Instead applies multidimensional acoustic feature synthesis.
"""
import logging
from typing import Dict, Any, Optional, Tuple, List

from ..config import settings
from ..schemas.mood import MoodClass
from ..schemas.music import MusicProfile, Track, UserPreferenceSchema
from ..schemas.jev import JevDecisionBundle, ConfidenceTier

logger = logging.getLogger("moodtune.music_profile")

# Acoustic archetypes across the valence-arousal space
MOOD_ACOUSTIC_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "energetic": {
        "genre": "synthwave",
        "energy": 0.88,
        "valence": 0.80,
        "tempo": 0.82,
        "danceability": 0.85,
        "instrumental": 0.60,
        "mood_tags": ["energetic", "high-tempo", "driving"]
    },
    "positive": {
        "genre": "upbeat_pop",
        "energy": 0.75,
        "valence": 0.85,
        "tempo": 0.72,
        "danceability": 0.78,
        "instrumental": 0.15,
        "mood_tags": ["uplifting", "positive", "bright"]
    },
    "calm": {
        "genre": "ambient",
        "energy": 0.25,
        "valence": 0.65,
        "tempo": 0.30,
        "danceability": 0.20,
        "instrumental": 0.90,
        "mood_tags": ["calm", "relaxing", "peaceful"]
    },
    "neutral": {
        "genre": "lofi",
        "energy": 0.45,
        "valence": 0.50,
        "tempo": 0.45,
        "danceability": 0.50,
        "instrumental": 0.75,
        "mood_tags": ["focus", "neutral", "study"]
    },
    "reflective": {
        "genre": "indie_folk",
        "energy": 0.35,
        "valence": 0.42,
        "tempo": 0.38,
        "danceability": 0.30,
        "instrumental": 0.40,
        "mood_tags": ["reflective", "acoustic", "introspective"]
    },
    "low_energy": {
        "genre": "ambient",
        "energy": 0.20,
        "valence": 0.35,
        "tempo": 0.25,
        "danceability": 0.15,
        "instrumental": 0.85,
        "mood_tags": ["comfort", "gentle", "low_energy"]
    },
    "tense": {
        "genre": "meditation",
        "energy": 0.20,
        "valence": 0.55,
        "tempo": 0.25,
        "danceability": 0.15,
        "instrumental": 0.95,
        "mood_tags": ["soothing", "de-stress", "unwind"]
    },
}


class MusicProfileService:
    """Synthesizes structured MusicProfile targets from multidimensional context."""

    def synthesize_profile(
        self,
        stable_mood: str,
        jev_decision: JevDecisionBundle,
        current_song: Optional[Track] = None,
        user_preferences: Optional[UserPreferenceSchema] = None,
        recent_skips: int = 0,
        recent_likes: int = 0
    ) -> Tuple[MusicProfile, str]:
        """
        Synthesizes target audio features and returns a human-centered explanation.
        """
        norm_mood = stable_mood.lower()
        archetype = MOOD_ACOUSTIC_ARCHETYPES.get(norm_mood, MOOD_ACOUSTIC_ARCHETYPES["neutral"])
        tier = jev_decision.confidence_tier
        target_energy_choice = getattr(jev_decision.energy, "value", "medium").lower()

        # 1. Energy mapping from Jev decision
        energy_levels = {"low": 0.25, "medium": 0.55, "high": 0.85}
        jev_energy = energy_levels.get(target_energy_choice, 0.55)

        # 2. Preference blend
        pref_bias = user_preferences.preferred_energy_bias if user_preferences else 0.5
        preferred_genres = user_preferences.preferred_genres if user_preferences else ["lofi", "ambient"]

        # 3. Confidence Tier handling
        if tier == ConfidenceTier.LOW:
            # Low confidence: fallback toward balanced safe-default profile
            final_energy = 0.40
            final_valence = 0.50
            final_tempo = 0.40
            final_danceability = 0.40
            final_instrumental = 0.70
            chosen_genre = preferred_genres[0] if preferred_genres else "lofi"
            tags = ["safe_default", "balanced", "calm"]
            explanation = (
                "Recommended because our confidence in the estimated expression is currently low, "
                "so we selected a balanced, gentle track aligned with your listening preferences."
            )
        else:
            # High / Medium confidence: compute blended features
            base_energy = archetype["energy"]
            # Blend mood baseline (50%), Jev energy choice (35%), and user preference bias (15%)
            final_energy = (base_energy * 0.50) + (jev_energy * 0.35) + (pref_bias * 0.15)
            final_energy = round(float(max(0.10, min(0.95, final_energy))), 2)

            final_valence = round(float(archetype["valence"]), 2)
            final_tempo = round(float(archetype["tempo"]), 2)
            final_danceability = round(float(archetype["danceability"]), 2)
            final_instrumental = round(float(archetype["instrumental"]), 2)

            # Genre selection: match archetype or user's top preferred genre
            chosen_genre = archetype["genre"]
            if preferred_genres and recent_likes >= 2:
                # If user has demonstrated affinity, favor preferred genre
                if any(g.lower() in preferred_genres for g in [chosen_genre]):
                    pass
                else:
                    chosen_genre = preferred_genres[0]

            # Acoustic continuity: if current song is playing and continuing, smooth energy step
            if current_song and getattr(jev_decision.transition, "value", "continue") == "continue":
                cur_energy = current_song.profile.energy
                final_energy = round(float((cur_energy * 0.4) + (final_energy * 0.6)), 2)

            tags = list(archetype["mood_tags"])
            explanation = (
                f"Recommended because it matches your current estimated mood ({norm_mood}) "
                f"and your listening preferences."
            )

        target_profile = MusicProfile(
            genre=chosen_genre,
            energy=final_energy,
            valence=final_valence,
            tempo=final_tempo,
            danceability=final_danceability,
            instrumental=final_instrumental,
            mood_tags=tags
        )

        return target_profile, explanation


music_profile_service = MusicProfileService()
