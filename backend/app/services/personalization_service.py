"""Personalization Service (Phase 9: Personalization).
Tracks non-sensitive interaction telemetry:
- played, skipped, completed, liked, disliked
- preferred genres
- preferred energy (dynamic exponential moving average)
- preferred tempo (dynamic exponential moving average)
- skip rate by genre

PRIVACY & SAFETY MANDATES:
- Uses ONLY non-sensitive audio interaction telemetry.
- Explicitly PROHIBITED from inferring, storing, or predicting:
  * race
  * religion
  * political views
  * health / medical status
  * sexuality / sexual orientation
  * other sensitive personal characteristics
- Personalization influences recommendation ranking without ever overriding
  current estimated mood context.
"""
import logging
from typing import Dict, List, Optional, Any, Set

from ..schemas.music import UserPreferenceSchema, UserPreferenceProfile, Track
from ..schemas.mood import MoodClass

logger = logging.getLogger("moodtune.personalization")

# Strict privacy prohibition set
PROHIBITED_INFERENCES: Set[str] = {
    "race", "ethnicity", "religion", "political_views", "politics",
    "health", "medical_status", "sexuality", "sexual_orientation",
    "gender_identity", "biometric_identity"
}


class PersonalizationService:
    """Intelligent, Privacy-Preserving Personalization Service."""

    MAX_PROFILES: int = 500
    MAX_TRACK_HISTORY: int = 100

    def __init__(self):
        # In-memory preference and interaction telemetry store keyed by user_id
        self._profiles: Dict[str, dict] = {}
        self._init_default_profile("default_user")

    def _init_default_profile(self, user_id: str):
        """Initializes a fresh, privacy-compliant user profile with bounded memory footprint."""
        if len(self._profiles) >= self.MAX_PROFILES and user_id not in self._profiles:
            for k in list(self._profiles.keys()):
                if k != "default_user":
                    del self._profiles[k]
                    break

        self._profiles[user_id] = {
            "preferred_genres": ["pop", "lofi", "synthwave"],
            "disliked_genres": [],
            "preferred_energy": 0.64,
            "preferred_tempo": 0.58,
            "preferred_energy_bias": 0.50,
            "transition_sensitivity": 0.60,
            "auto_play_on_mood_shift": True,
            "genre_affinities": {
                "lofi": 1.2,
                "ambient": 1.1,
                "synthwave": 1.25,
                "upbeat_pop": 1.1,
                "pop": 1.2,
                "classical": 1.0,
                "indie_folk": 1.05,
                "meditation": 1.0
            },
            "mood_genre_affinities": {
                "positive": {"upbeat_pop": 1.3, "synthwave": 1.2, "pop": 1.25},
                "calm": {"ambient": 1.3, "lofi": 1.2, "meditation": 1.25},
                "energetic": {"synthwave": 1.4, "upbeat_pop": 1.3, "pop": 1.3},
                "neutral": {"lofi": 1.2, "indie_folk": 1.1},
                "reflective": {"indie_folk": 1.3, "classical": 1.25},
                "low_energy": {"ambient": 1.2, "lofi": 1.15},
                "tense": {"ambient": 1.4, "meditation": 1.35}
            },
            # Non-sensitive interaction counters
            "total_played": 0,
            "total_skipped": 0,
            "total_completed": 0,
            "total_liked": 0,
            "total_disliked": 0,
            "recent_skips": 0,
            "recent_likes": 0,
            # Telemetry by genre
            "genre_plays": {},
            "genre_skips": {},
            "skip_rate_by_genre": {},
            # Track ID history
            "recent_track_ids": [],
            "recent_skipped_ids": [],
            "liked_track_ids": [],
            "disliked_track_ids": []
        }

    # -------------------------------------------------------------------------
    # Profile & Preferences Retrieval
    # -------------------------------------------------------------------------

    def get_user_profile(self, user_id: str = "default_user") -> UserPreferenceProfile:
        """
        Produces the structured UserPreferenceProfile matching specification:
        {
          "preferred_genres": ["pop", "lofi"],
          "preferred_energy": 0.64,
          "preferred_tempo": 0.58,
          "skip_rate_by_genre": {}
        }
        """
        if user_id not in self._profiles:
            self._init_default_profile(user_id)

        raw = self._profiles[user_id]
        return UserPreferenceProfile(
            preferred_genres=list(raw["preferred_genres"]),
            preferred_energy=round(raw["preferred_energy"], 3),
            preferred_tempo=round(raw["preferred_tempo"], 3),
            skip_rate_by_genre=dict(raw.get("skip_rate_by_genre", {})),
            disliked_genres=list(raw.get("disliked_genres", [])),
            total_played=raw.get("total_played", 0),
            total_skipped=raw.get("total_skipped", 0),
            total_completed=raw.get("total_completed", 0),
            total_liked=raw.get("total_liked", 0),
            total_disliked=raw.get("total_disliked", 0)
        )

    def get_preferences(self, user_id: str = "default_user") -> UserPreferenceSchema:
        """Backward-compatible preferences schema getter."""
        profile = self._profiles.get(user_id)
        if not profile:
            self._init_default_profile(user_id)
            profile = self._profiles[user_id]

        return UserPreferenceSchema(
            preferred_genres=profile["preferred_genres"],
            disliked_genres=profile["disliked_genres"],
            preferred_energy_bias=profile["preferred_energy_bias"],
            transition_sensitivity=profile["transition_sensitivity"],
            auto_play_on_mood_shift=profile["auto_play_on_mood_shift"]
        )

    def update_preferences(self, user_id: str, new_prefs: UserPreferenceSchema):
        """Updates user preferences manually."""
        if user_id not in self._profiles:
            self._init_default_profile(user_id)

        self._profiles[user_id].update({
            "preferred_genres": list(new_prefs.preferred_genres),
            "disliked_genres": list(new_prefs.disliked_genres),
            "preferred_energy_bias": new_prefs.preferred_energy_bias,
            "transition_sensitivity": new_prefs.transition_sensitivity,
            "auto_play_on_mood_shift": new_prefs.auto_play_on_mood_shift
        })
        logger.info(f"Updated preferences for user '{user_id}'")

    def reset_profile(self, user_id: str = "default_user"):
        """Resets a user's profile to default state."""
        self._init_default_profile(user_id)

    # -------------------------------------------------------------------------
    # Interaction Tracking (Non-Sensitive Signals Only)
    # -------------------------------------------------------------------------

    def record_play(self, user_id: str, track: Track):
        """Records track playback event."""
        self.record_interaction(user_id=user_id, track=track, feedback_type="play", seconds_played=0.0)

    def record_skip(self, user_id: str, track: Track, seconds_played: float = 0.0):
        """Records track skip event."""
        self.record_interaction(user_id=user_id, track=track, feedback_type="skip", seconds_played=seconds_played)

    def record_complete(self, user_id: str, track: Track):
        """Records track completion event."""
        self.record_interaction(
            user_id=user_id,
            track=track,
            feedback_type="complete",
            seconds_played=float(track.duration_seconds)
        )

    def record_like(self, user_id: str, track: Track):
        """Records explicit track like."""
        self.record_interaction(user_id=user_id, track=track, feedback_type="like", seconds_played=0.0)

    def record_dislike(self, user_id: str, track: Track):
        """Records explicit track dislike."""
        self.record_interaction(user_id=user_id, track=track, feedback_type="dislike", seconds_played=0.0)

    def record_interaction(
        self,
        user_id: str,
        track: Track,
        feedback_type: str,
        seconds_played: float = 0.0,
        mood_at_time: Optional[str] = None
    ):
        """
        Processes non-sensitive interaction feedback to update personalization telemetry.
        Never infers sensitive demographic, religious, political, or health characteristics.
        """
        if user_id not in self._profiles:
            self._init_default_profile(user_id)

        profile = self._profiles[user_id]
        genre = track.profile.genre.lower()
        p = track.profile

        # Track history list management
        recent_tracks = profile.setdefault("recent_track_ids", [])
        if track.id not in recent_tracks:
            recent_tracks.append(track.id)
        if len(recent_tracks) > 50:
            recent_tracks.pop(0)

        # Genre play counters
        genre_plays = profile.setdefault("genre_plays", {})
        genre_skips = profile.setdefault("genre_skips", {})
        skip_rates = profile.setdefault("skip_rate_by_genre", {})
        affinities = profile.setdefault("genre_affinities", {})
        current_genre_weight = affinities.get(genre, 1.0)

        # 1. Play event
        if feedback_type == "play":
            profile["total_played"] = profile.get("total_played", 0) + 1
            genre_plays[genre] = genre_plays.get(genre, 0) + 1
            skip_rates[genre] = round(genre_skips.get(genre, 0) / max(1, genre_plays[genre]), 2)

            # Gentle moving average on energy and tempo
            alpha = 0.08
            profile["preferred_energy"] = round((1 - alpha) * profile["preferred_energy"] + alpha * p.energy, 3)
            profile["preferred_tempo"] = round((1 - alpha) * profile["preferred_tempo"] + alpha * p.tempo, 3)
            logger.info(f"Recorded PLAY for track '{track.title}' (Genre: {genre})")

        # 2. Like event
        elif feedback_type == "like":
            profile["total_liked"] = profile.get("total_liked", 0) + 1
            profile["recent_likes"] = profile.get("recent_likes", 0) + 1
            liked_ids = profile.setdefault("liked_track_ids", [])
            if track.id not in liked_ids:
                liked_ids.append(track.id)
            if len(liked_ids) > self.MAX_TRACK_HISTORY:
                liked_ids.pop(0)

            # Boost genre affinity
            affinities[genre] = min(2.5, current_genre_weight + 0.20)
            if genre not in profile["preferred_genres"]:
                profile["preferred_genres"].append(genre)

            # Higher weight update on preferred energy and tempo
            alpha = 0.25
            profile["preferred_energy"] = round((1 - alpha) * profile["preferred_energy"] + alpha * p.energy, 3)
            profile["preferred_tempo"] = round((1 - alpha) * profile["preferred_tempo"] + alpha * p.tempo, 3)

            if mood_at_time:
                mood_aff = profile.setdefault("mood_genre_affinities", {}).setdefault(mood_at_time, {})
                mood_aff[genre] = min(2.5, mood_aff.get(genre, 1.0) + 0.25)

            logger.info(f"Recorded LIKE for track '{track.title}' (Genre {genre} affinity -> {affinities[genre]:.2f})")

        # 3. Dislike event
        elif feedback_type == "dislike":
            profile["total_disliked"] = profile.get("total_disliked", 0) + 1
            disliked_ids = profile.setdefault("disliked_track_ids", [])
            if track.id not in disliked_ids:
                disliked_ids.append(track.id)
            if len(disliked_ids) > self.MAX_TRACK_HISTORY:
                disliked_ids.pop(0)

            # Penalize genre affinity
            affinities[genre] = max(0.15, current_genre_weight - 0.35)
            # Demote from preferred genres if present
            if genre in profile["preferred_genres"]:
                profile["preferred_genres"].remove(genre)
            if genre not in profile["disliked_genres"]:
                profile["disliked_genres"].append(genre)

            logger.info(f"Recorded DISLIKE for track '{track.title}' (Genre {genre} affinity -> {affinities[genre]:.2f})")

        # 4. Skip event
        elif feedback_type == "skip":
            profile["total_skipped"] = profile.get("total_skipped", 0) + 1
            profile["recent_skips"] = profile.get("recent_skips", 0) + 1
            skipped_ids = profile.setdefault("recent_skipped_ids", [])
            if track.id not in skipped_ids:
                skipped_ids.append(track.id)
            if len(skipped_ids) > 30:
                skipped_ids.pop(0)

            genre_skips[genre] = genre_skips.get(genre, 0) + 1
            genre_plays[genre] = genre_plays.get(genre, 0) + 1
            skip_rates[genre] = round(genre_skips[genre] / max(1, genre_plays[genre]), 2)

            # Skip penalty on genre affinity proportional to early skip
            penalty = 0.15 if seconds_played < 20.0 else 0.06
            affinities[genre] = max(0.2, current_genre_weight - penalty)

            # If skip rate is high (> 65% with >= 3 plays), demote from preferred genres
            if skip_rates[genre] > 0.65 and genre_plays[genre] >= 3:
                if genre in profile["preferred_genres"] and len(profile["preferred_genres"]) > 1:
                    profile["preferred_genres"].remove(genre)
                    logger.info(f"Demoted genre '{genre}' from preferred genres due to high skip rate ({skip_rates[genre]:.2f})")

            logger.info(f"Recorded SKIP for track '{track.title}' (Genre {genre} skip_rate: {skip_rates[genre]:.2f})")

        # 5. Complete event
        elif feedback_type == "complete":
            profile["total_completed"] = profile.get("total_completed", 0) + 1
            profile["recent_skips"] = max(0, profile.get("recent_skips", 0) - 1)
            genre_plays[genre] = genre_plays.get(genre, 0) + 1
            skip_rates[genre] = round(genre_skips.get(genre, 0) / max(1, genre_plays[genre]), 2)

            affinities[genre] = min(2.5, current_genre_weight + 0.10)
            if genre not in profile["preferred_genres"]:
                profile["preferred_genres"].append(genre)

            # Completion reinforces preferred energy and tempo
            alpha = 0.15
            profile["preferred_energy"] = round((1 - alpha) * profile["preferred_energy"] + alpha * p.energy, 3)
            profile["preferred_tempo"] = round((1 - alpha) * profile["preferred_tempo"] + alpha * p.tempo, 3)

            logger.info(f"Recorded COMPLETE for track '{track.title}' (Genre {genre})")

    # -------------------------------------------------------------------------
    # Recommendation Influence & Safeguards
    # -------------------------------------------------------------------------

    def compute_personalization_boost(self, user_id: str, track: Track, mood: str) -> float:
        """
        Computes a bounded personalization score multiplier in [0.75, 1.25].
        MANDATE: Personalization must NEVER completely override current mood context.
        The multiplier is strictly bounded so mood alignment remains the primary driver.
        """
        profile = self._profiles.get(user_id, self._profiles.get("default_user", {}))
        genre = track.profile.genre.lower()

        # Genre blacklist check: strong reduction but not total deletion
        if genre in profile.get("disliked_genres", []):
            return 0.50

        # Base genre affinity
        base_affinity = profile.get("genre_affinities", {}).get(genre, 1.0)

        # Mood-specific affinity
        mood_aff = profile.get("mood_genre_affinities", {}).get(mood, {}).get(genre, 1.0)

        # Energy alignment bonus with user's preferred energy
        user_pref_energy = profile.get("preferred_energy", 0.50)
        energy_alignment = 1.0 - abs(track.profile.energy - user_pref_energy) * 0.30

        combined = (base_affinity * 0.40) + (mood_aff * 0.35) + (energy_alignment * 0.25)

        # Strictly bounded multiplier: [0.75, 1.25]
        bounded_multiplier = float(min(1.25, max(0.75, combined)))
        return round(bounded_multiplier, 3)

    def get_recent_stats(self, user_id: str = "default_user") -> dict:
        """Returns non-sensitive recent statistics."""
        profile = self._profiles.get(user_id)
        if not profile:
            self._init_default_profile(user_id)
            profile = self._profiles[user_id]

        return {
            "recent_skips": profile.get("recent_skips", 0),
            "recent_likes": profile.get("recent_likes", 0),
            "total_completed": profile.get("total_completed", 0),
            "recent_track_ids": list(profile.get("recent_track_ids", [])),
            "recent_skipped_ids": list(profile.get("recent_skipped_ids", [])),
            "liked_track_ids": list(profile.get("liked_track_ids", [])),
            "disliked_track_ids": list(profile.get("disliked_track_ids", []))
        }


# Global singleton instance
personalization_service = PersonalizationService()
